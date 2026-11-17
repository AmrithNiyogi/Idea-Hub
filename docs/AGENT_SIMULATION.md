# Agent simulation (local stubs)

Idea Hub ships **simulated** agents until Kompass workflows are created and wired.

## What is stubbed today

| Surface | Endpoint / path | Engine | Kompass prompt (to create) |
|---------|-----------------|--------|----------------------------|
| Agent roster / run / proposals | `POST /api/v1/agents/run`, … | `AgentGateway` → `agent_heuristics` (`mock-heuristic-v1`) | Part A / B in `KOMPASS_AGENT_PROMPTS.md` |
| **Submit ideation co-pilot** (freeform chat → form patches) | `POST /api/v1/agents/simulate/submit-assist` | `agent_simulate_service.submit_assist_turn` | `ideakonnekt-wf-submit-assist` |
| **Help / app guide** (FAQ nav only) | `POST /api/v1/agents/simulate/help` | `agent_simulate_service.help_turn` | `ideakonnekt-wf-help-guide` |
| **Author idea optimizer** (post-submit; author-only) | `POST /api/v1/agents/simulate/idea-optimize` · also `POST /agents/run` (`idea-optimizer`) | `agent_simulate_service.idea_optimize_turn` | `ideakonnekt-wf-idea-optimizer` |
| **Review intelligence** (scores + decision lean + merge `target_id`) | `POST /api/v1/agents/run` (`review-intelligence`) | `agent_heuristics.review_brief` | `ideakonnekt-wf-review-intelligence` (exists in payloads) |

| Status legend | Meaning |
|---------------|---------|
| **Simulated locally today** | Heuristic stub; UI labelled Simulated |
| **To-create in Kompass** | Prompt / workflow not yet live; create via `KOMPASS_PROMPT_CREATE_API.md` |

UI always shows **Simulated** / **Simulated — Kompass soon**. Agents **propose only** — they never write scores or decisions of record (`PUT /review/.../scores`, decide APIs remain human). Review UI **Apply suggested decision** selects a card, fills Written reason, and (for merge) prefills **Merge into** from `suggested_decision.target_id`; **Record decision** stays human and must send `target_id` when decision is merge.

**Submit assist:** blank draft OK — chat to brainstorm or refine; multi-field `patches` auto-apply on the form (live mirror + “Updated …” chips + Undo toast). Hide chat for manual-only. Not a one-field wizard.

Author optimizer **Apply** chips stage `field_patches` on Idea Detail; they do not call Review Intelligence and do not write scores.

## Config seam

```env
# backend/.env — default true
SIMULATE_AGENTS=true
```

Defined on `Settings.SIMULATE_AGENTS` (`backend/app/config/settings.py`). While true (and until a Kompass HTTP client exists), all agent UX uses local heuristics. No Kompass HTTP calls are made.

## Flip to Kompass later

1. Create prompts / workflows per `docs/KOMPASS_AGENT_PROMPTS.md` and the create-API docs (including submit-assist, help-guide, idea-optimizer).
2. Implement a Kompass adapter inside `AgentGateway` (replace / branch `_execute_simulated`).
3. Route `submit_assist_turn` / `help_turn` / `idea_optimize_turn` through the same gateway when `SIMULATE_AGENTS=false` and Kompass env is present.
4. Keep response schemas (`SubmitAssistTurnOut`, `HelpTurnOut`, `IdeaOptimizeTurnOut`, `AgentRunOut`) stable so the React clients do not need a rewrite.
5. Never inject JWT, SMTP, OTP, or SSO secrets into prompt context.

## Security notes

- Help, submit-assist, and idea-optimize scrub secret-like `key=value` patterns from user text.
- Help answers are a fixed FAQ/intent map (submit, review, roles, explore, agents, SSO/MFA high-level, admin, ideathons).
- Auth required on simulate routes (`RequireActor`).
