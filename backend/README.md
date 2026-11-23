# KonnektIdea — Backend (Phase 1 spine)

FastAPI + Postgres + Redis. Auth mirrors Kompass admin (email+password → OTP → JWT cookies).

Agent rules/skills/hooks/MCP: see [`docs/AGENT_TOOLING.md`](../docs/AGENT_TOOLING.md) and root `CLAUDE.md` / `AGENTS.md`.

## Quick start (preferred — no Docker)

```bash
cd backend
cp .env.example .env          # already points at 15432 / 16379
uv sync

./scripts/dev-services.sh up  # isolated Postgres+Redis under .dev/
./scripts/dev-services.sh status
# optional: eval "$(./scripts/dev-services.sh env)"

uv run alembic upgrade head
uv run python -m app.seed.demo          # users, ideas, groups/channels, …
# groups only (idempotent): uv run python -m app.seed.groups
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

After seed, open **Groups** in the sidebar (`/groups`) for sample collaborate chat
(Parking lot without an idea + optional runbook-linked group). See `docs/TEAM_SPACE.md`.

| Script | Ports |
|--------|-------|
| Postgres | `127.0.0.1:15432` user/pass/db `ideahub` |
| Redis | `127.0.0.1:16379` (no password) |

```bash
./scripts/dev-services.sh {up|start|down|stop|status|env}
```

API docs: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/health

### Optional Docker Compose fallback

If you prefer containers (or lack local Redis/Postgres binaries):

```bash
# from repo root
docker compose up -d
# then point .env at localhost:5432 / 6379 and run alembic/seed/uvicorn as above
```

## Seed credentials

Shared password: **`IdeaHub!2026`**

| Email | Name | Primary role |
|-------|------|--------------|
| priya@dotkonnekt.example | Priya Sharma | contributor (+lead) |
| marcus@dotkonnekt.example | Marcus Webb | contributor |
| elena@dotkonnekt.example | Elena Rossi | reviewer |
| tomas@dotkonnekt.example | Tomas Berg | lead (+reviewer) |
| dana@dotkonnekt.example | Dana Okafor | leadership |
| sam@dotkonnekt.example | Sam Patel | admin (+reviewer) |

### Login OTP email (SMTP)

OTP delivery requires `SMTP_*` in `backend/.env` (see `.env.example` for placeholders). Copy real credentials into `.env` only — that file is gitignored.

When `OTP_EMAIL_OVERRIDE` is set, every OTP is emailed to that address regardless of which account is logging in. Password auth still uses the real account email; the intended login email is named in the message body. In `ENV=dev`, the OTP is also printed to the uvicorn console as a backup. If SMTP send fails, the OTP is discarded and the API returns 500.

## Sample auth curl

```bash
# 1) Send OTP (delivered to OTP_EMAIL_OVERRIDE when set; also logged in DEV console)
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/send-login-otp \
  -H 'Content-Type: application/json' \
  -d '{"email":"elena@dotkonnekt.example","password":"IdeaHub!2026"}'

# 2) Login (replace 123456 with the emailed / console OTP); saves cookies
curl -s -c /tmp/ih.jar -D - -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"elena@dotkonnekt.example","password":"IdeaHub!2026","otp":"123456"}'

# 3) Me
curl -s -b /tmp/ih.jar http://127.0.0.1:8000/api/v1/users/me
```

## Microsoft Entra ID (optional)

Work/school OIDC SSO runs alongside OTP. Configure Azure app registration, then set `MICROSOFT_*` in `.env`. Full steps: [`docs/MICROSOFT_SSO.md`](../docs/MICROSOFT_SSO.md).

### Authenticator MFA (TOTP)

Optional authenticator-app MFA runs alongside email OTP. Enroll from **Account** settings; at login choose **Email code** or **Authenticator app**. Details: [`docs/MFA_TOTP.md`](../docs/MFA_TOTP.md).

## API prefix

All routes under `/api/v1`. Phase 2+3 / 4+5+6 routers mount via `include_phase23_routers` / `include_phase456_routers`.

## Quality gates

Install tooling once, then run the full gate suite:

```bash
cd backend
uv sync --extra dev
make check   # typecheck + lint + test + secrets
```

| Target | What it runs |
|--------|----------------|
| `make typecheck` | `mypy app` (strict-ish) |
| `make lint` | `pylint` + `pydoclint` (Google-style) |
| `make test` | `pytest -x` with `--cov-fail-under=85` on critical paths |
| `make secrets` | `gitleaks detect` (repo root; `.env` not allowlisted) |
| `make check` | all of the above |

Coverage is measured on critical modules (auth/OTP/JWT, ideas lifecycle, review decide, notifications, email adapter, auth deps, lifecycle). Delivery has smoke tests but is not in the fail-under set yet. First test failure stops the run (`-x` / `--maxfail=1`).

### CI snippet (Bitbucket Pipelines)

No pipeline file exists in this repo yet. Drop this step into a future `bitbucket-pipelines.yml` (or GitHub Actions equivalent):

```yaml
# bitbucket-pipelines.yml (backend quality gates)
image: python:3.12

pipelines:
  default:
    - step:
        name: Backend quality gates
        caches:
          - pip
        script:
          - curl -LsSf https://astral.sh/uv/install.sh | sh
          - export PATH="$HOME/.local/bin:$PATH"
          - cd backend
          - uv sync --extra dev
          - make typecheck
          - make lint
          - make test
          # Install gitleaks once in the image/cache, then:
          # curl -sSL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_..._linux_x64.tar.gz | tar xz
          - make secrets
```

Requires `gitleaks` on `PATH` for `make secrets` (already common on DotKonnekt developer machines).
