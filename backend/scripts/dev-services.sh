#!/usr/bin/env bash
# Start/stop ISOLATED throwaway Postgres + Redis (tracing-style, no Docker required).
# Own ports, own data dir under backend/.dev — never touches system Postgres/Redis.
#   Postgres: 127.0.0.1:15432, user/pass/db ideahub/ideahub/ideahub
#   Redis   : 127.0.0.1:16379, no password
#
# Prefer system packages (apt/brew). If initdb is missing, auto-downloads a portable
# PostgreSQL 16 binary into .dev/pg-dist (x86_64/aarch64 Linux).
#
# Usage: scripts/dev-services.sh {up|start|down|stop|status|env}
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$ROOT/.dev"
mkdir -p "$D"/{pg/data,pg/log,redis/data,redis/log,pg-dist}
PG_PORT=15432
REDIS_PORT=16379
PG_USER=ideahub
PG_PASS=ideahub
PG_DB=ideahub
PG_DIST_VER=16.6.0

# Prefer PATH, then Debian/Ubuntu cluster bins, Homebrew, then vendored .dev/pg-dist.
pg_bin() {
  local name="$1" p
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi
  for p in /usr/lib/postgresql/*/bin/"$name" \
           /opt/homebrew/opt/postgresql*/bin/"$name" \
           /usr/local/opt/postgresql*/bin/"$name" \
           "$D"/pg-dist/*/bin/"$name" \
           "$D"/pg-dist/bin/"$name"; do
    # shellcheck disable=SC2086
    for m in $p; do
      [ -x "$m" ] && { echo "$m"; return 0; }
    done
  done
  return 1
}

ensure_portable_postgres() {
  if pg_bin initdb >/dev/null 2>&1; then
    return 0
  fi
  local arch url tarball dest
  case "$(uname -m)" in
    x86_64|amd64) arch="x86_64-unknown-linux-gnu" ;;
    aarch64|arm64) arch="aarch64-unknown-linux-gnu" ;;
    *)
      echo "initdb not found and no portable Postgres for arch=$(uname -m)"
      echo "Install postgresql (apt/brew) or use docker compose as fallback."
      return 1
      ;;
  esac
  # theseus-rs prebuilt PostgreSQL binaries (user-space, no sudo).
  url="https://github.com/theseus-rs/postgresql-binaries/releases/download/${PG_DIST_VER}/postgresql-${PG_DIST_VER}-${arch}.tar.gz"
  tarball="$D/pg-dist/postgresql-${PG_DIST_VER}-${arch}.tar.gz"
  dest="$D/pg-dist/postgresql-${PG_DIST_VER}-${arch}"
  if [ ! -x "$dest/bin/initdb" ]; then
    echo "Downloading portable PostgreSQL ${PG_DIST_VER} → $dest"
    curl -fsSL "$url" -o "$tarball"
    mkdir -p "$dest"
    tar -xzf "$tarball" -C "$D/pg-dist"
    # Tarball may unpack to a top-level dir; normalize to $dest if needed.
    if [ ! -x "$dest/bin/initdb" ]; then
      local unpacked
      unpacked="$(find "$D/pg-dist" -maxdepth 2 -type f -path '*/bin/initdb' | head -1)"
      if [ -n "$unpacked" ]; then
        dest="$(cd "$(dirname "$unpacked")/.." && pwd)"
      fi
    fi
    rm -f "$tarball"
  fi
  if [ ! -x "$dest/bin/initdb" ]; then
    echo "Portable Postgres extract failed under $D/pg-dist"
    return 1
  fi
  # Symlink for stable pg_bin lookup
  ln -sfn "$dest" "$D/pg-dist/current"
  echo "portable postgres ready: $dest"
}

pg_up() {
  ss -ltn 2>/dev/null | grep -q "127.0.0.1:$PG_PORT " && { echo "postgres already up"; return; }
  ensure_portable_postgres || return 1
  local INITDB POSTGRES PG_CTL CREATEDB PSQL
  INITDB="$(pg_bin initdb)" || { echo "initdb not found"; return 1; }
  POSTGRES="$(pg_bin postgres)" || { echo "postgres not found"; return 1; }
  PG_CTL="$(pg_bin pg_ctl)" || true
  CREATEDB="$(pg_bin createdb)" || true
  PSQL="$(pg_bin psql)" || true

  if [ ! -f "$D/pg/data/PG_VERSION" ]; then
    "$INITDB" -D "$D/pg/data" -U "$PG_USER" --auth-local=trust --auth-host=trust --no-instructions >/dev/null
  fi

  # Bind only loopback; unix socket under .dev/pg so we never use /var/run/postgresql.
  mkdir -p "$D/pg"
  if [ -n "${PG_CTL:-}" ]; then
    "$PG_CTL" -D "$D/pg/data" -l "$D/pg/log/stdout.log" -o "-h 127.0.0.1 -p $PG_PORT -k $D/pg" start >/dev/null
  else
    (nohup "$POSTGRES" -D "$D/pg/data" -h 127.0.0.1 -p "$PG_PORT" -k "$D/pg" >> "$D/pg/log/stdout.log" 2>&1 &)
  fi

  for _ in $(seq 1 60); do
    ss -ltn 2>/dev/null | grep -q "127.0.0.1:$PG_PORT " && break
    sleep 1
  done
  ss -ltn 2>/dev/null | grep -q "127.0.0.1:$PG_PORT " || {
    echo "postgres failed to start; see $D/pg/log"
    tail -40 "$D/pg/log/stdout.log" 2>/dev/null || true
    return 1
  }

  if [ -n "${CREATEDB:-}" ]; then
    "$CREATEDB" -h 127.0.0.1 -p "$PG_PORT" -U "$PG_USER" "$PG_DB" 2>/dev/null || true
  elif [ -n "${PSQL:-}" ]; then
    "$PSQL" -h 127.0.0.1 -p "$PG_PORT" -U "$PG_USER" -d postgres \
      -c "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" -tA 2>/dev/null | grep -q 1 \
      || "$PSQL" -h 127.0.0.1 -p "$PG_PORT" -U "$PG_USER" -d postgres -c "CREATE DATABASE $PG_DB" >/dev/null
  fi
  if [ -n "${PSQL:-}" ]; then
    "$PSQL" -h 127.0.0.1 -p "$PG_PORT" -U "$PG_USER" -d postgres \
      -c "ALTER USER $PG_USER WITH PASSWORD '$PG_PASS'" >/dev/null 2>&1 || true
  fi
  echo "postgres up on :$PG_PORT"
}

redis_up() {
  ss -ltn 2>/dev/null | grep -q "127.0.0.1:$REDIS_PORT " && { echo "redis already up"; return; }
  command -v redis-server >/dev/null || {
    echo "redis-server not found (install redis or use docker compose)"
    return 1
  }
  cat > "$D/redis/redis.conf" <<CONF
bind 127.0.0.1
port $REDIS_PORT
dir $D/redis/data
daemonize no
logfile $D/redis/log/redis.log
save ""
CONF
  (nohup redis-server "$D/redis/redis.conf" >> "$D/redis/log/stdout.log" 2>&1 &)
  for _ in $(seq 1 40); do
    ss -ltn 2>/dev/null | grep -q "127.0.0.1:$REDIS_PORT " && {
      echo "redis up on :$REDIS_PORT"
      return
    }
    sleep 1
  done
  echo "redis failed to start; see $D/redis/log"
  return 1
}

_stop_port() {
  local port="$1" label="$2" pid
  pid=$(ss -ltnp 2>/dev/null | grep -E "127.0.0.1:$port " | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2 || true)
  [ -z "${pid:-}" ] && return 0
  [ "$(ps -o user= -p "$pid" | tr -d ' ')" = "$(id -un)" ] || {
    echo "refusing: pid $pid not owned by $(id -un)"
    return 2
  }
  kill -TERM "$pid"
  for _ in $(seq 1 40); do
    kill -0 "$pid" 2>/dev/null || {
      echo "$label stopped"
      return 0
    }
    sleep 1
  done
  return 1
}
pg_down() { _stop_port "$PG_PORT" postgres; }
redis_down() { _stop_port "$REDIS_PORT" redis; }

case "${1:-}" in
  up|start) pg_up; redis_up ;;
  down|stop) redis_down; pg_down ;;
  status)
    ss -ltn 2>/dev/null | grep -q "127.0.0.1:$PG_PORT " && echo "postgres: up :$PG_PORT" || echo "postgres: down"
    ss -ltn 2>/dev/null | grep -q "127.0.0.1:$REDIS_PORT " && echo "redis: up :$REDIS_PORT" || echo "redis: down"
    ;;
  env) cat <<ENV
export DATABASE_URL=postgresql+asyncpg://$PG_USER:$PG_PASS@127.0.0.1:$PG_PORT/$PG_DB
export REDIS_HOST=127.0.0.1
export REDIS_PORT=$REDIS_PORT
ENV
  ;;
  *)
    echo "usage: $0 {up|start|down|stop|status|env}"
    exit 1
    ;;
esac
