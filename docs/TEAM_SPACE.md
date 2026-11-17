# Team collaboration space

Per-idea **team space** with Discord-like channels, meeting scheduling
(Microsoft Teams Incoming Webhook), and attachable **custom MCP** endpoints.

## UI

| Path | Purpose |
|------|---------|
| Idea → **Channels** tab | Channel list + message pane, Schedule, MCP drawer |
| `/integrations/teams` | Connect Incoming Webhook (personal or org default) |

Default channels on first open: `#general`, `#decisions`, `#blockers`.

## Who can post

Authors, co-authors, owner, accepted collaborators, delivery contributors,
plus roles `lead` / `admin` / `leadership`. Others can view live idea spaces;
drafts stay private to the team.

## API (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/ideas/{id}/team-space` | Get or create space + channels |
| POST | `/ideas/{id}/team-space/channels` | Create channel (manage) |
| GET/POST | `/ideas/{id}/team-space/channels/{cid}/messages` | List / post |
| GET/POST | `/ideas/{id}/team-space/meetings` | List / schedule |
| GET/POST | `/ideas/{id}/team-space/mcp` | List / attach MCP |
| POST | `/ideas/{id}/team-space/mcp/{mcp_id}/discover` | `tools/list` |
| POST | `/ideas/{id}/team-space/mcp/{mcp_id}/call` | `tools/call` |
| DELETE | `/ideas/{id}/team-space/mcp/{mcp_id}` | Remove MCP |

## Teams Incoming Webhook

1. In Teams: channel → **Connectors** → **Incoming Webhook** → copy URL.
2. Idea Hub → **Integrations** → **Microsoft Teams** → paste URL (personal
   or admin org default).
3. On an idea **Channels** tab → **Schedule** → leave “Notify Microsoft Teams”
   checked. Hub posts a MessageCard and optionally announces in-channel.

Credentials use the same encrypted `tracker_connections` table as ClickUp/Jira
(`provider_id=teams`, scope user/org). Secrets are never returned by the API.

## Custom MCP

Attach a JSON-RPC HTTP endpoint to the idea space (or use the **stub** catalog).

### Expected tools (Hub understands)

| Tool | Purpose |
|------|---------|
| `schedule_meeting` | Hub schedules locally (Teams + channel announce). Args: `title`, `starts_at`, optional `ends_at`, `description`, `join_url`, `channel_slug`, `notify_teams`. |
| `post_channel_message` | Documented for remote MCPs; stub echoes. |
| `list_channels` | Documented for remote MCPs. |

### HTTP contract (MVP)

```http
POST {endpoint_url}
Content-Type: application/json
Authorization: <optional>

{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call",
 "params":{"name":"schedule_meeting","arguments":{…}}}
```

SSE / stdio transports are out of scope; use `transport=stub` until you host
an HTTP MCP. Align Kompass/ngrok agent tools with
[KOMPASS_TOOLS_NGROK.md](./KOMPASS_TOOLS_NGROK.md) when exposing Hub APIs
as agent tools.

### Add your own later

1. Run an MCP server that speaks JSON-RPC over HTTPS (or tunnel via ngrok).
2. On Channels → MCP → uncheck stub → paste URL + auth header.
3. **Discover** refreshes `tools/list`. Calling `schedule_meeting` is always
   handled by Hub so Teams + channel announce stay consistent.

## Migrate

```bash
cd backend
uv run alembic upgrade head   # includes team_space_001
# restart uvicorn
```

## Follow-ups

- Real-time websocket / SSE for channel messages
- Graph API calendar create (beyond Incoming Webhook cards)
- Full MCP Streamable HTTP + SSE host inside Idea Hub
- Per-channel permissions / @mentions / reactions
