---
name: idea-hub-pull-idea
description: Pull an Idea Hub idea’s full agent context (markdown + structured JSON) by UUID or idea URL so Cursor/Claude can start building. Use when the user pastes an idea link/ID, asks to implement an Idea Hub idea, or mentions agent handoff / context.md.
---

# Pull Idea Hub idea → agent context

## Install (if missing)

End users: Idea Hub UI → **Build with an agent → Download skill** → extract the zip at the **target repo root** so both exist:

- `.cursor/skills/idea-hub-pull-idea/SKILL.md`
- `.claude/skills/idea-hub-pull-idea/SKILL.md`

Or `GET /api/v1/agent-handoff/skill-pack.zip` (auth cookie / Bearer). First-time paste from **Copy for Cursor / Claude** already embeds full context — this skill is for re-fetch / URL handoff.

## When to use

- User gives an idea UUID or URL like `/ideas/<uuid>` or `http://localhost:5173/ideas/<uuid>`
- User asks to “build this idea”, “implement from Idea Hub”, or “pull agent context”

## Env

| Variable | Purpose | Example |
|----------|---------|---------|
| `IDEA_HUB_API_URL` | API origin (no trailing slash); preferred for agents | `http://127.0.0.1:8000` |
| `VITE_API_BASE_URL` | Same origin used by the Vite app | `http://localhost:8000` |

Resolve base as: `IDEA_HUB_API_URL` → else `VITE_API_BASE_URL` → else `http://127.0.0.1:8000`.

Endpoint (auth required):

```http
GET {base}/api/v1/ideas/{idea_id}/agent-context
```

Auth: session cookie from a logged-in browser, or `Authorization: Bearer <access_token>`.

Never put SMTP passwords, JWT secrets, or OTP codes into prompts.

## Steps

1. **Parse idea id** from UUID or URL path `/ideas/<uuid>` (ignore query `?tab=`).
2. **Fetch** agent-context with credentials / Bearer.
3. **Prefer** response fields:
   - `prompts.cursor` when running in Cursor
   - `prompts.claude` when running in Claude Code
   - `markdown` for a neutral pack / writing `context.md`
4. **Confirm target repo** with the user:
   - Default Idea Hub checkout hint: `/home/nakula/Desktop/DotKonnekt/REPOS/Idea-Hub`
   - If they name another product repo, implement there instead
5. **Plan then build** against problem / solution / success metrics. Keep changes additive; match existing architecture.

## curl example

```bash
BASE="${IDEA_HUB_API_URL:-${VITE_API_BASE_URL:-http://127.0.0.1:8000}}"
IDEA_ID="<uuid>"
curl -sS -H "Authorization: Bearer $IDEA_HUB_TOKEN" \
  "$BASE/api/v1/ideas/$IDEA_ID/agent-context" | jq -r .prompts.cursor
```

Cookie-based (after browser login) also works with `-b` / `credentials: include` from the UI.

## Output contract (summary)

JSON includes: `idea_id`, `title`, `status`, `category`, `problem`, `solution`, `beneficiaries`, `success_metrics`, `tags`, `owner` / redacted `author`, `status_history`, `latest_decision`, `comments`, optional `delivery`, `related_links`, `markdown`, `prompts.{cursor,claude}`.

Full docs: `docs/AGENT_HANDOFF.md`.
