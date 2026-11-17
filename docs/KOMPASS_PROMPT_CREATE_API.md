# Create Idea Konnekt prompts via API Gateway

Ready bodies: [`KOMPASS_PROMPT_CREATE_PAYLOADS.json`](KOMPASS_PROMPT_CREATE_PAYLOADS.json)  
(9 prompts, `status: "active"`, labels `latest` + `production`, human-readable names).

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
IdeaKonnekt - WF Idea Intelligence
IdeaKonnekt - WF Idea Enhancement
IdeaKonnekt - WF Review Intelligence
IdeaKonnekt - WF Innovation Workflow
IdeaKonnekt - WF Recognition
IdeaKonnekt - WF Innovation Analytics
IdeaKonnekt - Ideathon Cluster
IdeaKonnekt - Ideathon Rank
IdeaKonnekt - Ideathon Pitch
```

Pattern: `IdeaKonnekt - WF <Role>` for workflow LLM prompts; `IdeaKonnekt - Ideathon <Stage>` for agent prompts.

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
| IdeaKonnekt - WF Innovation Workflow | `claude_4_5_haiku` |
| IdeaKonnekt - WF Recognition | `claude_4_5_haiku` |
| IdeaKonnekt - WF Idea Intelligence | `claude_4_6_sonnet` |
| IdeaKonnekt - WF Idea Enhancement | `claude_4_6_sonnet` |
| IdeaKonnekt - WF Review Intelligence | `claude_4_6_sonnet` |
| IdeaKonnekt - WF Innovation Analytics | `claude_4_6_sonnet` |
| IdeaKonnekt - Ideathon * | `claude_4_6_sonnet` |

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

## Curl all 9

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

Open https://kompass-admin-ui-staging.dotkonnekt.com/ → tenant **devtest** → Prompts → filter `IdeaKonnekt`.

Or:

```bash
curl -sS "$GW/api/v1/prompts?q=IdeaKonnekt&limit=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT" | jq .
```

---

## Inventory

| name (UI) | slug (auto) | type | temp | model |
|-----------|-------------|------|------|-------|
| IdeaKonnekt - WF Idea Intelligence | `ideakonnekt-wf-idea-intelligence` | text | 0.20 | `claude_4_6_sonnet` |
| IdeaKonnekt - WF Idea Enhancement | `ideakonnekt-wf-idea-enhancement` | text | 0.30 | `claude_4_6_sonnet` |
| IdeaKonnekt - WF Review Intelligence | `ideakonnekt-wf-review-intelligence` | text | 0.10 | `claude_4_6_sonnet` |
| IdeaKonnekt - WF Innovation Workflow | `ideakonnekt-wf-innovation-workflow` | text | 0.25 | `claude_4_5_haiku` |
| IdeaKonnekt - WF Recognition | `ideakonnekt-wf-recognition` | text | 0.20 | `claude_4_5_haiku` |
| IdeaKonnekt - WF Innovation Analytics | `ideakonnekt-wf-innovation-analytics` | text | 0.25 | `claude_4_6_sonnet` |
| IdeaKonnekt - Ideathon Cluster | `ideakonnekt-ideathon-cluster` | agent | 0.20 | `claude_4_6_sonnet` |
| IdeaKonnekt - Ideathon Rank | `ideakonnekt-ideathon-rank` | agent | 0.15 | `claude_4_6_sonnet` |
| IdeaKonnekt - Ideathon Pitch | `ideakonnekt-ideathon-pitch` | agent | 0.35 | `claude_4_6_sonnet` |
