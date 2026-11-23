# Create KonnektIdea prompts via API Gateway

Ready bodies: [`KOMPASS_PROMPT_CREATE_PAYLOADS.json`](KOMPASS_PROMPT_CREATE_PAYLOADS.json)  
(12 prompts, `status: "active"`, labels `latest` + `production`, human-readable names).  
See also simulation map: [`AGENT_SIMULATION.md`](AGENT_SIMULATION.md).

## Staging targets

| What | Value |
|------|--------|
| Admin UI | https://kompass-admin-ui-staging.dotkonnekt.com/ |
| API Gateway (POST here) | https://aistudio-apigateway-v2-staging.dotkonnekt.com |
| Tenant | `devtest` |

UI hosts the product; **create prompts against the API Gateway**, not the admin UI origin.

## Naming convention

Display `name` (what you see in Prompt Engine):

```text
KonnektIdea - WF Idea Intelligence
KonnektIdea - WF Idea Enhancement
KonnektIdea - WF Submit Assist
KonnektIdea - WF Idea Optimizer
KonnektIdea - WF Review Intelligence
KonnektIdea - WF Help Guide
KonnektIdea - WF Innovation Workflow
KonnektIdea - WF Recognition
KonnektIdea - WF Innovation Analytics
KonnektIdea - Ideathon Cluster
KonnektIdea - Ideathon Rank
KonnektIdea - Ideathon Pitch
```

Pattern: `KonnektIdea - WF <Role>` for workflow LLM prompts; `KonnektIdea - Ideathon <Stage>` for agent prompts.

Slug (auto from name): lowercase, spaces→`-`, strip other chars → e.g. `ideakonnekt-wf-idea-intelligence`. Use that slug in Workflow LLM nodes / agent `prompt_slug`.

## Endpoint

```http
POST https://aistudio-apigateway-v2-staging.dotkonnekt.com/api/v1/prompts
```

### Headers

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer <access_token>` from staging login |
| `X-Tenant-ID` | `devtest` |
| `Content-Type` | `application/json` |
| `X-User-ID` | optional (owner) |
| `project-id` | optional (else `default`) |

Needs permission `PROMPT_CREATE`.

### Body fields

| Field | Notes |
|-------|--------|
| `name` | Human title above (not snake_case) |
| `promptType` | `text` (WF) or `agent` (Ideathon) |
| `prompt` | string |
| `status` | **`active`** |
| `labels` | `["latest", "production"]` |
| `config.modelName` | catalog id (already set) |
| `config.temperature` | already set |
| `variables_metadata` | text only; agents omit |

## Models (already in payloads)

| Prompt name | modelName |
|-------------|-----------|
| KonnektIdea - WF Innovation Workflow | `claude_4_5_haiku` |
| KonnektIdea - WF Recognition | `claude_4_5_haiku` |
| KonnektIdea - WF Help Guide | `claude_4_5_haiku` |
| KonnektIdea - WF Idea Intelligence | `claude_4_6_sonnet` |
| KonnektIdea - WF Idea Enhancement | `claude_4_6_sonnet` |
| KonnektIdea - WF Submit Assist | `claude_4_6_sonnet` |
| KonnektIdea - WF Idea Optimizer | `claude_4_6_sonnet` |
| KonnektIdea - WF Review Intelligence | `claude_4_6_sonnet` |
| KonnektIdea - WF Innovation Analytics | `claude_4_6_sonnet` |
| KonnektIdea - Ideathon * | `claude_4_6_sonnet` |

Gemini alts: Fast → `gemini_2_5_flash`; Heavy → `gemini_2_5_pro`.

---

## Curl one

```bash
export GW="https://aistudio-apigateway-v2-staging.dotkonnekt.com"
export TOKEN="<bearer from staging login>"
export TENANT="devtest"

jq '.[0]' docs/KOMPASS_PROMPT_CREATE_PAYLOADS.json | \
curl -sS -X POST "$GW/api/v1/prompts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT" \
  -H "Content-Type: application/json" \
  -d @-
```

## Curl all

```bash
export GW="https://aistudio-apigateway-v2-staging.dotkonnekt.com"
export TOKEN="<bearer>"
export TENANT="devtest"

python3 << 'PY'
import json, os, urllib.request

gw = os.environ["GW"].rstrip("/")
token = os.environ["TOKEN"]
tenant = os.environ["TENANT"]
items = json.load(open("docs/KOMPASS_PROMPT_CREATE_PAYLOADS.json"))

for item in items:
    body = json.dumps(item).encode()
    req = urllib.request.Request(
        f"{gw}/api/v1/prompts",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": tenant,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        payload = data.get("data") or data
        print("OK", payload.get("name"), "→", payload.get("slug"), resp.status)
    except Exception as e:
        err = getattr(e, "read", lambda: b"")()
        print("FAIL", item["name"], e, err[:500])
PY
```

Expect **201**. **409** = name/slug already exists.

### Verify in UI

Open https://kompass-admin-ui-staging.dotkonnekt.com/ → tenant **devtest** → Prompts → filter `KonnektIdea`.

Or:

```bash
curl -sS "$GW/api/v1/prompts?q=KonnektIdea&limit=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT" | jq .
```

---

## Execute agent runs (after prompts / Smart Agents exist)

Authoritative contract (same as chatbot-admin embeddable curl):

```http
POST https://aistudio-apigateway-v2-staging.dotkonnekt.com/api/v2/runs/execute
```

```bash
curl -X POST "$GW/api/v2/runs/execute" \
  -H 'accept: */*' \
  -H "X-Tenant-ID: $TENANT" \
  -H 'project-slug: <your project slug>' \
  -H 'X-Authorization: <optional tool auth token>' \
  -H 'Content-Type: application/json' \
  -d '{
  "agent_id": "<kompass agent id or slug>",
  "input": "<string or JSON string>",
  "conversation_id": null
}'
```

KonnektIdea maps surfaces → env agent ids (`AISTUDIO_AGENT_*`) and proxies
server-side — see [`AGENT_SIMULATION.md`](AGENT_SIMULATION.md). Do **not** put
`X-Authorization` in the browser Help widget.

## Inventory

| name (UI) | slug (auto) | type | temp | model | Hub route / execute env |
|-----------|-------------|------|------|-------|-------------------------|
| KonnektIdea - WF Idea Intelligence | `ideakonnekt-wf-idea-intelligence` | text | 0.20 | `claude_4_6_sonnet` | `/agents/run` |
| KonnektIdea - WF Idea Enhancement | `ideakonnekt-wf-idea-enhancement` | text | 0.30 | `claude_4_6_sonnet` | `/agents/run` |
| KonnektIdea - WF Submit Assist | `ideakonnekt-wf-submit-assist` | text | 0.40 | `claude_4_6_sonnet` | `/simulate/submit-assist` · `AISTUDIO_AGENT_SUBMIT_ASSIST` |
| KonnektIdea - WF Idea Optimizer | `ideakonnekt-wf-idea-optimizer` | text | 0.35 | `claude_4_6_sonnet` | `/simulate/idea-optimize` · `AISTUDIO_AGENT_IDEA_OPTIMIZER` |
| KonnektIdea - WF Review Intelligence | `ideakonnekt-wf-review-intelligence` | text | 0.10 | `claude_4_6_sonnet` | `/agents/run` · `AISTUDIO_AGENT_REVIEW_INTELLIGENCE` |
| KonnektIdea - WF Help Guide | `ideakonnekt-wf-help-guide` | text | 0.20 | `claude_4_5_haiku` | `/simulate/help` · `AISTUDIO_AGENT_HELP` |
| KonnektIdea - WF Innovation Workflow | `ideakonnekt-wf-innovation-workflow` | text | 0.25 | `claude_4_5_haiku` | `/agents/run` |
| KonnektIdea - WF Recognition | `ideakonnekt-wf-recognition` | text | 0.20 | `claude_4_5_haiku` | `/agents/run` |
| KonnektIdea - WF Innovation Analytics | `ideakonnekt-wf-innovation-analytics` | text | 0.25 | `claude_4_6_sonnet` | `/agents/run` |
| KonnektIdea - Ideathon Cluster | `ideakonnekt-ideathon-cluster` | agent | 0.20 | `claude_4_6_sonnet` | planned |
| KonnektIdea - Ideathon Rank | `ideakonnekt-ideathon-rank` | agent | 0.15 | `claude_4_6_sonnet` | planned |
| KonnektIdea - Ideathon Pitch | `ideakonnekt-ideathon-pitch` | agent | 0.35 | `claude_4_6_sonnet` | planned |
