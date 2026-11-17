# Phase 4–6 wire-up

Additive modules for Insights, Admin, Simulated Agents, Problem radar, Reopen, and Collab.

## Backend

`main.py` already includes (same pattern as phase23):

```python
from app.phase456_register import import_phase456_models, include_phase456_routers
# in lifespan:
import_phase456_models()
# after routers:
include_phase456_routers(app, prefix=prefix)
```

If a sibling reset `main.py`, re-add those two calls.

### Migrate + seed

```bash
# PG/Redis: prefer tracing-style local services (not docker-compose)
# backend/scripts/dev-services.sh   # when present

cd backend
alembic upgrade head   # includes phase456_001 after phase23_001
python -m app.seed.demo
python -m app.seed.phase456
```

## Frontend

`routeModules.ts` auto-discovers `phase456_routes.tsx` (routes + sidebar). No App.tsx edit required.

Idea detail Collaborate tab: `?tab=collab` via `CollabTrackerPanel`.

## APIs (prefix `/api/v1`)

| Area | Endpoints |
|------|-----------|
| Insights | `GET /insights?days=` |
| Admin | `GET /admin/config`, `PUT /admin/timelines\|scoring\|points`, `POST /admin/categories`, `PATCH /admin/categories/{id}`, `POST /admin/panels`, `PUT /admin/panels/{id}`, panel member/chair, `GET /admin/audit\|export`, `POST /admin/reset` |
| Agents | `GET /agents/roster`, `POST /agents/run`, `GET /agents/runs\|proposals`, `POST /agents/proposals/decide`, `GET /agents/kompass`, `PUT /agents/kompass/questions/{id}` |
| Problems | `GET /problems`, `/problems/headline`, `/problems/{key}`, `/problems/by-idea/{id}`, `POST\|DELETE /problems/{key}/me-too`, `PATCH /problems/{key}/meta` |
| Reopen | `POST /reopen`, `GET /reopen/proposals`, `GET /reopen/{idea_id}`, `POST .../mark-manual\|approve\|dismiss` |
| Collab | `GET /collab/mine\|incoming`, `POST /collab`, decide/withdraw, `GET\|POST /ideas/{id}/tracker…` |

## Frontend routes

- `/insights` — leadership
- `/admin` — admin
- `/agents` — reviewer / leadership / admin
- `/problems`, `/problems/:key` — all roles
- Idea `?tab=collab` — collab + tracker

## Gaps / thin spots

- Admin categories/panels UI supports create, edit, soft-disable, and membership; People/roles and ideathon/metrics admin tabs from the HTML prototype remain out of scope.
- Reset is a hook (audit + message) — does not truncate; run seed CLI.
- Export returns inventory counts, not full JSON dump.
- Problem clusters recomputed on read (no cached cluster table).
- Reopen approve writes status history but no `reopened` boolean column (reason text).
- Agents never call live Kompass; adapter boundary is `AgentGateway._execute_simulated`.
- Ideathon agent heuristics not fully ported (recognition/analytics stubs only).
- Collab accept for `build` does not yet create delivery contributor rows.
- No automatic parking when needs-info SLA expires (flags only via workflow agent).
