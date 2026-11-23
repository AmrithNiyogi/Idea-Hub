# Tracker providers (ClickUp, Jira, custom)

KonnektIdea can push accepted / in-prototype ideas into external work trackers.
Integrations are **pluggable**: core flow never hardcodes vendors.

For **org default vs personal override**, the Integrations settings page,
**Notion docs**, and coming-soon Sheets/Teams stubs, see
[INTEGRATIONS.md](./INTEGRATIONS.md).

## Post-approval flow

1. Review decides **accept** → idea status `accepted` (ready for development).
2. Owner requests innovation hours; leadership approve → status `prototype` and a delivery project opens.
3. Connect the tracker once under **Integrations** (personal) or ask an admin to set an **organization default**.
4. On the Delivery tab, owners/leads **Create task** or **Link existing** using the effective connection (no re-entry of tokens per idea).

Statuses that allow linking: `accepted`, `prototype`, `implemented`.  
Creating a *new* remote task: `accepted` or `prototype` only.

## Built-in providers

| `provider_id` | Auth | Notes |
|---------------|------|--------|
| `clickup` | Personal API token + list id | Creates tasks via ClickUp REST v2 |
| `jira` | Email + API token + site URL + project key | Jira Cloud REST v3 |
| `custom_webhook` | HTTPS create URL + optional auth header | Stub for a tracker you build later |

List trackers at runtime: `GET /api/v1/trackers/providers`.  
Full catalog (including Notion docs + coming-soon stubs):
`GET /api/v1/integrations/providers`.

## Configure locally

1. Migrate: `uv run alembic upgrade head` (through `integrations_001`).
2. Copy placeholders from `backend/.env.example` — OAuth client ids are optional for MVP.
3. In the UI (**Integrations**):
   - **ClickUp**: token from ClickUp → Settings → Apps; paste a list id.
   - **Jira**: Atlassian API token + `https://your-domain.atlassian.net` + project key.
   - **Custom**: HTTPS endpoint that implements the webhook contract below.
4. Admins can set the same providers as **organization defaults** so teammates inherit them until they connect their own.

Credentials are encrypted with Fernet derived from `JWT_SECRET_KEY`. Rotating that secret requires reconnecting trackers. Prefer a dedicated `TRACKER_CREDENTIALS_KEY` later.

## How to add a tracker you build later

### Option A — Webhook (fastest)

1. Implement `POST /your/create-task` accepting:

```json
{
  "title": "…",
  "description": "…",
  "idea_id": "uuid",
  "idea_url": "https://…/ideas/uuid",
  "status_hint": "prototype",
  "tags": [],
  "extra": {}
}
```

2. Respond `2xx` with JSON: `{ "id": "…", "url": "https://…", "key": "…" }`.
3. In KonnektIdea, connect provider **Custom tracker (webhook)** with that URL (+ auth header).

No code change required.

### Option B — First-class `TrackerProvider` (recommended)

1. Create `backend/app/trackers/my_tracker.py` implementing the contract in `app/trackers/base.py`:

   - Attributes: `id`, `display_name`, `description`, `auth_mode`, `connect_fields`
   - Methods: `validate_connection`, `create_issue`, `resolve_existing`, `get_task`, `update_task`

2. Register it in `app/trackers/registry.py` inside `_ensure_builtins()` (or call `register_provider(MyTrackerProvider())` from an imported module).

3. Restart the API. `GET /trackers/providers`, `GET /integrations/providers`, and the Integrations + Delivery UIs list the new provider automatically — no router/UI vendor hardcoding.

Required methods:

| Method | Responsibility |
|--------|----------------|
| `validate_connection(credentials)` | Probe remote API; return `ConnectionProbe` or raise `ValueError` |
| `create_issue(credentials, payload)` | Create remote work item → `ExternalIssue` |
| `resolve_existing(credentials, id_or_url)` | Resolve existing item for link-only mode |
| `get_task(credentials, external_id)` | Live snapshot → `RemoteTask` (title, status, assignees, options) |
| `update_task(credentials, external_id, payload)` | Write-back status/title → refreshed `RemoteTask` |

Do **not** put secrets in git. Collect them via `connect_fields` (marked `secret=True`); the service encrypts the blob.

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/trackers/providers` | Tracker registry catalog |
| GET | `/trackers/connections/effective` | Effective connection per tracker (user → org → none) |
| GET/POST | `/trackers/connections` | List / connect **personal** |
| DELETE | `/trackers/connections/{id}` | Disconnect personal |
| GET/POST/DELETE | `/integrations/*` | Broader catalog + personal + **org** (admin) — see INTEGRATIONS.md |
| GET/POST | `/ideas/{id}/tracker-links` | List / create-or-link (`connection_id` or `provider_id`) |
| GET | `/ideas/{id}/tracker-links/live` | List links with **live** remote title/status/assignees/options |
| GET | `/ideas/{id}/tracker-links/{link_id}/live` | Refresh one linked task from the remote API |
| PATCH | `/ideas/{id}/tracker-links/{link_id}/remote` | Write-back `status` (and optional `title`) to the remote tracker |
| DELETE | `/ideas/{id}/tracker-links/{link_id}` | Unlink (remote item kept) |

UI: idea detail **Tracker** tab (`?tab=tracker`) shows live tasks; **Delivery** still creates/links.

### ClickUp status mapping

- Live fetch: `GET /api/v2/task/{id}` → `status.status` (name), color, type; assignees from `assignees[]`.
- Status options: `GET /api/v2/list/{list_id}` → `statuses[]` (from the task’s list, else the connected default list).
- Write-back: `PUT /api/v2/task/{id}` with `{ "status": "<status name>" }` — ClickUp expects the **status name string** (e.g. `in progress`), not the status UUID.

### Jira / custom webhook

- Jira: live via issue fields; status change uses **transitions** (`GET …/transitions` → `POST …/transitions` matching target status name).
- Custom webhook: optional `POST` actions `get_task` / `update_task` (see provider module). Link-only remains best-effort if the webhook omits these.

## Follow-ups

- OAuth authorization-code flows using `CLICKUP_*` / `JIRA_*` client settings
- Sync status / webhooks from remote → KonnektIdea delivery tasks
- Dedicated credential encryption key independent of JWT
- Notion public OAuth using `NOTION_CLIENT_*` (MVP uses internal integration secret)
- Promote Sheets / Teams stubs (see INTEGRATIONS.md)
