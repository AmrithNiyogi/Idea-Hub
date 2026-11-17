# Idea Hub → Cursor / Claude Code agent handoff

Turn a reviewed idea into a paste-ready context pack so a coding agent can start building. The pack is **self-contained** (full markdown + idea UUID + API URL). An optional **skill** can re-fetch live context later.

## UI entry points

| Surface | What you get |
|---------|----------------|
| **Idea detail** (`/ideas/:id`) | **Copy for Cursor**, **Copy for Claude**, **Download context.md**, **Download skill**, plus **How to launch** |
| **Review workspace** (`/review/:id`) | Same bar (compact) |

### Recommended flow (actually interact)

1. Open the idea (signed in).
2. Click **Copy for Cursor** or **Copy for Claude** — clipboard gets a tool-tailored prompt that already includes idea UUID, API base, and the full context pack.
3. Open Cursor Agent chat or a Claude Code session in the **target repo** and **paste**. The agent can plan and build immediately — no skill required for the first paste.
4. Optional: **Download context.md** and attach / `@`-mention the file.
5. Optional (re-fetch later): **Download skill** → extract the zip at the repo root → ask the agent to use skill `idea-hub-pull-idea` with the idea UUID.

There is **no** reliable universal deeplink that injects a prompt into every Cursor/Claude install. Paste is the supported interaction path.

### Skill install paths (from the zip)

Extract `idea-hub-pull-idea-skill.zip` at the **repo root** so both exist:

| Tool | Path |
|------|------|
| Cursor | `.cursor/skills/idea-hub-pull-idea/SKILL.md` |
| Claude Code | `.claude/skills/idea-hub-pull-idea/SKILL.md` |

The zip also includes `README.md` with the same steps. From **How to launch** you can also **Copy SKILL.md** / **Download SKILL.md only**.

Set env for the skill:

| Variable | Purpose | Example |
|----------|---------|---------|
| `IDEA_HUB_API_URL` | API origin (preferred for agents) | `http://127.0.0.1:8000` |
| `VITE_API_BASE_URL` | Same origin used by the Vite app | `http://localhost:8000` |
| `PUBLIC_API_URL` | Server-side value embedded in prompts | `http://127.0.0.1:8000` |

## API

```http
GET /api/v1/ideas/{idea_id}/agent-context
GET /api/v1/agent-handoff/skill
GET /api/v1/agent-handoff/skill-pack.zip
```

- **Auth:** required (JWT cookie or `Authorization: Bearer`)
- **404 (agent-context):** missing idea or private draft
- **Secrets:** never included (no emails, OTP, JWT secrets, SMTP)

### Response shape (high level)

```json
{
  "idea_id": "uuid",
  "slug": "string|null",
  "title": "string",
  "status": "under_review",
  "category": { "id": "uuid", "slug": "process", "label": "Process" },
  "problem": "...",
  "solution": "...",
  "beneficiaries": "...",
  "success_metrics": "...",
  "effort": "M",
  "tags": ["ops"],
  "anonymous": false,
  "author": { "id": "uuid", "name": "…" },
  "owner": { "id": "uuid", "name": "…" },
  "status_history": [{ "from_status": "submitted", "to_status": "under_review", "at": "…", "reason": "" }],
  "latest_decision": { "outcome": "accept", "reason": "…", "at": "…", "as_role": "reviewer", "hours": 20 },
  "comments": { "count": 3, "highlights": [{ "kind": "discussion", "body": "…", "at": "…", "author_name": "…" }] },
  "delivery": { "hours_granted": 20, "task_total": 4, "task_done": 1, "open_task_titles": ["…"] },
  "related_links": [{ "label": "Idea detail", "href": "/ideas/…" }],
  "api_base_url": "http://127.0.0.1:8000",
  "skill": {
    "name": "idea-hub-pull-idea",
    "skill_markdown": "---\nname: idea-hub-pull-idea\n…",
    "install_cursor": "Extract … `.cursor/skills/idea-hub-pull-idea/SKILL.md` …",
    "install_claude": "Extract … `.claude/skills/idea-hub-pull-idea/SKILL.md` …",
    "zip_url": "/api/v1/agent-handoff/skill-pack.zip"
  },
  "markdown": "# Idea: …\n\n## Build with an agent\n…",
  "prompts": {
    "cursor": "You are helping implement…",
    "claude": "You are Claude Code…"
  }
}
```

Anonymous ideas redact author identity in the pack. `context.md` (`markdown`) includes install steps that match the shipped skill zip.

## Cursor / Claude skill (repo developers)

Canonical copies for people working **inside** the Idea Hub checkout:

- `.cursor/skills/idea-hub-pull-idea/SKILL.md`
- `.claude/skills/idea-hub-pull-idea/SKILL.md`
- API-packaged copy: `backend/app/assets/agent_skills/idea-hub-pull-idea/SKILL.md`

End users who are **not** in this repo should use **Download skill** from the UI (or `GET …/skill-pack.zip`), not these paths alone.

## End-to-end (test idea)

Idea example: `b5b832b7-1c1c-4618-a09f-02e5c55c82d6` (Structured handoff checklist…).

1. Local stack up: API `:8000`, UI `:5173`, signed in.
2. Open `/ideas/b5b832b7-1c1c-4618-a09f-02e5c55c82d6`.
3. **Copy for Cursor** → paste into Cursor Agent in Idea Hub or a product repo → confirm the prompt contains the UUID + API URL + problem/solution.
4. **Download skill** → unzip at a scratch repo root → confirm both skill paths exist → ask the agent to use `idea-hub-pull-idea` with that UUID.
5. **Download context.md** → open the file → confirm **Build with an agent** section lists real install paths (not a dead skill mention).

## Implementation map

| Layer | Location |
|-------|----------|
| Schema | `backend/app/schemas/agent_context.py` |
| Skill pack service | `backend/app/services/agent_skill_pack.py` |
| Context service | `backend/app/services/agent_context_service.py` |
| Routes | `GET …/ideas/{id}/agent-context`, `GET …/agent-handoff/skill`, `GET …/agent-handoff/skill-pack.zip` |
| Packaged skill | `backend/app/assets/agent_skills/idea-hub-pull-idea/SKILL.md` |
| UI | `frontend/src/components/AgentHandoffBar.tsx` |
| Clients | `ideasApi.agentContext`, `agentHandoffApi` in `frontend/src/api/` |
| Skill (repo) | `.cursor/skills/idea-hub-pull-idea/`, `.claude/skills/idea-hub-pull-idea/` |
