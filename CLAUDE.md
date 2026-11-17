# CLAUDE.md — Idea Hub

Guidance for coding agents working in this repository.

## What this is

Internal **Idea Hub** (Idea Konnekt): submit / explore / review ideas, plus phase features (ideathons, recognition, delivery, agents, insights).

| Area | Path | Stack |
|------|------|-------|
| Backend | `backend/` | FastAPI, SQLAlchemy async, Postgres, Redis OTP, Alembic, uv |
| Frontend | `frontend/` | Vite, React 18, TypeScript |
| Design source | `idea-hub.html` | Prototype UI — React must match |
| Docs | `docs/` | Kompass prompts, phase wireup, agent tooling |

## Architecture

- **Spine**: auth, users, ideas lifecycle, explore, engagement, review
- **Phase 2+3 / 4+5+6**: mounted via `include_phase23_routers` / `include_phase456_routers`
- Layers: `routers` → `services` → `repositories` / `models`; `schemas` for I/O
- Auth: email+password → Redis OTP → JWT cookies (see `backend/README.md`)

## Commands

```bash
# Backend (preferred local services)
cd backend
cp -n .env.example .env
uv sync
./scripts/dev-services.sh up
uv run alembic upgrade head
uv run python -m app.seed.demo
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
cp -n .env.example .env
npm install && npm run dev
```

API: `http://127.0.0.1:8000/docs` · UI: `http://localhost:5173`

## Design rules

Full Cursor rule: `.cursor/rules/idea-hub-frontend-parity.mdc` (applies to `frontend/**/*.{tsx,ts,css}`). Skill: `idea-hub-ui-html-parity`.

- Port from `idea-hub.html`; use `frontend/src/styles/tokens.css` + `app.css` — do not invent a new visual system
- Fonts: DM Sans + IBM Plex Mono; reuse `AppShell`, `StatusPill`, `IdeaCard`
- Prefer **list/row** patterns (Integrations, Tracker) over generic card grids for catalog/task surfaces
- Status via chips/`StatusPill`, not raw browser selects when product patterns already use chips
- Scope new CSS (`.trk-*`, `.integ-*`); never overload bare `.check` as an 18px box (it is a flex label row)
- Preserve Idea Hub brand tokens; avoid AI-slop extras (glow stacks, pill clusters, cream+serif terracotta, etc.)

## Secrets

- Never commit `backend/.env` / `frontend/.env`
- Seed emails + shared demo password: **`backend/README.md`** only
- SMTP/JWT live in local `.env` (see `.env.example`)

## Agent tooling

See [`docs/AGENT_TOOLING.md`](docs/AGENT_TOOLING.md) for Cursor rules, skills, hooks, subagents, and **code-review-graph** MCP.

After major structural changes: `uvx code-review-graph update` (or MCP `build_or_update_graph_tool`).
