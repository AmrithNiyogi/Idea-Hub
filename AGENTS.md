# AGENTS.md — Idea Hub

Short briefing for Cursor / Claude coding agents.

## Stack

FastAPI + Postgres + Redis (OTP) backend · Vite React TS frontend · design from `idea-hub.html`.

## Do first

1. Read `CLAUDE.md` and `docs/AGENT_TOOLING.md`
2. For relationship questions, use **code-review-graph** MCP (`user-code-review-graph`)
3. Match UI to `idea-hub.html` + `frontend/src/styles/tokens.css`
4. Keep backend layering: routers → services → repos

## Run

See `backend/README.md` and `frontend/README.md`. Preferred: `backend/scripts/dev-services.sh` (ports **15432** / **16379**), API **:8000**, Vite **:5173**.

## Seed / login

Demo users and shared password are documented in `backend/README.md` — do not invent credentials or commit `.env`.

## Project agents

| Subagent | Use for |
|----------|---------|
| `idea-hub-backend` | API, auth, migrations, seed |
| `idea-hub-frontend` | Pages, tokens, HTML parity |
| `idea-hub-reviewer` | Diff review + blast radius |

## Skills (project)

- `idea-hub-spine` — boot / migrate / seed
- `idea-hub-ui-html-parity` — port from HTML
- `idea-hub-auth-otp` — JWT + OTP + SMTP
- `idea-hub-code-review-graph` — build/query graph
- `idea-hub-pull-idea` — fetch idea agent-context by UUID/URL

## External trackers / Integrations

ClickUp / Jira / custom webhook live under `backend/app/trackers/` (pluggable `TrackerProvider` registry). Broader catalog + org/user scopes: `backend/app/integrations/`. UI: `/integrations` (personal + admin org defaults). Delivery uses effective connections (user → org). Docs: `docs/INTEGRATIONS.md`, `docs/TRACKER_PROVIDERS.md`.
