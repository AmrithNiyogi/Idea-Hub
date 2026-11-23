# IdeaKonnekt: code analysis notes (internal, do not share)

Analysed at commit 94c9930 on `main`, 2026-11-22. Every claim below comes from reading the code, not the older prototype docs.

## Numbers (measured)

| What | Count |
|---|---|
| API endpoints | 187 across 20 routers |
| DB tables | 53 (18 model files), 14 Alembic migrations in a single chain |
| Frontend screens | 28 pages |
| Code | about 33k lines Python, about 29k lines TypeScript |
| Backend tests | 214 passed, 87.46% coverage on critical services (gate is 85%) |
| Frontend tests | 27 passed, 1 failed, 19 skipped |
| Assistants in roster | 9 |
| Surfaces wired for live Kompass / AI Studio | 5 |

The failing frontend test is `Login.test.tsx` › "shows loading while auth bootstraps".

## What is genuinely smart (safe to claim)

1. **Live similar-idea detection while typing.** `agent_heuristics.similar_ideas`, debounced 500 ms in `Submit.tsx`.
   - Uses Jaccard over title, problem and tags across up to 200 ideas.
   - Matches at 0.12 or above count; the top 5 are shown with the shared terms.
   - Shows a duplicate-risk band: high at 0.45 or above, medium at 0.25 or above.
2. **Idea Intelligence:**
   - suggests a category (Jaccard against each category's text)
   - suggests tags (word frequency)
   - flags missing or thin template fields (under 12 characters)
3. **Co-pilots:**
   - Submit co-pilot chat: rule-based intent machine, returns patches that the form applies; scrubs secrets.
   - Help chat: FAQ with deep links.
   - Idea Optimizer: points out weak fields.
4. **Automatic routing and SLA clocks** on submit.
   - Draft → submitted → under_review in one transaction.
   - Pickup due in 3 days, decision due in 10.
   - The category panel is notified in-app and by email.
   - "Needs info" pauses the clock. Resuming shifts both deadlines by the length of the pause.
5. **Governed decisions:**
   - A written reason of at least 20 characters is required.
   - Scores are required for every outcome except info.
   - Accept needs an owner and hours. Park needs a future revisit date. Merge needs a target. Decline needs a "what would change our mind" note.
   - **Conflict-of-interest guards:** you cannot decide on, vote for, pitch-score or audience-vote your own idea, and you cannot approve your own hours request.
   - Merge automatically adds the merged authors as co-authors of the target.
6. **Reviewer brief** (heuristic):
   - comment triage into pros, concerns and questions
   - suggested impact, effort and alignment scores
   - a decision lean: merge (pre-filled target) → info → park → decline → accept
   - The human applies or ignores it, and the brief never writes the scores of record.
7. **Reopen engine:**
   - Up to 6 conditions, combined with ALL or ANY: date, raised (the problem cluster grows), dependency, capacity (pool hours), demand (votes or "me too"), manual.
   - Evaluated live, with progress, evidence and an "impossible" flag.
   - When conditions are met, a proposal appears; a panel member approves it, or dismisses it to snooze 7 days.
8. **Problem Radar:**
   - Clusters ideas by problem text and tags (threshold 0.34, union-find).
   - Shows the state (solved, in progress, unsolved), distinct teams, "me too" counts and "raised again in 30 days".
   - Leadership can set a sponsor and a label.
9. **Idea → Build handoff:**
   - `GET /ideas/{id}/agent-context` builds a context pack: idea, history, decision, discussion, delivery tasks and links, with the author redacted if anonymous.
   - It renders as markdown plus prompts for Cursor and Claude Code.
   - There is an installable skill pack zip.
   - `POST /agents/builds/{id}` sends the pack to the Kompass coding agent when configured, otherwise to a simulated timeline.
10. **Delivery governance:**
    - A quarterly innovation-hours pool. Going over needs an explicit override, which is recorded.
    - Approving hours automatically creates the project, moves the idea to prototype and awards points.
    - Implementing needs an outcome, evidence-backed impact entries, and shares that total exactly 100%.
    - Impact must be verified by a second person.
11. **Recognition:**
    - An append-only, idempotent ledger (dedupe key); every row cites a rule.
    - Monthly caps, largest-remainder share splitting, and an impact bonus of confidence × size band (25 to 150).
    - Leaderboard with rank change; written thanks (20–280 characters, 3 a month).
12. **Insights:**
    - The funnel is built from status history.
    - Per-panel review speed against SLA, with bottleneck ranking.
    - Theme growth and strategic theme matching.
    - Impact (verified vs unverified), hours pool, and rule-generated insight cards.
13. **AI news radar:**
    - Live arXiv (6 AI categories) and GitHub (new AI repos, with a star-farming dedupe).
    - 7-day freshness check and a 6-hour cache.
14. **Integrations:**
    - Jira, ClickUp and custom-webhook trackers sit behind a provider registry. Connecting probes the remote live; credentials are Fernet-encrypted.
    - Live status, assignees and priority, with write-back. Jira status changes go through workflow transitions. Assignees are matched to users by email.
    - Notion pages, Teams cards and an MCP JSON-RPC client.
    - Personal → org fallback ("effective connection").
15. **Groups:**
    - One per idea, with #general, #decisions and #blockers created automatically.
    - DMs, invites, meetings posted to Teams, and MCP tools per group.
16. **Security:**
    - Email OTP (HMAC-hashed, attempt caps, cooldown), TOTP MFA (Fernet at rest) and Microsoft SSO (nonce, state, JWKS, issuer checks).
    - httpOnly JWT cookies, multi-role with an active role, a field-level admin audit log, and rollback-safe DB sessions.

## Framing used in the documents

- **Explainable intelligence today.** Deterministic, auditable rules over real data. No hallucination and no per-call cost.
- **LLM-ready.** Five surfaces are wired to DotKonnekt AI Studio / Kompass (`POST /api/v2/runs/execute`). They turn on with `SIMULATE_AGENTS=false` plus the tenant, project and agent ids. Default is simulated (`settings.py:121`).
- **Human in the loop.** Every agent run is logged. Proposals need a role-checked human approval. Agents never record decisions, scores, winners or awards.

## Do NOT claim or demo (gaps found in code)

- **No LLM is called by default.** I could not verify whether any Kompass agents exist on the AI Studio side. Confirm before saying "live AI".
- **Idea-intelligence and idea-enhancement have no live LLM path.** They are heuristic only.
- **News categories:** only AI Research (arXiv) and AI Tools (GitHub) are live. The other 6 categories use invented sample stories. News "themes" mix in those sample titles.
- **Recognition:** points for submit, accepted, helpful, dedupe, on-time review and volunteer are defined but nothing awards them.
- **Missing UI:**
  - no "Mark implemented" button in the UI (the API exists)
  - no Annual Award UI
- **No background scheduler.** Overdue emails are never sent automatically. SLA tracking is visible but passive.
- **Trackers:** no push or webhook sync. Sync is a live fetch on view or refresh, plus write-back.
- **Review weighted score:** the UI uses 40/30/30, but admin defaults are 40/20/40 and the UI does not read them.
- **Submit uses hard-coded 10/3-day deadlines.** It ignores the admin timeline settings; only reopen reads them.
- **Ideathon:** the shortlist "agent score" is described but not computed in React.
- **Impact verification** is looser than designed: any employee other than the creator can verify.
- **Hard-coded path:** the agent-context prompts contain a developer-local path (`agent_context_service.py:52`).

## Security issues to fix before production (keep out of shared docs)

1. **HIGH: header impersonation.** `dependencies/phase23_auth.py:85-105`.
   - With no valid cookie, `get_actor` trusts the `X-User-Id` / `X-Roles` / `X-Active-Role` headers.
   - Nothing limits this to dev. An unauthenticated caller could act as admin on `/admin`, `/reopen`, delivery and profiles.
2. **No rate limiting** on the password check (`/auth/send-login-otp`).
3. **Insecure defaults are not checked at startup:**
   - `JWT_SECRET_KEY` has a dev default.
   - `COOKIE_SECURE` defaults to false.
   - The same secret also derives the OTP, TOTP and tracker encryption keys.
4. **Tokens are exposed in response headers** as well as httpOnly cookies.
5. **Refresh tokens cannot be revoked** server-side.
6. **Reviewer checks are loose:** the check passes for any held reviewer role, not the active role, and is not limited to the category panel.
7. **Anonymous ideas leak the author:** `author_id` is returned for anonymous ideas, and anonymous ideas are listed on the public profile.
8. **Bridge history and reopen bypass the state machine:**
   - `spine_bridge.set_idea_status` writes `from_status` equal to `to_status`.
   - Reopen moves declined → under_review, which `TRANSITIONS` does not allow.
