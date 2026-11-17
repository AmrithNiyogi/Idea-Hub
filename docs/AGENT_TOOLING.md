# Agent tooling (Cursor + Claude)

How coding agents should use project rules, skills, hooks, subagents, and the **code-review-graph** MCP in Idea Hub.

## Quick map

| Kind | Location |
|------|----------|
| Rules | `.cursor/rules/*.mdc` |
| Skills | `.cursor/skills/*/SKILL.md` (mirrored under `.claude/skills/`) |
| Hooks | `.cursor/hooks.json` + `.cursor/hooks/*` |
| Subagents | `.cursor/agents/*.md` (mirrored under `.claude/agents/`) |
| MCP | `.cursor/mcp.json` |
| Briefings | `CLAUDE.md`, `AGENTS.md` |

## Rules

| Rule | When |
|------|------|
| `idea-hub-architecture` | Always — stack, spine/phases, run commands |
| `idea-hub-frontend-parity` | Frontend TS/CSS — HTML/tokens parity, list/row patterns, scoped CSS, anti-slop (see rule body) |
| `idea-hub-backend-layering` | Backend Python — layers + secrets |
| `idea-hub-code-review-graph` | Always — when to use the graph MCP |

## Skills

Invoke by name or when the description matches:

- **idea-hub-spine** — `dev-services`, migrate, seed, uvicorn, Vite
- **idea-hub-ui-html-parity** — port UI from `idea-hub.html`
- **idea-hub-auth-otp** — Redis OTP + JWT cookies + SMTP
- **idea-hub-code-review-graph** — build/update/query the graph
- **idea-hub-pull-idea** — pull idea agent-context by UUID/URL for handoff

## Hooks

Configured in `.cursor/hooks.json`:

1. **protect-env** (`beforeShellExecution`) — denies `git add`/`commit` targeting `.env` files
2. **post-edit-hint** (`afterFileEdit`) — short context for UI/router/service/migration edits (not a formatter)

Reload: save `hooks.json` or restart Cursor; check the Hooks output channel if a hook misbehaves.

## Subagents

Ask Cursor to use:

- `idea-hub-backend` — FastAPI / Alembic / auth
- `idea-hub-frontend` — React / tokens / HTML parity
- `idea-hub-reviewer` — diff review + blast radius

## MCP: code-review-graph

### Project config (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "code-review-graph": {
      "command": "uvx",
      "args": ["code-review-graph", "serve"],
      "type": "stdio"
    }
  }
}
```

Same pattern as other DotKonnekt repos (admin / llmengine). Requires [`uv`](https://docs.astral.sh/uv/) so `uvx` is on `PATH`.

### First-time setup

```bash
cd /home/nakula/Desktop/DotKonnekt/REPOS/Idea-Hub
uvx code-review-graph register .
uvx code-review-graph build
uvx code-review-graph status
```

After large refactors: `uvx code-review-graph update` or MCP **`build_or_update_graph_tool`**.

### Verify connected

1. Cursor → **Settings → MCP** → `code-review-graph` enabled / connected
2. In chat, call **`list_graph_stats_tool`** (or ask the agent to) — expect non-zero nodes/edges
3. Namespace in this environment often appears as `user-code-review-graph`

### When to use

Relationship / blast-radius / review questions → graph tools.  
String literals, env keys, comments → Grep.

## Secrets

Never commit `backend/.env` or `frontend/.env`. Placeholders only in `*.env.example`. Demo seed accounts: `backend/README.md`.
