# Kompass workflows: one flow per workflow prompt

Nine workflow prompts (Part A in `KOMPASS_AGENT_PROMPTS.md`) → nine flows. Each flow is a chain of components:

```text
init (Input) → api (0..N reads) → llm (prompt) → adapter (parse) → output
```

The Ideathon agents (Cluster, Rank, Pitch) are **agent** prompts, not workflow prompts. They run as the team `idea-konnekt-ideathon` (see [Ideathon team](#ideathon-team-not-a-workflow)).

## Conventions

- **Component types** match the files in `workflowengine/schema/component_types/`: `init`, `api`, `llm`, `adapter`, `output`, plus `conditional` and `guardrail` where a flow uses them. ASSUMPTION: the `type` literals are the file names; confirm against the Workflow Weaver palette on the first build.
- **Placeholders** are `{{name}}`. A node's input maps from the Input node (`{{input.<field>}}`) or from an earlier node's output (`{{<node>.<field>}}`). ASSUMPTION: this is the syntax the workflow engine resolves for node inputs; verify on the first run.
- **Read APIs** are the internal Hub routes listed in `KOMPASS_DEV_SETUP_RUNBOOK.md` Step 2. They are not built yet (see "Open items"). Until they exist, use a mock that returns the sample shape.
- **Guardrails** sit on each `llm` node's output, and on any `api` result that carries user text (runbook Step 7).
- **Human approval** stays in the Idea Hub after `output`. No flow writes to the database.

---

## 1. Idea Intelligence — `ideakonnekt-wf-idea-intelligence`

Runs on submit / draft assist. Temperature 0.20. Prompt variables: `idea_json`, `taxonomy_json`, `similar_ideas_json`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | fields: `idea_id`, `title`, `problem`, `solution`, `tags`, `category_id` | caller |
| 2 | Taxonomy | `api` | `GET /internal/agents/config/taxonomy` | — |
| 3 | Similar ideas | `api` | `POST /internal/agents/ideas/similar`, body `{title, problem, tags}` | `{{input.title}}`, `{{input.problem}}`, `{{input.tags}}` |
| 4 | Intelligence | `llm` | prompt `ideakonnekt-wf-idea-intelligence` | `idea_json` ← `{{input}}`; `taxonomy_json` ← `{{taxonomy.body}}`; `similar_ideas_json` ← `{{similar.body}}` |
| 5 | Guardrail | `guardrail` | on node 4 output | — |
| 6 | Parse | `adapter` | `IdeaIntelligenceResult` | `{{intelligence.output}}` |
| 7 | Output | `output` | `{ intelligence }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6, 6→7.

Output keys (from the prompt): `ideaId`, `suggestedCategory`, `suggestedTags`, `similarIdeas`, `missingFields`, `duplicateRisk`.

---

## 2. Idea Enhancement — `ideakonnekt-wf-idea-enhancement`

Runs on the Submit page, one field at a time. Temperature 0.30. Variables: `idea_json`, `taxonomy_json`, `field`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `idea_id`, `field` (one of title, problem, solution, beneficiaries, success_metrics), plus the idea fields | caller |
| 2 | Taxonomy | `api` | `GET /internal/agents/config/taxonomy` | — |
| 3 | Enhancement | `llm` | prompt `ideakonnekt-wf-idea-enhancement` | `idea_json` ← `{{input}}`; `taxonomy_json` ← `{{taxonomy.body}}`; `field` ← `{{input.field}}` |
| 4 | Guardrail | `guardrail` | on node 3 output | — |
| 5 | Parse | `adapter` | enhancement result | `{{enhancement.output}}` |
| 6 | Output | `output` | `{ enhancement }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6.

---

## 3. Review Intelligence — `ideakonnekt-wf-review-intelligence`

Runs in the review workspace, after a reviewer records a decision (runbook Flow C). Temperature 0.10 (heavy model). Variables: `idea_json`, `thread_json`, `past_decisions_json`, `similar_ideas_json`, `mode`, `score_scale_json`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `idea_id`, `panel_id`, `mode` (`brief`, `integrity`, `consistency`), `decision`, `scores` | caller |
| 2 | Idea | `api` | `GET /internal/agents/ideas/{{input.idea_id}}` | `{{input.idea_id}}` |
| 3 | Thread | `api` | `GET /internal/agents/ideas/{{input.idea_id}}/thread` | `{{input.idea_id}}` |
| 4 | Past decisions | `api` | `GET /internal/agents/panels/{{input.panel_id}}/decisions` | `{{input.panel_id}}` |
| 5 | Similar ideas | `api` | `POST /internal/agents/ideas/similar` | from node 2 |
| 6 | Review | `llm` | prompt `ideakonnekt-wf-review-intelligence` | `idea_json` ← node 2; `thread_json` ← node 3; `past_decisions_json` ← node 4; `similar_ideas_json` ← node 5; `mode` ← `{{input.mode}}`; `score_scale_json` ← constant from the Hub |
| 7 | Guardrail | `guardrail` | on node 6 output | — |
| 8 | Parse | `adapter` | review brief | `{{review.output}}` |
| 9 | Output | `output` | `{ brief }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6, 6→7, 7→8, 8→9. Nodes 2–5 can run in parallel after 1; keep them sequential in the first build.

---

## 4. Innovation Workflow (nudges) — `ideakonnekt-wf-innovation-workflow`

Runs on the scheduler or the Pipeline / Home page (runbook Flow B). Temperature 0.25, fast model. Variable: `nudge_json`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `ideaId`, `condition`, `daysInStage`, `slaDays`, `ideaTitle`, `targetUserId` | caller (the Hub computes SLA first) |
| 2 | Nudge | `llm` | prompt `ideakonnekt-wf-innovation-workflow` | `nudge_json` ← `{{input}}` |
| 3 | Guardrail | `guardrail` | on node 2 output | — |
| 4 | Parse | `adapter` | `WorkflowNudge` | `{{nudge.output}}` |
| 5 | Output | `output` | `{ nudge }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5. No API node, because the Hub passes the whole nudge in. Add an `api` node for `GET /internal/agents/pipeline/stuck` only if the input becomes a filter.

---

## 5. Recognition — `ideakonnekt-wf-recognition`

Runs after a decision, or on the Recognition page (runbook Flows C and E). Temperature 0.20, fast model. Variables: `recognition_context_json`, `mode`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `mode` (for example `contributions`, `award_nomination`), `idea_id` (optional), `period` | caller |
| 2 | Context | `api` | `GET /internal/agents/recognition/context` | `{{input.period}}` |
| 3 | Recognition | `llm` | prompt `ideakonnekt-wf-recognition` | `recognition_context_json` ← `{{context.body}}`; `mode` ← `{{input.mode}}` |
| 4 | Guardrail | `guardrail` | on node 3 output | — |
| 5 | Parse | `adapter` | recognition result | `{{recognition.output}}` |
| 6 | Output | `output` | `{ recognition }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6. Points are never decided here. The Hub's rules engine writes the ledger.

---

## 6. Innovation Analytics — `ideakonnekt-wf-innovation-analytics`

Runs on Insights and Home (runbook Flow E). Temperature 0.25. Variables: `snapshot_json`, `period`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `period` (for example `quarter`, `year`, `all`) | caller |
| 2 | Snapshot | `api` | `GET /internal/agents/analytics/snapshot` | `{{input.period}}` |
| 3 | Analytics | `llm` | prompt `ideakonnekt-wf-innovation-analytics` | `snapshot_json` ← `{{snapshot.body}}`; `period` ← `{{input.period}}` |
| 4 | Guardrail | `guardrail` | on node 3 output | — |
| 5 | Parse | `adapter` | analytics insights | `{{analytics.output}}` |
| 6 | Output | `output` | `{ insights }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6. Read-only.

---

## 7. Submit Assist — `ideakonnekt-wf-submit-assist`

The Submit page co-pilot. Each chat turn is one run. The Hub keeps the conversation and sends the history each time. Temperature 0.40. Variables: `draft_json`, `taxonomy_json`, `message`, `history_json`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `draft` (object), `message` (string), `history` (array) | caller |
| 2 | Taxonomy | `api` | `GET /internal/agents/config/taxonomy` | — |
| 3 | Assist | `llm` | prompt `ideakonnekt-wf-submit-assist` | `draft_json` ← `{{input.draft}}`; `taxonomy_json` ← `{{taxonomy.body}}`; `message` ← `{{input.message}}`; `history_json` ← `{{input.history}}` |
| 4 | Guardrail | `guardrail` | on node 3 output | — |
| 5 | Parse | `adapter` | `SubmitAssistTurn` | `{{assist.output}}` |
| 6 | Output | `output` | `{ reply, patches, awaiting_field, done }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6. The Hub applies `patches` to the draft. The flow never saves anything.

---

## 8. Help Guide — `ideakonnekt-wf-help-guide`

The global help button. Temperature 0.20, fast model. Variables: `message`, `role_json`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `message` (string), `role` (string) | caller |
| 2 | Help | `llm` | prompt `ideakonnekt-wf-help-guide` | `message` ← `{{input.message}}`; `role_json` ← `{{input.role}}` |
| 3 | Guardrail | `guardrail` | on node 2 output | — |
| 4 | Parse | `adapter` | help reply | `{{help.output}}` |
| 5 | Output | `output` | `{ reply }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5. No API node. The help guide never reads or changes idea data, and it never receives an access token.

---

## 9. Idea Optimizer — `ideakonnekt-wf-idea-optimizer`

The author's chat on their own idea. It proposes patches and never scores or decides. Temperature 0.35. Variables: `idea_json`, `message`, `history_json`, `taxonomy_json`.

| # | Node | Type | Config | Input |
|---|------|------|--------|-------|
| 1 | Input | `init` | `idea_id`, `message`, `history` | caller |
| 2 | Idea | `api` | `GET /internal/agents/ideas/{{input.idea_id}}` | `{{input.idea_id}}` |
| 3 | Taxonomy | `api` | `GET /internal/agents/config/taxonomy` | — |
| 4 | Optimizer | `llm` | prompt `ideakonnekt-wf-idea-optimizer` | `idea_json` ← node 2; `message` ← `{{input.message}}`; `history_json` ← `{{input.history}}`; `taxonomy_json` ← node 3 |
| 5 | Guardrail | `guardrail` | on node 4 output | — |
| 6 | Parse | `adapter` | `IdeaOptimizeTurn` | `{{optimizer.output}}` |
| 7 | Output | `output` | `{ reply, field_patches, focus_fields }` | `{{parse.output}}` |

**Edges:** 1→2, 2→3, 3→4, 4→5, 5→6, 6→7. Nodes 2 and 3 can run in parallel.

---

## Ideathon team (not a workflow)

The Cluster, Rank and Pitch agents run as the team `idea-konnekt-ideathon` (sequential: `ideathon-cluster` → `ideathon-rank` → `ideathon-pitch`). The team already exists in Kompass. The workflow that used to wrap it, `Ideathon Pipeline`, was deleted, so this is the only Ideathon artifact left to decide on.

If it's rebuilt, the chain would be: `init {ideathon_id, stage, weights}` → `agent` (team slug) → `adapter` → `output`. Its node-to-node placeholders are still unverified.

---

## Open items

1. **Internal read routes.** Every `api` node above points at `/internal/agents/*`. Those routes don't exist yet, so each flow needs a mock until they're built.
2. **Auth on `api` nodes.** Decide whether these calls carry the static tool token or the signed-in user's token, as we discussed for the Ideathon tools.
3. **Placeholder and type names.** Confirm the `{{…}}` syntax and the component type literals on the first build.
4. **Build order.** Start with Help Guide (no API nodes) to prove the chain, then Innovation Workflow, then the rest.
