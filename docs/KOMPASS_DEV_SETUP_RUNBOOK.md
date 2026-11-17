# Idea Konnekt → Kompass Dev setup runbook

Follow this in **Kompass Dev**. Order matters. Checkboxes are for you.

**Primary pattern: Workflows** = `Input` → `API` (Idea Konnekt data) → `LLM` (Prompt Engine text/chat) → `Adapter` → `Output`.

**Secondary:** Smart Agents / Agentic Team only where tool loops or multi-stage Ideathon autonomy help.

Full prompts: [`KOMPASS_AGENT_PROMPTS.md`](KOMPASS_AGENT_PROMPTS.md) (Part A = workflow LLM with `{{}}`; Part B = agent prompts, no `{{}}`).

Sources: Features deck, [`docs/discovery/04_ai_kompass.md`](discovery/04_ai_kompass.md), prototype `FLOWS` / `AGENT_REGISTRY` in `idea-hub.html`.

---

## Rules that never change

1. Kompass returns **proposals (JSON)**. Idea Konnekt is system of record for status, scores, awards, points overrides.
2. Workflow **API nodes are read-only**. No write APIs from Kompass into decisions/awards.
3. Anonymous ideas: strip author from API payloads and Brain docs.
4. Human gates stay in **Idea Konnekt UI** (not Kompass HITL as SoR).
5. Two prompt kinds — do not mix:
   - **Workflow LLM node** → Prompt Engine `text` or `chat` **with** `{{variables}}`
   - **Smart Agent / Team** → Prompt Engine `agent` **with no** `{{variables}}`

---

## Architecture (what you are building)

```text
Idea Konnekt (event / button)
        │
        ▼
 Kompass Workflow (Flows A–E)     ← primary invoke target
   Input → API* → LLM → Adapter → Output
        │
        ├── most assistants: LLM only (data from API or Input)
        └── Ideathon: Team node or Subflow of agents (optional)

* API = Idea Konnekt /internal/agents/* (Vault: IDEAKONNEKT_API_KEY)
```

| Assistant | Kompass form | Data | Prompt |
|-----------|--------------|------|--------|
| Idea Intelligence | **Workflow** (Flow A stage 1) | API taxonomy + similar (+ idea) | text `ideakonnekt-wf-idea-intelligence` |
| Idea Enhancement | **Workflow** (Flow A stage 2) | API idea / Input | text `ideakonnekt-wf-idea-enhancement` |
| Review Intelligence | **Workflow** (Flow C / review) | API idea + thread + decisions | text `ideakonnekt-wf-review-intelligence` |
| Innovation Workflow | **Workflow** (Flow B) | Input nudge (Hub-computed) or API stuck | text `ideakonnekt-wf-innovation-workflow` |
| Recognition | **Workflow** (Flow C/E) | API recognition context | text `ideakonnekt-wf-recognition` |
| Innovation Analytics | **Workflow** (Flow E / insights) | API analytics snapshot | text `ideakonnekt-wf-innovation-analytics` |
| Ideathon | **Team** `ideakonnekt-ideathon` inside Flow D | Agent tools or APIs in subflow | **agent** prompts (Part B) |

Do **not** register custom agent tools for the six workflow assistants if every fetch is an **API node**. Tools are for Ideathon agents (and any Agent-node fallback).

---

## Step 0 — Preconditions

- [ ] Dev tenant; Prompt Engine + Workflow Weaver + Agentic Engine reachable
- [ ] Idea Konnekt (or mock) reachable from Kompass workers
- [ ] Vault / env: `IDEAKONNEKT_BASE`, `IDEAKONNEKT_API_KEY`
- [ ] Models in tenant catalog (Haiku/Flash, Sonnet, Pro)

---

## Step 1 — Prompt Engine

See [`KOMPASS_AGENT_PROMPTS.md`](KOMPASS_AGENT_PROMPTS.md).

### 1.1 Workflow LLM prompts (create these first — Part A)

`promptType: **text**` (or chat). Variables allowed. Production label. Model + temperature from tier table.

| Slug | Temp | Tier |
|------|------|------|
| `ideakonnekt-wf-idea-intelligence` | 0.20 | Default Sonnet / Flash-Pro |
| `ideakonnekt-wf-idea-enhancement` | 0.30 | Default |
| `ideakonnekt-wf-review-intelligence` | 0.10 | Heavy Sonnet / Pro |
| `ideakonnekt-wf-innovation-workflow` | 0.25 | Fast Haiku / Flash |
| `ideakonnekt-wf-recognition` | 0.20 | Fast–Default |
| `ideakonnekt-wf-innovation-analytics` | 0.25 | Default–Heavy |

- [ ] Six workflow text prompts + Production
- [ ] Variables match Part A (`idea_json`, `taxonomy_json`, …)

### 1.2 Agent prompts (Ideathon — Part B)

`promptType: **agent**`. No `{{}}`.

| Slug | Temp |
|------|------|
| `ideakonnekt-ideathon-cluster` | 0.20 |
| `ideakonnekt-ideathon-rank` | 0.15 |
| `ideakonnekt-ideathon-pitch` | 0.35 |

Optional: Part B also has agent twins of the six above if you later drop an **Agent** node into a workflow instead of LLM — not required for Dev if Flows use LLM nodes.

- [ ] Three Ideathon agent prompts + Production

---

## Step 2 — Idea Konnekt read APIs (for Workflow API nodes)

Same paths whether called as API nodes or (later) agent tools. **Read-only.**

| API purpose | Method | Path |
|-------------|--------|------|
| Get idea | GET | `{IDEAKONNEKT_BASE}/internal/agents/ideas/{{idea_id}}` |
| Similar ideas | POST | `{IDEAKONNEKT_BASE}/internal/agents/ideas/similar` |
| Taxonomy | GET | `{IDEAKONNEKT_BASE}/internal/agents/config/taxonomy` |
| Thread | GET | `{IDEAKONNEKT_BASE}/internal/agents/ideas/{{idea_id}}/thread` |
| Past decisions | GET | `{IDEAKONNEKT_BASE}/internal/agents/panels/{{panel_id}}/decisions` |
| Pipeline stuck | GET | `{IDEAKONNEKT_BASE}/internal/agents/pipeline/stuck` |
| Recognition context | GET | `{IDEAKONNEKT_BASE}/internal/agents/recognition/context` |
| Analytics snapshot | GET | `{IDEAKONNEKT_BASE}/internal/agents/analytics/snapshot` |
| Ideathon entries | GET | `{IDEAKONNEKT_BASE}/internal/agents/ideathons/{{ideathon_id}}/entries` |

In Workflow Weaver API node:

- Headers: `Authorization: Bearer {{vault.IDEAKONNEKT_API_KEY}}` (or your Vault key name)
- Map path/body from `{{input.*}}` / prior node outputs
- Until backend exists: mock HTTP returning sample JSON

- [ ] Endpoints or mocks reachable
- [ ] One manual API-node test returns JSON

---

## Step 3 — AI Brain (optional first Dev pass)

| Collection | Contents |
|------------|----------|
| `ideakonnekt-ideas` | Accepted/declined summaries (no author if anonymous) |
| `ideakonnekt-decisions` | Decision reasons |
| `ideakonnekt-policy` | Categories, rubrics, recognition rules |
| `ideakonnekt-kompass-capabilities` | Product capabilities |
| `ideakonnekt-pitches` | Past pitch packs |

Skip for first smoke if Similar API is mocked.

---

## Step 4 — Workflows first (Flows A–E)

Build in **Workflow Weaver**. Default graph shape:

```text
Input (JSON)
  → API … (0..N Idea Konnekt reads)
  → LLM (prompt slug from Step 1.1; map {{vars}} from Input/API outputs)
  → Adapter (force/parse JSON schema)
  → Output
```

Guardrails: attach on LLM output (and on API results that carry user text). Human approval stays in Idea Konnekt after Output.

### Flow A — Assist on submit (`ideakonnekt-flow-assist-submit`)

Trigger: Idea Konnekt `idea.submitted` / draft assist.

```text
Input { idea_id, idea fields… }
  → API taxonomy
  → API similar (body from idea title/problem/tags)
  → LLM ideakonnekt-wf-idea-intelligence
       vars: idea_json, taxonomy_json, similar_ideas_json
  → Adapter → (store / pass) IntelligenceResult
  → optional Conditional on duplicateRisk
  → LLM ideakonnekt-wf-idea-enhancement
       vars: idea_json, taxonomy_json, field
  → Adapter → Output { intelligence, enhancement }
```

- [ ] Draft / Active

### Flow B — Overdue / stale nudge (`ideakonnekt-flow-workflow-nudge`)

Trigger: Idea Konnekt scheduler / page compute (SLA already done).

```text
Input { ideaId, condition, daysInStage, slaDays, ideaTitle, targetUserId, … }
  → LLM ideakonnekt-wf-innovation-workflow
       vars: nudge_json   (entire Input as one var is fine)
  → Adapter → Output WorkflowNudge
```

Optional: API `pipeline/stuck` if Input is only a filter, not a full nudge.

- [ ] Draft / Active

### Flow C — After decision (`ideakonnekt-flow-decision-followup`)

```text
Input { idea_id, panel_id, decision, scores, mode }
  → API idea + API thread + API past_decisions
  → LLM ideakonnekt-wf-review-intelligence (mode integrity/consistency)
  → Adapter
  → API recognition context
  → LLM ideakonnekt-wf-recognition
  → Adapter → Output { brief, recognition }
```

- [ ] Draft / Active

### Flow D — Ideathon (`ideakonnekt-flow-ideathon`)

```text
Input { ideathon_id, stage, weights… }
  → Agent Team ideakonnekt-ideathon   (or Subflow: cluster → rank → pitch)
  → Adapter → Output IdeathonPack
```

Team uses **agent** prompts (Step 1.2) + tools (Step 5).

- [ ] Draft / Active

### Flow E — Implemented / impact / insights (`ideakonnekt-flow-impact-insights`)

```text
Input { idea_id, period, … }
  → API analytics snapshot
  → LLM ideakonnekt-wf-innovation-analytics
  → Adapter
  → API recognition context
  → LLM ideakonnekt-wf-recognition
  → Adapter → Output { insights, recognition }
```

- [ ] Draft / Active

---

## Step 5 — Ideathon agents + Team (only where needed)

Framework `langgraph`. `prompt_slug` = Part B agent prompts. Tools (custom HTTP) for Ideathon only:

| Tool | Used by |
|------|---------|
| `ik_ideathon_entries` | cluster, rank, pitch |
| `ik_search_similar` | cluster |
| `ik_get_idea` | pitch |

Team:

| Field | Value |
|-------|--------|
| Name | Idea Konnekt Ideathon |
| Slug | `ideakonnekt-ideathon` |
| Topology | Sequential |
| Nodes | `ideathon-cluster` → `ideathon-rank` → `ideathon-pitch` |

- [ ] Three agents + Team Production
- [ ] Wired into Flow D

**Do not** create six Smart Agents for Intelligence/Enhancement/Review/… unless you intentionally use Agent nodes instead of LLM nodes.

---

## Step 6 — Invoke for Dev testing

Primary: **run the workflow** (Weaver test / workflow execute API — use Dev Swagger for exact path).

Pass Input JSON fixtures from [`KOMPASS_AGENT_PROMPTS.md`](KOMPASS_AGENT_PROMPTS.md) sample payloads.

Secondary: Team execute for Ideathon only; agent execute only if testing Part B agents alone.

Smoke table:

| Run | Target | Input | JSON OK? |
|-----|--------|-------|----------|
| 1 | Flow A | sample draft idea | |
| 2 | Flow B | overdue nudge | |
| 3 | Flow C | decision + idea_id | |
| 4 | Flow D / Team | ideathon_id | |
| 5 | Flow E | period + idea_id | |

---

## Step 7 — Guardrails

| Guardrail | Where |
|-----------|--------|
| PII | LLM in+out; API bodies with user text |
| Prompt injection | Idea/comment fields into LLM |
| Hallucination | Review + Analytics LLM outputs |
| Custom: no “should be declined/accepted” | Review LLM |

- [ ] Attached on Flows A–E LLM nodes
- [ ] Fail-closed smoke

---

## Step 8 — Idea Konnekt later

1. Ship `/internal/agents/*` read APIs for real.
2. `AgentGateway` invokes **workflow** ids (not raw agents) for A/B/C/E; Team/Flow D for Ideathon.
3. Validate Output JSON against Idea Konnekt schemas; fail → no suggestion.
4. Persist `AgentRun` + approval gates in Idea Konnekt.
5. Brain sync on submit / decision / implement.

Orchestrator = deterministic router in Idea Konnekt (not a Kompass agent).

---

## Quick map

| Assistant | Where | Kompass | Final say |
|-----------|-------|---------|-----------|
| Idea Intelligence | Submit | **Flow A** LLM | Author |
| Idea Enhancement | Submit | **Flow A** LLM | Author |
| Review Intelligence | Review | **Flow C** LLM | Reviewer |
| Innovation Workflow | Pipeline, Home | **Flow B** LLM | Reviewer / owner |
| Ideathon | Ideathon pages | **Flow D** + Team | Organiser |
| Recognition | Recognition, profiles | **Flow C/E** LLM | Leadership |
| Innovation Analytics | Insights, Home | **Flow E** LLM | Read-only |

---

## Done when

- [ ] Six Production **workflow text** prompts (Part A)
- [ ] Three Production **agent** prompts + Ideathon Team (Part B)
- [ ] Flows A–E Active in Dev (API mocks OK)
- [ ] Smoke table green for all five flows
- [ ] No duplicate custom tools for assistants already covered by API nodes
