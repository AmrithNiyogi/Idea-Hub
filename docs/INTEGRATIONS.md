# Integrations (org default + personal override)

Idea Hub connects to external tools through a shared **Integrations** surface.
Trackers (ClickUp, Jira, custom webhook) are fully wired today. Docs / chat /
spreadsheet tools are registered as **coming soon** stubs so the UI and
registry stay ready for Google Sheets, Notion, and Microsoft Teams.

## Two-tier connections

| Scope | Who sets it | When it is used |
|-------|-------------|-----------------|
| `user` | Any signed-in user (own credentials) | Preferred when present for that provider |
| `organization` | Administrator | Fallback when the user has no personal connection |

**Resolution order** (create / link from Delivery):

1. Explicit `connection_id` (must be the actor’s personal connection **or** an org default)
2. Else `provider_id` → personal connection → org default
3. Else prompt to connect under **Integrations**

Credentials stay Fernet-encrypted in `tracker_connections` (same table for both
scopes). Secrets are never returned by the API.

## UI

| Path | Purpose |
|------|---------|
| `/integrations` | **My integrations** + **Organization defaults** (admin) |
| Sidebar → Integrations | Same page |
| Account menu → Integrations | Same page |
| Idea → Delivery → External trackers | Uses effective connections; link to Integrations if none |

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/integrations/providers` | Full catalog (trackers + stubs); `?category=` optional |
| GET | `/integrations/connections/effective` | Per provider: `source` = `user` \| `organization` \| `none` |
| GET/POST | `/integrations/connections` | List / create personal connections |
| DELETE | `/integrations/connections/{id}` | Disconnect personal |
| GET/POST | `/integrations/org/connections` | Org defaults (**admin**) |
| DELETE | `/integrations/org/connections/{id}` | Remove org default (**admin**) |

Tracker-specific helpers remain under `/trackers/*` (providers, effective,
idea links). Prefer Integrations for day-to-day connect/disconnect.

## Categories & future providers

| Category | Today | Later |
|----------|-------|-------|
| `tracker` | clickup, jira, custom_webhook | any `TrackerProvider` |
| `sheets` | `google_sheets` stub | OAuth + sheet mapping |
| `docs` | `notion` stub | OAuth + database sync |
| `chat` | `teams` stub | Bot / webhook notifications |

### Adding a new tracker

See [TRACKER_PROVIDERS.md](./TRACKER_PROVIDERS.md) — implement `TrackerProvider`,
register in `app.trackers.registry`. It appears automatically in Integrations
as category `tracker` / status `available`.

### Promoting a stub (Sheets / Notion / Teams)

1. Replace the stub in `app/integrations/base.py` (or `register_integration`)
   with `status="available"` and real `connect_fields`.
2. Add validate/connect logic (OAuth or token) — reuse `TrackerConnection`
   storage by `provider_id` + `scope`, or a dedicated service if the payload
   differs.
3. Expose actions from the Integrations page (already driven by the catalog).

## Migrate / restart

```bash
cd backend
uv run alembic upgrade head   # includes integrations_001
# restart uvicorn
```

Existing personal connections keep `scope=user`. Org defaults are new rows
with `scope=organization` and `user_id` null.

## How to test org default vs personal override

1. As **admin**: Integrations → Organization defaults → Set default for ClickUp
   (or Jira / custom).
2. As a **non-admin** with no personal ClickUp: open an accepted idea → Delivery
   → External trackers. The dropdown should show the org default.
3. As that user: Integrations → Connect ClickUp with *your* token.
4. Return to Delivery: the dropdown should prefer **my connection**; create/link
   uses the personal credentials.
5. Disconnect personal: Delivery falls back to org default again.
6. Non-admin cannot call `/integrations/org/connections` (403).
