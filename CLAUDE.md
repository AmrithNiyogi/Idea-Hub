# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Workspace-wide rules (git, scope, verification) live in `../CLAUDE.md`; this file covers Idea Hub only. If they conflict, this file wins.

## What this is

Internal **Idea Hub** (Idea Konnekt): submit / explore / review ideas, plus phase features (ideathons, recognition, delivery, agents, insights, groups).

| Area | Path | Stack |
|------|------|-------|
| Backend | `backend/` | FastAPI, SQLAlchemy async, Postgres, Redis OTP, Alembic, uv |
| Frontend | `frontend/` | Vite, React 18, TypeScript, vitest |
| Design source | `idea-hub.html` | Prototype UI — React must match |
| Docs | `docs/` | Kompass prompts, phase wireup, integrations, agent tooling |

## Commands

```bash
# Backend (from backend/) — Makefile wraps these
cp -n .env.example .env
make sync                       # uv sync --extra dev
make services-up                # native Postgres (15432) + Redis (16379) via scripts/dev-services.sh
make migrate                    # alembic upgrade head
make seed                       # app.seed.demo  (groups: uv run python -m app.seed.groups)
make api                        # uvicorn :8000  (docs at /docs)

make typecheck | lint | test | secrets   # mypy | pylint+pydoclint | pytest | gitleaks
make check                      # all four gates

uv run pytest tests/test_idea_service.py::test_name --no-cov   # single test

# Frontend (from frontend/)
npm install && npm run dev      # :5173
npm run check                   # lint + typecheck + vitest with coverage
npx vitest run src/api/ideas.test.ts   # single test file
```

Test gotchas: `pytest` addopts include `-x` and a coverage gate (`--cov-fail-under=85`) scoped to a handful of critical services (auth, OTP, idea, review, notification, email adapter, lifecycle, auth deps). Running a single test without `--no-cov` fails the gate. Tests must not hit shared/dev databases.

## Backend architecture

- **Layers**: `routers` → `services` → `repositories` / `models`; `schemas` for I/O. Routers are thin (see `.cursor/rules/idea-hub-backend-layering.mdc`).
- **Spine vs phases**: `app/main.py` mounts the spine (auth, users, ideas lifecycle, explore, engagement, review). Later features are additive and mounted via `app/phase23_register.py` (`include_phase23_routers`) and `app/phase456_register.py` (`include_phase456_routers`, which holds admin, agents, collab, groups, insights, problems, reopen). New phase routers register there, not in spine routers. Phase services reach idea status through `SpineBridge`.
- **Auth**: email+password → Redis OTP → JWT cookies; also TOTP MFA and Microsoft SSO (`docs/MFA_TOTP.md`, `docs/MICROSOFT_SSO.md`). Details in `backend/README.md`.
- **External connections** come in two registries: `app/trackers/` (ClickUp / Jira / custom webhook behind a `TrackerProvider` registry) and `app/integrations/` (broader catalog: Notion docs, Teams incoming webhook, MCP client; org and user scopes). Delivery uses the effective connection (user → org). See `docs/INTEGRATIONS.md`, `docs/TRACKER_PROVIDERS.md`.
- **Groups** (replaced the old team-space model): Discord-like channels + chat, optionally linked to an idea. API `/groups/*`, `GET /ideas/{id}/group`; `docs/TEAM_SPACE.md`.
- **DB sessions**: `get_db` in `app/db/session_deps.py` rolls back and closes on exceptions (including FastAPI `HTTPException`); regression-tested in `tests/test_session_deps.py`.
- **Schema changes** → new Alembic revision in `backend/alembic/versions/`. Demo data → `app.seed.*`, run after `alembic upgrade head`.
- **Type-check gate**: mypy is strict-ish, but `pyproject.toml` lists legacy phase modules under `ignore_errors` (e.g. `agent_gateway`, `insights_service`, `admin_service`, `collab_service`). New code should be fully typed; don't add modules to that list. `pydoclint` runs with pylint, so docstrings need to match signatures.

## Frontend architecture

- `src/api/*` — one axios-based module per backend area (with `client.ts`/`http.ts` as the shared layer); `src/pages`, `src/components`, `src/auth` (provider + `ProtectedRoute`).
- Routes are split like the backend: `App.tsx` plus `phase23_routes.tsx`, `phase456_routes.tsx`, `profile_routes.tsx`; `routeModules.ts` holds the lazy page modules.
- Styling: `src/styles/tokens.css` + `app.css`.

## Design rules

Full Cursor rule: `.cursor/rules/idea-hub-frontend-parity.mdc` (applies to `frontend/**/*.{tsx,ts,css}`). Skill: `idea-hub-ui-html-parity`.

- Port from `idea-hub.html`; use `tokens.css` + `app.css` — do not invent a new visual system
- Fonts: DM Sans + IBM Plex Mono; reuse `AppShell`, `StatusPill`, `IdeaCard`
- Prefer **list/row** patterns (Integrations, Tracker) over generic card grids for catalog/task surfaces
- Status via chips/`StatusPill`, not raw browser selects when product patterns already use chips
- Scope new CSS (`.trk-*`, `.integ-*`); never overload bare `.check` as an 18px box (it is a flex label row)
- Preserve Idea Hub brand tokens; avoid AI-slop extras (glow stacks, pill clusters, cream+serif terracotta, etc.)

## Secrets

- Never commit `backend/.env` / `frontend/.env`
- Seed emails + shared demo password: **`backend/README.md`** only
- SMTP/JWT/OAuth credentials live in local `.env` (see `.env.example`)

## Agent tooling

See [`docs/AGENT_TOOLING.md`](docs/AGENT_TOOLING.md) for Cursor rules, skills, hooks, subagents, and **code-review-graph** MCP. `AGENTS.md` is a short briefing for the same.

After major structural changes: `uvx code-review-graph update` (or MCP `build_or_update_graph_tool`).
