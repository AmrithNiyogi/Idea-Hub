---
name: idea-hub-spine
description: Run IdeaKonnekt local stack — Postgres/Redis via dev-services, uv sync, Alembic migrate, seed demo users, uvicorn, and Vite frontend. Use when starting the app, resetting local DB, seeding, or debugging boot/migrate/seed failures.
---

# IdeaKonnekt spine — run / migrate / seed

## Preferred path (no Docker)

```bash
cd backend
cp -n .env.example .env          # never commit .env
uv sync
./scripts/dev-services.sh up
./scripts/dev-services.sh status
uv run alembic upgrade head
uv run python -m app.seed.demo
# optional phase seeds if present:
# uv run python -m app.seed.ideathons
# uv run python -m app.seed.recognition
# uv run python -m app.seed.delivery
# uv run python -m app.seed.phase456
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
cp -n .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                      # http://localhost:5173
```

| Service | Default |
|---------|---------|
| Postgres | `127.0.0.1:15432` user/pass/db `ideahub` |
| Redis | `127.0.0.1:16379` |
| API | `http://127.0.0.1:8000` (`/docs`, `/health`) |
| UI | `http://localhost:5173` |

```bash
./scripts/dev-services.sh {up|start|down|stop|status|env}
```

## Docker Compose fallback

From repo root: `docker compose up -d`, then point `backend/.env` at `localhost:5432` / `6379`.

## Auth smoke

Seed password and emails: `backend/README.md`. OTP: SMTP in `.env` and/or console log when `ENV=dev`.

## Agent checklist

- [ ] `.env` exists and is gitignored
- [ ] `dev-services.sh status` shows Postgres + Redis
- [ ] `alembic upgrade head` succeeded
- [ ] Seed completed; login works with OTP
- [ ] Frontend talks to `:8000` with credentials
