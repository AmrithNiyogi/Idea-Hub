# Groups & channels

First-class **Groups** with Discord-like channel navigation and a
WhatsApp-like chat transcript. Groups are creatable **without an idea**;
an idea can be linked later (at most one group per idea).

## Product model

| Concept | Notes |
|---------|--------|
| **Group** (`hub_groups`) | Name, description, members, optional `idea_id` |
| **Channels** | `#general`, `#decisions`, `#blockers` by default |
| **Messages** | Dense chat bubbles + sticky composer |
| **Meetings / MCP** | Attached to the group (Teams webhook optional) |

Idea-bound 1:1 `team_spaces` were replaced by this model (migration
`groups_001`). Existing idea spaces (if any) are migrated into groups with
the creator as owner.

## UI

| Path | Purpose |
|------|---------|
| Sidebar → **Groups** (`/groups`) | List + create (no idea required) |
| `/groups/:id` | Channel list (left) + chat (main) |
| Idea detail → Team card | **Open group** if linked, or **Create group** |

Chat UX mixes Discord (group + `#channel` switcher, topic) with WhatsApp
(bubbles, timestamps, sticky bottom composer). Styling uses Idea Hub tokens
(`.grp-*`, `.ts-*`) — not Discord/WhatsApp brand colors.

## Who can post

Group **members** (and platform `lead` / `admin` / `leadership`) can post.
Owners/admins manage channels, members, and MCP.

## API (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/groups` | List mine / create |
| GET/PATCH | `/groups/{id}` | Detail / update (incl. link idea) |
| POST/DELETE | `/groups/{id}/members…` | Add / remove members |
| POST | `/groups/{id}/channels` | Create channel |
| GET/POST | `/groups/{id}/channels/{cid}/messages` | List / post |
| GET/POST | `/groups/{id}/meetings` | List / schedule |
| GET/POST/DELETE | `/groups/{id}/mcp…` | MCP attach / discover / call |
| GET | `/ideas/{id}/group` | Linked group or `null` |

## Teams Incoming Webhook

1. Integrations → Microsoft Teams → paste Incoming Webhook URL.
2. In a group → **Schedule** → leave “Notify Microsoft Teams” checked.

## Migrate & seed

```bash
cd backend
uv run alembic upgrade head          # includes groups_001
uv run python -m app.seed.demo       # full demo (calls groups seed via phase456)
# or groups only (idempotent):
uv run python -m app.seed.groups
# restart uvicorn
```

Demo groups (after seed):

| Group | Idea | Members |
|-------|------|---------|
| Parking lot — pre-build chat | none | priya (owner), marcus, elena, tomas, sam |
| Runbook draft team | linked to runbook idea if present | marcus (owner), elena, tomas, priya |

Shared demo password: see `backend/README.md` (do not invent credentials).

If you previously applied a local `team_space_001` revision that is no longer
in the tree, stamp/reset carefully or recreate the local DB.

## Follow-ups

- Real-time websocket / SSE for channel messages
- Member picker (search users) instead of raw UUID
- Graph API calendar create beyond Incoming Webhook cards
