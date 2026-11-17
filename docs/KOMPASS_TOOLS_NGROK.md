# Kompass tools → Idea Hub (ngrok)

Create these **HTTP tools** (and/or Workflow **API nodes**) in Kompass Dev so agents/workflows can call a local Idea Hub API exposed through **ngrok**.

Related: [`KOMPASS_DEV_SETUP_RUNBOOK.md`](KOMPASS_DEV_SETUP_RUNBOOK.md), [`KOMPASS_PROMPT_CREATE_PAYLOADS.json`](KOMPASS_PROMPT_CREATE_PAYLOADS.json), [`KOMPASS_PROMPT_CREATE_API.md`](KOMPASS_PROMPT_CREATE_API.md), [`TRACKER_PROVIDERS.md`](TRACKER_PROVIDERS.md), [`AGENT_SIMULATION.md`](AGENT_SIMULATION.md).

---

## Overview — ngrok + base URL

```text
Kompass worker (staging)
    │  HTTPS tool / API node
    ▼
https://<subdomain>.ngrok-free.app   ← ngrok http 8000
    │
    ▼
Idea Hub API  http://127.0.0.1:8000
    paths under /api/v1/…
```

1. Start Hub API: `cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
2. Tunnel: `ngrok http 8000` (or your ngrok config)
3. In Kompass Vault / tool config set:

| Vault / env | Value |
|-------------|--------|
| `IDEAKONNEKT_BASE` | `https://<subdomain>.ngrok-free.app/api/v1` (no trailing slash beyond `/api/v1`) |
| Tool auth | See [Auth](#auth--ngrok-caveats) |

Paste that base into every tool’s URL prefix. When the ngrok hostname rotates, update Vault once.

**Primary Kompass pattern** (runbook): Workflows = Input → **API node** (Hub read) → LLM (`ideakonnekt-wf-*`) → Adapter → Output.  
**Custom agent tools** are required for **Ideathon** Smart Agents (tool loops). Do **not** duplicate the same Hub fetch as both an API node and a tool on the same flow unless you intentionally use an Agent node instead of LLM + API.

---

## Auth / ngrok caveats

| Mechanism | When to use |
|-----------|-------------|
| `Authorization: Bearer <access_jwt>` | Preferred for Kompass → Hub today. Spine auth accepts cookie **or** Bearer ([`dependencies/auth.py`](../backend/app/dependencies/auth.py)). |
| Cookie `access_token` | Browser / Vite proxy only. Kompass workers generally **cannot** reuse browser cookies across hosts. |
| `X-User-Id` (+ optional `X-Roles`, `X-Active-Role`) | Phase 2+3 **local stub** only ([`phase23_auth.py`](../backend/app/dependencies/phase23_auth.py)). Fine for Dev smoke; do not rely on in production. |
| Planned `IDEAKONNEKT_API_KEY` on `/internal/agents/*` | Documented in the runbook; **not implemented yet**. Until then use Bearer JWT (service user) or header stubs. |
| Hub → Kompass `AISTUDIO_TOOL_AUTH_TOKEN` | Stored in Hub `.env`; gateway forwards as `X-Authorization` to **tools**. Never put this in the browser Help widget. |

**ngrok notes**

- Free ngrok may inject an interstitial; use a header Kompass can send (e.g. `ngrok-skip-browser-warning: true`) or a paid/stable domain.
- CORS does not apply to server-side Kompass calls.
- Do not commit real JWTs, tracker tokens, or `.env` secrets.

---

## Quick attach matrix

| Tool slug | Required now? | Attach to (Kompass) | Hub path (today / planned) |
|-----------|---------------|---------------------|----------------------------|
| `ik_get_idea` | **Yes** (Ideathon) | Agent `ideakonnekt-ideathon-pitch` (Team `ideakonnekt-ideathon`) | `GET /ideas/{idea_id}` · planned `/internal/agents/ideas/{idea_id}` |
| `ik_search_similar` | **Yes** (Ideathon) | Agent `ideakonnekt-ideathon-cluster` | **Stub** → planned `POST /internal/agents/ideas/similar` |
| `ik_ideathon_entries` | **Yes** (Ideathon) | Agents `ideakonnekt-ideathon-cluster`, `-rank`, `-pitch` | Interim `GET /ideathons/{id}` (`entry_idea_ids`) · planned `…/ideathons/{id}/entries` |
| Workflow API reads (not tools) | Yes for Flows A–E | Weaver **API nodes**, not agent tools | See [§ Workflow API nodes](#required-now--workflow-api-nodes-not-agent-tools) |
| Tracker tools (`ik_tracker_*`) | **No** for current prompts | Do **not** attach to WF / Ideathon prompts | Hub UI uses live `/trackers/*` — [§ Tracker Hub APIs](#tracker-hub-apis-complete--not-kompass-agent-tools) |

**Do not create tools for:** multi-role login / `complete-login` / `switch-role`, toasts, or Innovation Workflow `remind_link_tracker` (draft text only). See [§ Explicitly no tool](#explicitly-no-tool--draft-only--ui-only).

---

## Required now — Ideathon agent tools

Prompt payloads (`promptType: agent`) bind these by name. Create matching custom HTTP tools in Agentic Engine and attach only as listed.

Team: **`ideakonnekt-ideathon`** (sequential: cluster → rank → pitch).

### 1. `ik_get_idea`

| Field | Value |
|-------|--------|
| Purpose | Load one idea’s problem/solution fields for pitch / handoff drafts |
| When | Ideathon pitch stage |
| Method + path | `GET {IDEAKONNEKT_BASE}/ideas/{idea_id}` |
| Planned twin | `GET {IDEAKONNEKT_BASE}/internal/agents/ideas/{idea_id}` (anonymous-safe strip) |
| Auth | `Authorization: Bearer {{vault.IDEAKONNEKT_ACCESS_TOKEN}}` |
| Attach to | **`ideakonnekt-ideathon-pitch`** only (prompt: “Tools when bound: ik_get_idea, ik_ideathon_entries”) |

**Request:** path param `idea_id` (UUID).

**Response sketch** (IdeaOut subset agents need):

```json
{
  "id": "uuid",
  "title": "…",
  "problem": "…",
  "solution": "…",
  "status": "submitted",
  "tags": [],
  "category_id": null,
  "is_anonymous": false
}
```

Strip author identity in mocks / future `/internal/agents` if `is_anonymous`.

---

### 2. `ik_search_similar`

| Field | Value |
|-------|--------|
| Purpose | Similarity peers for clustering themes |
| When | Ideathon cluster stage |
| Method + path | **Stub / mock until Hub ships** `POST {IDEAKONNEKT_BASE}/internal/agents/ideas/similar` |
| Today | No public `/ideas/…/similar` router. Similarity lives in agent heuristics (`agent_heuristics.similar_ideas`) inside Hub runs — not a Kompass-callable route yet. |
| Auth | Bearer (planned API key on `/internal/agents`) |
| Attach to | **`ideakonnekt-ideathon-cluster`** |

**Request sketch:**

```json
{
  "title": "…",
  "problem": "…",
  "tags": [],
  "exclude_idea_ids": [],
  "limit": 10
}
```

**Response sketch:**

```json
{
  "items": [
    {
      "idea_id": "uuid",
      "title": "…",
      "similarity": 0.42,
      "status": "accepted",
      "can_join": false
    }
  ]
}
```

Until the route exists: point the Kompass tool at a mock that returns this shape, or temporarily call Hub only after `/internal/agents/ideas/similar` is implemented.

---

### 3. `ik_ideathon_entries`

| Field | Value |
|-------|--------|
| Purpose | List entry idea ids (and later rich entry payloads) for an ideathon |
| When | Cluster, rank, and pitch stages |
| Method + path (interim) | `GET {IDEAKONNEKT_BASE}/ideathons/{ideathon_id}` → use `entry_idea_ids` (+ `shortlist`, challenges) |
| Planned | `GET {IDEAKONNEKT_BASE}/internal/agents/ideathons/{ideathon_id}/entries` |
| Auth | Bearer or Phase23 headers |
| Attach to | **`ideakonnekt-ideathon-cluster`**, **`ideakonnekt-ideathon-rank`**, **`ideakonnekt-ideathon-pitch`** |

**Response sketch (interim from IdeathonDetailOut):**

```json
{
  "id": "uuid",
  "title": "…",
  "theme": "…",
  "challenges": ["…"],
  "phase": "…",
  "entry_idea_ids": ["uuid", "uuid"],
  "shortlist": []
}
```

Adapter tip: map `entry_idea_ids` → the shape the agent prompt expects (array of entries). Pitch may then call `ik_get_idea` per id.

---

## Required now — Workflow API nodes (not agent tools)

These feed `{{variables}}` into **text** prompts. Create them as Weaver **API** nodes (read-only). Optionally mirror as tools **only** if you drop an Agent node instead of LLM + API — then attach the twin tool to that agent, not to every WF prompt.

Planned Hub contract (runbook). **Status:** `/internal/agents/*` is **not shipped**; use interim Hub routes or mocks.

| API purpose | Method | Planned path | Interim Hub route (exists) | Used by workflow / prompt |
|-------------|--------|--------------|----------------------------|---------------------------|
| Get idea | GET | `/internal/agents/ideas/{{idea_id}}` | `GET /ideas/{idea_id}` | Flow A/C · `ideakonnekt-wf-idea-intelligence`, `-enhancement`, `-review-intelligence`, `-idea-optimizer` |
| Similar ideas | POST | `/internal/agents/ideas/similar` | **Mock / stub** | Flow A/C · Intelligence, Review |
| Taxonomy | GET | `/internal/agents/config/taxonomy` | `GET /categories` | Flow A · Intelligence, Enhancement, Submit Assist, Optimizer |
| Thread | GET | `/internal/agents/ideas/{{idea_id}}/thread` | `GET /ideas/{idea_id}/comments` (+ votes if you compose) | Flow C · Review Intelligence |
| Past decisions | GET | `/internal/agents/panels/{{panel_id}}/decisions` | **Mock** (panel decisions not a dedicated agents path) | Flow C · Review |
| Pipeline stuck | GET | `/internal/agents/pipeline/stuck` | Optional; Flow B usually passes Hub-computed `nudge_json` in Input | Flow B · Innovation Workflow |
| Recognition context | GET | `/internal/agents/recognition/context` | Compose from `GET /recognition/*` or mock | Flow C/E · Recognition |
| Analytics snapshot | GET | `/internal/agents/analytics/snapshot` | `GET /insights?days=` | Flow E · Innovation Analytics |
| Ideathon entries | GET | `/internal/agents/ideathons/{{id}}/entries` | `GET /ideathons/{id}` | Flow D (prefer agent tools above) |

Headers on API nodes: `Authorization: Bearer {{vault.IDEAKONNEKT_ACCESS_TOKEN}}` (or planned API key).

| Prompt slug | Prefer data from |
|-------------|------------------|
| `ideakonnekt-wf-idea-intelligence` | taxonomy + similar + idea |
| `ideakonnekt-wf-idea-enhancement` | idea + taxonomy |
| `ideakonnekt-wf-submit-assist` | draft + taxonomy (+ message) — usually Hub chat surface / execute input |
| `ideakonnekt-wf-idea-optimizer` | idea + taxonomy (+ chat) |
| `ideakonnekt-wf-review-intelligence` | idea + thread + past decisions + similar |
| `ideakonnekt-wf-help-guide` | Input only: `message`, `role_json` — **no Hub tool** |
| `ideakonnekt-wf-innovation-workflow` | Input `nudge_json` (optional stuck API) — **no write / tracker tools** |
| `ideakonnekt-wf-recognition` | recognition context API |
| `ideakonnekt-wf-innovation-analytics` | analytics snapshot |

---

## Explicitly no tool (draft-only / UI-only)

| Product behaviour | Why no Kompass tool |
|-------------------|---------------------|
| Multi-role login (`requires_role_selection`, `POST /auth/complete-login`, `active_role`, `POST /auth/switch-role`) | Browser ↔ Hub auth. Help Guide **describes** the flow via `role_json`; it must not call auth APIs or handle OTP/tickets. |
| Auth / success toasts | Frontend-only UX. |
| Innovation Workflow `remind_link_tracker` | Prompt outputs `recommendedAction` + `draftMessage` for a **human** to approve. Hard rule: never connect trackers or create remote work items. |
| Review Intelligence post-accept delivery | Prompt forbids proposing ClickUp/Jira/custom links or asking for credentials. |
| Help Guide tracker FAQ | Explains Delivery UI + registry; never connects trackers or reveals secrets. |
| Recognition awards / review decide / status changes | Hub SoR after human approval; Kompass proposals only. |

Do **not** invent `ik_complete_login`, `ik_switch_role`, `ik_send_toast`, or `ik_create_tracker_issue` for these prompts.

---

## Tracker Hub APIs (complete) — not Kompass agent tools

Tracker integrations are **implemented** in Hub (`backend/app/trackers/`, Alembic `trackers_001`, phase23 mount). Full product doc: [`TRACKER_PROVIDERS.md`](TRACKER_PROVIDERS.md).

**Kompass rule:** current prompts treat tracker create/link as **human Delivery UI** after accept. Do **not** attach write tools to `ideakonnekt-wf-*` or Ideathon agents. Documented here so Dev does not “fill the gap” with forbidden agent tools, and so a **future** optional read-only tool (if ever needed) targets the real routes.

All paths below are under `{IDEAKONNEKT_BASE}` = `…/api/v1`.

### Status gates (service constants)

| Action | Allowed idea status |
|--------|---------------------|
| List / link existing | `accepted`, `prototype`, `implemented` |
| Create new remote task | `accepted`, `prototype` only |

### Providers (registry-driven)

| `provider_id` | Credentials (encrypted at rest) |
|---------------|----------------------------------|
| `clickup` | Personal API token + list id |
| `jira` | Site URL + email + API token + project key |
| `custom_webhook` | HTTPS create URL + optional auth header |

### Routes (actual)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/trackers/providers` | Registry catalog for UI | Actor (JWT / headers) |
| GET | `/trackers/connections` | List my connections | Actor |
| POST | `/trackers/connections` | Connect / update credentials | Actor |
| DELETE | `/trackers/connections/{connection_id}` | Disconnect | Actor |
| GET | `/ideas/{idea_id}/tracker-links` | List links on an idea | Actor |
| POST | `/ideas/{idea_id}/tracker-links` | Create **or** link remote item | Actor |
| DELETE | `/ideas/{idea_id}/tracker-links/{link_id}` | Unlink (remote kept) | Actor |

**POST `/trackers/connections` body:**

```json
{
  "provider_id": "clickup",
  "label": "default",
  "credentials": { }
}
```

**POST `/ideas/{idea_id}/tracker-links` body:**

```json
{
  "connection_id": "uuid",
  "mode": "create",
  "title": "optional",
  "description": "optional",
  "external_id_or_url": null,
  "extra": {}
}
```

`mode=link` requires `external_id_or_url`. Response: `IdeaTrackerLinkOut` (`provider_id`, `external_id`, `external_url`, …).

### Custom tracker later (Hub, not Kompass)

1. **Fast path:** connect provider `custom_webhook` — Hub POSTs the create-task JSON contract in TRACKER_PROVIDERS.md to your URL.
2. **First-class:** implement `TrackerProvider` in `backend/app/trackers/`, `register_provider` in `registry.py`, restart API.

No new Kompass tool is required for either path; the Delivery UI already drives the same Hub routes.

### Optional later (only if product explicitly allows agent-assisted delivery)

| Tool slug | Method + path | Attach only if… |
|-----------|---------------|-----------------|
| `ik_list_tracker_providers` | `GET /trackers/providers` | A **new** agent prompt is written to help choose a provider (read-only). **Not** Help Guide / Innovation Workflow / Review today. |
| `ik_list_idea_tracker_links` | `GET /ideas/{id}/tracker-links` | A delivery-assist agent needs link state for drafts. Still **no** create/link tool while prompts forbid writes. |
| `ik_create_or_link_tracker` | `POST /ideas/{id}/tracker-links` | **Forbidden** by current payloads. Do not create until prompts and product policy change. |

---

## Role / session awareness (no tools)

| Surface | How role reaches the model |
|---------|----------------------------|
| Help Guide | Workflow/execute input variable `{{role_json}}` (`active_role`, `roles[]`) from Hub — not a tool call |
| Other WF prompts | No role tool; Hub strips anonymity and builds context before invoke |
| Hub APIs | JWT claim `active_role`; `POST /auth/switch-role` re-issues cookies/Bearer |

Kompass must not implement login, OTP, or role-switch tools.

---

## Setup checklist

1. [ ] Hub API on `:8000`; DB migrated (`trackers_001` if testing Delivery).
2. [ ] `ngrok http 8000` → set Vault `IDEAKONNEKT_BASE=https://…/api/v1`.
3. [ ] Vault Bearer JWT for a Dev service user (or Phase23 `X-User-Id` for smoke).
4. [ ] Create tools **`ik_get_idea`**, **`ik_search_similar`** (mock OK), **`ik_ideathon_entries`**.
5. [ ] Attach tools to Ideathon agents per matrix; wire Team `ideakonnekt-ideathon` into Flow D.
6. [ ] Wire Flows A–E **API nodes** (or mocks) — not duplicate agent tools for the six WF assistants.
7. [ ] Confirm **no** tracker write tools on Review / Innovation Workflow / Help / Ideathon.
8. [ ] Smoke: Ideathon team run with bound tools; one Flow A API+LLM run.

---

## Inventory vs prompts (12 payloads)

| Prompt name | Slug | Tools to attach |
|-------------|------|-----------------|
| IdeaKonnekt - WF Idea Intelligence | `ideakonnekt-wf-idea-intelligence` | None (API nodes) |
| IdeaKonnekt - WF Idea Enhancement | `ideakonnekt-wf-idea-enhancement` | None (API nodes) |
| IdeaKonnekt - WF Submit Assist | `ideakonnekt-wf-submit-assist` | None (Hub execute / input) |
| IdeaKonnekt - WF Idea Optimizer | `ideakonnekt-wf-idea-optimizer` | None (API nodes / execute input) |
| IdeaKonnekt - WF Review Intelligence | `ideakonnekt-wf-review-intelligence` | None (API nodes); **no trackers** |
| IdeaKonnekt - WF Help Guide | `ideakonnekt-wf-help-guide` | None (`message` + `role_json`) |
| IdeaKonnekt - WF Innovation Workflow | `ideakonnekt-wf-innovation-workflow` | None; `remind_link_tracker` is draft-only |
| IdeaKonnekt - WF Recognition | `ideakonnekt-wf-recognition` | None (API nodes) |
| IdeaKonnekt - WF Innovation Analytics | `ideakonnekt-wf-innovation-analytics` | None (API nodes) |
| IdeaKonnekt - Ideathon Cluster | `ideakonnekt-ideathon-cluster` | **`ik_ideathon_entries`**, **`ik_search_similar`** |
| IdeaKonnekt - Ideathon Rank | `ideakonnekt-ideathon-rank` | **`ik_ideathon_entries`** |
| IdeaKonnekt - Ideathon Pitch | `ideakonnekt-ideathon-pitch` | **`ik_get_idea`**, **`ik_ideathon_entries`** |
