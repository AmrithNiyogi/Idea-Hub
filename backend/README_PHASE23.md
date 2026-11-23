# KonnektIdea — Phase 2 + Phase 3 (Delivery, Ideathons, Recognition, Profiles)

Additive modules built alongside the Phase 1 spine. **Do not treat this package as a standalone app** — mount it into the spine FastAPI + Vite React apps.

## Enable backend

1. Ensure spine Postgres has `users` and `ideas` tables (Phase 1 migration).
2. Point Alembic `down_revision` in `alembic/versions/20261117_phase23_tables.py` at the spine head revision, then:

   ```bash
   cd backend && alembic upgrade head
   ```

3. In spine `main.py`:

   ```python
   from app.phase23_register import include_phase23_routers, import_phase23_models

   import_phase23_models()  # if Alembic env imports models from a registry
   include_phase23_routers(app)  # mounts under /api/v1
   ```

4. In spine seed (after demo users/ideas):

   ```python
   from app.seed import seed_delivery, seed_ideathons, seed_recognition

   await seed_recognition(session, user_ids=user_map, idea_ids=idea_map)
   await seed_delivery(session, user_ids=user_map, idea_ids=idea_map)
   await seed_ideathons(session, user_ids=user_map, idea_ids=idea_map)
   ```

5. Auth: `app/dependencies/phase23_auth.py` prefers `app.dependencies.auth.get_current_user` when present. Until then, send `X-User-Id` (+ optional `X-Roles`, `X-Active-Role`) for local calls.

## Enable frontend

1. Merge routes from `frontend/src/phase23_routes.tsx` into spine `App.tsx`.
2. On Idea Detail, render `<DeliveryTab ideaId={id} />` for the Delivery tab.
3. Add shell nav links: `/ideathons`, `/recognition`.
4. Prefer replacing `frontend/src/api/client.ts` with a re-export of the spine `credentials: 'include'` client once it exists.

## API surface (`/api/v1`)

### Delivery
| Method | Path |
|--------|------|
| GET | `/ideas/{idea_id}/delivery` |
| POST | `/ideas/{idea_id}/delivery/hours-requests` |
| POST | `/delivery/hours-requests/{request_id}/decide` |
| POST | `/ideas/{idea_id}/delivery/hours-log` |
| POST/DELETE | `/ideas/{idea_id}/delivery/contributors[/{user_id}]` |
| POST | `/ideas/{idea_id}/delivery/tasks` |
| PATCH | `/delivery/tasks/{task_id}` |
| POST | `/delivery/tasks/{task_id}/status` |
| POST | `/ideas/{idea_id}/delivery/updates` |
| POST | `/ideas/{idea_id}/delivery/mark-implemented` |
| POST | `/ideas/{idea_id}/delivery/impact/{entry_id}/verify` |

### Ideathons
| Method | Path |
|--------|------|
| GET/POST | `/ideathons` |
| GET | `/ideathons/{id}` |
| POST | `/ideathons/{id}/advance` |
| POST | `/ideathons/{id}/link` |
| DELETE | `/ideathons/{id}/entries/{idea_id}` |
| POST | `/ideathons/{id}/shortlist` |
| POST | `/ideathons/{id}/pitch/move\|score\|vote\|close` |
| GET | `/ideathons/{id}/tally` |
| POST | `/ideathons/{id}/winners` |
| POST | `/ideathons/{id}/handoff` |
| POST | `/ideathons/{id}/complete` |

### Recognition + Profiles
| Method | Path |
|--------|------|
| GET | `/recognition/rules` |
| GET | `/recognition/leaderboard` |
| GET | `/recognition/badges` |
| GET/POST | `/recognition/awards`, `/recognition/awards/ioq`, `/annual` |
| GET | `/recognition/users/{user_id}/ledger\|level` |
| GET | `/people/{user_id}` |

## Ownership boundary

Spine owns: docker-compose, auth OTP/JWT, core users/ideas/review, login UI, Home/Explore/Submit/Review/MyIdeas.

Phase 2+3 owns only the files under the paths listed in this README and `phase23_register.py` / `phase23_routes.tsx`.
