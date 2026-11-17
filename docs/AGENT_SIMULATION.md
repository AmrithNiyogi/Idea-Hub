# Agent simulation + AI Studio execute

Idea Hub ships **simulated** agents by default. When AI Studio / Kompass env is
configured and `SIMULATE_AGENTS=false`, chat and review surfaces call the real
**runs/execute** contract (same as chatbot-admin / DotAgent widget).

## Authoritative execute contract

```http
POST https://aistudio-apigateway-v2-staging.dotkonnekt.com/api/v2/runs/execute
```

| Header | Required | Notes |
|--------|----------|--------|
| `accept` | yes | `*/*` |
| `Content-Type` | yes | `application/json` |
| `X-Tenant-ID` | yes | e.g. `devtest` |
| `project-slug` | yes* | Resolves project for public/project-scoped execute (*or logged-in user) |
| `X-Authorization` | optional | Tool auth token; forwarded to tools. **Server-side only** — never embed in the browser |

```json
{
  "agent_id": "<kompass agent id or slug>",
  "input": "<string or JSON string>",
  "conversation_id": "<optional; omit to create a new thread>"
}
```

- Reply carries `conversation_id` — **echo it** on later turns for the same chat.
- Sync JSON completion (200) or 202 + poll `GET /api/v2/runs/{run_id}` (Idea Hub client polls like `aistudio-chatbot-ui-v2`).
- SSE create/stream (`POST /api/v2/runs`) exists on the gateway but Idea Hub uses **execute** only for now.

Source of truth in AI Studio:

| Path | Role |
|------|------|
| `AI STUDIO V2/aistudio-chatbot-ui-v2/.../src/api-client.js` | Browser execute client |
| `AI STUDIO V2/aistudio-chatbot-ui-v2/.../src/chat-widget.js` | `<dotagent-chat>` widget |
| `AI STUDIO V2/aistudio-admin-ui-v2/.../embeddable-code-modal.tsx` | Curl snippet (tenant + project-slug + X-Authorization) |
| `AI STUDIO V2/aistudio-apigateway-v2/.../agenticExecutionV2/runs.py` | Gateway route |

## Hub surface → Kompass agent_id + input

| Hub surface | Hub key / route | Env agent id | `input` shape | `conversation_id` |
|-------------|-----------------|--------------|---------------|-------------------|
| Submit assist | `POST …/simulate/submit-assist` | `AISTUDIO_AGENT_SUBMIT_ASSIST` | JSON string `{"draft","message","awaiting_field"}` | Per Submit chat thread |
| Help FAB | `POST …/simulate/help` | `AISTUDIO_AGENT_HELP` | Plain user `message` string | Per Help FAB thread |
| Idea optimizer | `POST …/simulate/idea-optimize` · `/agents/run` `idea-optimizer` | `AISTUDIO_AGENT_IDEA_OPTIMIZER` | JSON string `{"idea","message","messages"}` | Per optimizer session |
| Review intelligence | `/agents/run` `review-intelligence` | `AISTUDIO_AGENT_REVIEW_INTELLIGENCE` | JSON string idea + comments/votes/similar | Usually one-shot |

Prompt slugs (Prompt Engine / workflow LLM) remain `ideakonnekt-wf-*` — see
`KOMPASS_AGENT_PROMPTS.md`. The **execute** `agent_id` is the **Kompass Smart
Agent** id or slug created in admin (may differ from the prompt slug until you
align them). Fill the four `AISTUDIO_AGENT_*` env vars after agents exist.

Expected structured agent outputs (when using JSON agents/prompts):

| Surface | Prefer JSON fields |
|---------|--------------------|
| Submit assist | `reply`, `patches`, `awaiting_field`, `done` |
| Help | `reply`, `topic`, `links[{label,href}]` |
| Idea optimizer | `reply`, `field_patches`, `focus_fields` |
| Review intelligence | Same shape as heuristic `review_brief` (scores, decision lean, `target_id`) |

If the agent returns plain text, Idea Hub uses it as `reply` / wraps it.

## What is stubbed today (default)

| Surface | Endpoint / path | Engine while simulating |
|---------|-----------------|-------------------------|
| Agent roster / run / proposals | `POST /api/v1/agents/run`, … | `AgentGateway` → heuristics (`mock-heuristic-v1`) |
| Submit ideation co-pilot | `POST /api/v1/agents/simulate/submit-assist` | `agent_simulate_service` |
| Help / app guide | `POST /api/v1/agents/simulate/help` | FAQ intent map |
| Author idea optimizer | `POST …/simulate/idea-optimize` · `idea-optimizer` | `agent_simulate_service` |
| Review intelligence | `/agents/run` `review-intelligence` | `agent_heuristics.review_brief` |

Agents **propose only** — they never write scores or decisions of record.

## Config seam

```env
SIMULATE_AGENTS=true   # default: always stubs

AISTUDIO_API_BASE_URL=https://aistudio-apigateway-v2-staging.dotkonnekt.com
AISTUDIO_TENANT_ID=devtest
AISTUDIO_PROJECT_SLUG=<your-project-slug>
AISTUDIO_TOOL_AUTH_TOKEN=   # optional X-Authorization
AISTUDIO_EXECUTE_TIMEOUT_SECONDS=120
AISTUDIO_AGENT_SUBMIT_ASSIST=
AISTUDIO_AGENT_HELP=
AISTUDIO_AGENT_IDEA_OPTIMIZER=
AISTUDIO_AGENT_REVIEW_INTELLIGENCE=
```

**Live gate:** `SIMULATE_AGENTS=false` **and** base URL + tenant + project-slug set.
Per-route also requires the matching `AISTUDIO_AGENT_*` id (else 503).

Implementation:

| Module | Role |
|--------|------|
| `app/services/aistudio_execute_client.py` | Headers, POST execute, 202 poll, normalize |
| `app/services/agent_live_turns.py` | Branch simulate vs live for chat surfaces |
| `app/services/agent_gateway.py` | Live branch for `idea-optimizer` / `review-intelligence` |

## Flip to live

1. Create prompts / Smart Agents per `KOMPASS_AGENT_PROMPTS.md` + create-API docs.
2. Put real project-slug + agent ids in `backend/.env` (never commit secrets).
3. Set `SIMULATE_AGENTS=false`.
4. Keep response schemas stable; clients already accept optional `conversation_id`.
5. Never inject JWT, SMTP, OTP, or SSO secrets into agent `input`.

## Help FAB vs DotAgent widget

| Copy from chatbot-admin / `aistudio-chatbot-ui-v2` | Adapt for Idea Hub |
|----------------------------------------------------|--------------------|
| Launcher speech-bubble silhouette + brand mark | Use `/ideakonnect-mark.svg` (not `?` circle) |
| Panel: header / message list / textarea / Send / Clear | React `HelpChatFab` + Idea Hub tokens |
| `POST /api/v2/runs/execute` + optional `conversation_id` | Hub proxies via `/agents/simulate/help`; echo `conversation_id` |
| Headers `X-Tenant-ID`, `project-slug` | Server-side only in `aistudio_execute_client` |
| Optional `X-Authorization` for tools | Backend `.env` only — never in the browser widget |
| Direct browser → gateway | Cookie-auth Idea Hub API; keep secrets off the client |

Entry component: `frontend/src/components/HelpChatFab.tsx` (mounted from `AppShell`).

## Security notes

- Help, submit-assist, and idea-optimize scrub secret-like `key=value` patterns from user text (simulate path).
- Auth required on simulate routes (`RequireActor`).
- Tool auth token stays in backend env only.
