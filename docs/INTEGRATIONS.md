# Integrations (org default + personal override)

IdeaKonnekt connects to external tools through a shared **Integrations** surface.
Trackers (ClickUp, Jira, custom webhook) and **Notion** (docs) are fully wired.
Google Sheets and Microsoft Teams remain **coming soon** stubs.

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
scopes and for Notion). Secrets are never returned by the API.

## UI

| Path | Purpose |
|------|---------|
| `/integrations` | **My integrations** + **Organization defaults** (admin) |
| `/integrations/notion` | Connect Notion + docs setup steps |
| Sidebar → Integrations | Same page |
| Account menu → Integrations | Same page |
| Idea → Delivery → External trackers | ClickUp / Jira / custom |
| Idea → Delivery → Notion docs | Create / link Notion pages |

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/integrations/providers` | Full catalog (trackers + Notion + stubs); `?category=` optional |
| GET | `/integrations/connections/effective` | Per provider: `source` = `user` \| `organization` \| `none` |
| GET/POST | `/integrations/connections` | List / create personal connections |
| DELETE | `/integrations/connections/{id}` | Disconnect personal |
| GET/POST | `/integrations/org/connections` | Org defaults (**admin**) |
| DELETE | `/integrations/org/connections/{id}` | Remove org default (**admin**) |
| GET/POST | `/ideas/{id}/tracker-links` | Create/link remote item (trackers **or** Notion) |

Tracker-specific catalog remains under `/trackers/*` (excludes Notion). Prefer
Integrations for day-to-day connect/disconnect.

## Categories & providers

| Category | Today | Later |
|----------|-------|-------|
| `tracker` | clickup, jira, custom_webhook | any `TrackerProvider` |
| `docs` | **notion** (internal integration secret) | OAuth public integration |
| `sheets` | `google_sheets` stub | OAuth + sheet mapping |
| `chat` | **teams** Incoming Webhook | Graph bot / richer cards |

Team channels, meeting schedule, and custom MCP: idea **Channels** tab —
[TEAM_SPACE.md](./TEAM_SPACE.md).

### Adding a new tracker

See [TRACKER_PROVIDERS.md](./TRACKER_PROVIDERS.md) — implement `TrackerProvider`,
register in `app.trackers.registry`. It appears automatically in Integrations
as category `tracker` / status `available`.

### Notion (docs) — pages first

**Primary path:** create / update **Notion pages (documents)** under a parent
page. Idea title becomes the page title; problem + solution (and light markdown)
become Notion blocks. Database row create is **optional / Advanced**.

**Auth (local/dev):** Notion **internal integration** secret.

1. Open [My integrations](https://www.notion.so/my-integrations) → **New integration**.
2. Copy the **Internal Integration Secret** (`secret_…`).
3. In Notion, open the **parent page** where idea docs should live → **•••** →
   **Connections** → invite your integration.
4. Copy the page ID from the URL (32-char hex at the end).
5. IdeaKonnekt → **Integrations → Notion** → Connect:
   - Internal integration secret
   - **Parent page ID** (required for document create)
   - Advanced (optional): database ID + title property for row create
6. On an **accepted** / **prototype** idea → **Delivery → Notion docs** →
   **Create Notion page** or **Link existing** → **Open page**.
7. Later: **Append content** pushes an updated Problem / Solution section onto
   the linked page (does not delete prior blocks).

Optional env placeholders for a future public OAuth flow (not required for MVP):

```bash
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=
NOTION_REDIRECT_URI=http://localhost:8000/api/v1/integrations/notion/oauth/callback
```

Never put the integration secret in git — only in the UI connection form (encrypted
at rest) or a private local note.

### Teams (chat) — Incoming Webhook MVP

1. Teams channel → **Connectors** → **Incoming Webhook** → copy HTTPS URL.
2. IdeaKonnekt → **Integrations → Microsoft Teams** → paste URL (personal or org).
3. Idea → **Channels** → **Schedule** → “Notify Microsoft Teams” posts a
   MessageCard; optionally announces in the idea channel.

Webhook URLs are encrypted like other connection secrets. See
[TEAM_SPACE.md](./TEAM_SPACE.md).

### Promoting another stub (Sheets)

1. Implement an adapter under `app/integrations/` (same connect/create/link
   surface as `TrackerProvider`) and register it in `app.integrations.adapters`.
2. Set `integration_category` (`sheets` / `chat` / `docs`).
3. Remove the matching entry from `FUTURE_STUBS` in `app/integrations/base.py`.
4. Restart the API — Integrations catalog picks it up automatically.

## Migrate / restart

Notion/Teams reuse `tracker_connections`. Team channels need `team_space_001`:

```bash
cd backend
uv run alembic upgrade head   # through team_space_001
# restart uvicorn
```

Reconnect integrations only when rotating `JWT_SECRET_KEY` (Fernet key).

## How to test org default vs personal override

1. As **admin**: Integrations → Organization defaults → Set default for ClickUp
   (or Notion).
2. As a **non-admin** with no personal connection: open an accepted idea → Delivery.
   The panel should show the org default.
3. As that user: Integrations → Connect with *your* credentials.
4. Return to Delivery: panels prefer **my connection**.
5. Disconnect personal: Delivery falls back to org default again.
6. Non-admin cannot call `/integrations/org/connections` (403).
