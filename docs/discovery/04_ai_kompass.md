# IdeaKonnekt — AI, Agentic Workflows and Kompass Integration Architecture (Discovery, Agent 4)

Date: 2026-11-15. Status: discovery analysis, no application code. Source of Kompass facts: CONTEXT.md section 3 only. Anything not in its VERIFIED list is marked **UNVERIFIED** and appears in the gap list (section 6). Design-token values are out of scope and not asserted.

## 0. Ground rules

1. In the MVP every agent is **SIMULATED**: deterministic JavaScript over mock data, no network, no LLM. Every agent surface carries a persistent "Simulated" chip and each run record has `simulated: true`.
2. **AI may never decide on its own:** accept/park/merge/decline decisions or their reasons of record, scores of record, awards (Idea of the Quarter, Annual Award), points overrides, anything that changes a person's standing, de-anonymisation, and publication of announcements in someone's name. AI may *draft, score-suggest, flag, rank, remind*. A human click, attributed to a named user, is the only path to a state change on those.
3. **Auto-apply is limited to reversible, low-stakes, non-judgemental metadata:** suggested tags once the author accepts the template, SLA reminder notifications, derived analytics, activity-trace entries, point *accruals under published rules* (see Recognition).
4. AI output is always a **proposal object** with evidence, never a direct write. Humans see the evidence and can reject it. Rejections are logged and fed into the analytics.

## 1. The product agents

### Recommendation on the roster
Keep the seven as the user-visible roster (the brief and master instructions name them), with three structural changes:
- **Add a non-LLM Orchestrator** (called "IdeaKonnekt Orchestrator"), the event router and run recorder. It subscribes to events, selects agents, enforces the approval gates, and writes the agent run record. Making it explicitly deterministic keeps it honest and testable, and it is the seam where Kompass is later plugged in.
- **Split Review Intelligence into two roles inside one agent card:** *Reviewer Brief* (summarise, risks) and *Review Integrity check* (bias/consistency, see section 8). The integrity check must be separable because it audits the reviewer-facing output.
- **Treat Idea Intelligence and Idea Enhancement as one pipeline with two stages** ("Assist on submit"): Intelligence = classify, dedupe, completeness; Enhancement = improve text. They share inputs and appear in the same form, but keep two agent identities so traces stay legible and Kompass can later map them separately.
- Do not add an eighth LLM-style agent. "Anonymity" is a **policy layer** (a Guardrails-style filter in the adapter), not an agent.

Common approval vocabulary: `none` (auto-apply), `author` (submitter accepts), `reviewer`, `owner`, `admin`, `leadership`.

### 1.1 Idea Intelligence
- **Purpose:** understand, classify, dedupe, flag gaps.
- **Triggers:** `idea.draft_changed` (debounced, while typing), `idea.submitted`.
- **Context:** the draft; all existing ideas (title, problem, tags, category, status); tag vocabulary; category definitions from admin config.
- **Analysis:** category suggestion, tag suggestion, similar-idea search, completeness check.
- **Output (`IdeaIntelligenceResult`):** `ideaId`, `suggestedCategory{value,confidence,evidence[]}`, `suggestedTags[{tag,score,evidenceTerms[]}]`, `similarIdeas[{ideaId,similarity,sharedTerms[],status,canJoin}]`, `missingFields[{field,reason}]`, `duplicateRisk` (low/medium/high).
- **Approval:** category and tags need `author`. Similar-idea list and missing-field hints are advisory and auto-display. "Join instead" is a human click.
- **Appears:** side panel of the submission form (live), then on the submitted-idea page as "Agent notes".

### 1.2 Idea Enhancement
- **Purpose:** help authors improve text and framing.
- **Triggers:** user clicks "Improve with agent" on a field; `idea.submitted` for an optional post-submit suggestion.
- **Context:** the field text, the whole draft, category, successful accepted ideas in the same category (as exemplars).
- **Analysis:** problem-statement critique, rewrite suggestion, beneficiary suggestions, metric suggestions, impact estimate band.
- **Output (`EnhancementProposal`):** `ideaId`, `field`, `original`, `suggestions[{kind,text,rationale}]`, `suggestedBeneficiaries[]`, `suggestedMetrics[{metric,unit,baselinePrompt}]`, `impactEstimate{band,assumptions[]}`.
- **Approval:** always `author`; applied per suggestion via an accept/edit/dismiss control. Nothing overwrites the author's text silently. `impactEstimate` is labelled indicative and is never shown to reviewers as a score.
- **Appears:** inline per field in the submission form and edit view.

### 1.3 Review Intelligence
- **Purpose:** prepare reviewers, never decide.
- **Triggers:** `idea.review_started`, `comment.added` (when thread length passes a threshold), `idea.assigned_to_panel`.
- **Context:** idea, full comment thread, votes, volunteers, similar ideas, category panel scoring criteria, past decisions in the category.
- **Analysis:** summary, discussion themes, risks and dependencies, suggested scores per criterion with evidence, decision lean with caveats, integrity check.
- **Output (`ReviewerBrief`):** `ideaId`, `summary`, `discussionSummary{pros[],concerns[],openQuestions[]}`, `risks[{risk,source}]`, `dependencies[]`, `suggestedScores{impact,effort,alignment}{value,confidence,evidence[]}`, `decisionLean{option,rationale,caveats[]}`, `integrityFlags[]`.
- **Approval:** briefs are auto-generated (read-only aid). Suggested scores and any decision draft need `reviewer`; the reviewer must enter their own scores and reason. The UI must show the brief **collapsed by default for scoring** until the reviewer has entered an initial score (anchoring mitigation, section 8).
- **Appears:** the reviewer panel on the review screen.

### 1.4 Innovation Workflow
- **Purpose:** keep ideas moving and visible.
- **Triggers:** `clock.tick` (simulated daily, user-advanceable "advance time" demo control), `idea.status_changed`, `review.sla_breached`, `delivery.update_posted`.
- **Context:** all ideas with timestamps, panel SLA settings, owners, delivery tasks and time budgets.
- **Analysis:** stuck detection, SLA breach, next-action recommendation, delivery risk (budget burn vs progress).
- **Output (`WorkflowNudge`):** `ideaId`, `condition`, `daysInStage`, `slaDays`, `recommendedAction`, `targetUserId`, `draftMessage`.
- **Approval:** reminder to a reviewer or owner auto-sends (`none`). Escalation to leadership and reassignment need `admin`.
- **Appears:** dashboard "Needs attention", status board badges, notifications.

### 1.5 Ideathon
- **Purpose:** run campaigns.
- **Triggers:** `ideathon.draft_created`, `ideathon.closed`, `ideathon.shortlist_confirmed`, `ideathon.voting_closed`.
- **Context:** campaign, linked submissions, voting results, challenge statement.
- **Analysis:** challenge-statement drafting, theme suggestion, submission clustering, shortlist suggestion, pitch summaries, hackathon problem statements.
- **Output (`IdeathonPack`):** `ideathonId`, `challengeDraft`, `clusters[{label,ideaIds[],keyTerms[]}]`, `shortlistSuggestion[{ideaId,rank,criteriaScores,rationale}]`, `pitchSummaries[{ideaId,oneLiner,problem,solution,ask}]`, `hackathonStatements[{ideaId,statement,successCriteria[]}]`.
- **Approval:** `admin`/campaign owner for shortlist and challenge text; `leadership` for hackathon handoff. Pitch summaries need the idea author's `author` approval before going on a pitch deck.
- **Appears:** ideathon management and pitch-day views.

### 1.6 Recognition
- **Purpose:** transparent, quality- and impact-weighted recognition.
- **Triggers:** `idea.decision_recorded`, `idea.implemented`, `impact.measured`, `comment.helpful_marked`, `quarter.closed`.
- **Context:** contribution ledger, rules table, impact records, collaboration graph (co-authors, volunteers, helpful comments).
- **Analysis:** rule-based points, badge eligibility, award shortlist with evidence, collaboration detection.
- **Output (`RecognitionProposal`):** `userId`, `pointsDelta[{rule,points,evidenceRef}]`, `badgeEligibility[{badge,criteriaMet[]}]`, `awardCandidates[{awardType,ideaId|userId,evidence[],impactSummary}]`.
- **Approval:** points under published rules auto-apply (`none`) because they are deterministic and appealable. Badge grants of "judgement" type and every award need `leadership`/`admin`. Manual points overrides need `admin` plus a reason.
- **Appears:** profile, leaderboard, awards admin screen.

### 1.7 Innovation Analytics
- **Purpose:** leadership insight.
- **Triggers:** `analytics.requested`, `quarter.closed`, any batch of events (recomputed on view).
- **Context:** all ideas, events, decisions, impact records.
- **Analysis:** participation, theme emergence, stage conversion, bottlenecks, impact roll-up.
- **Output (`InsightSet`):** `period`, `metrics{}`, `insights[{id,type,statement,metric,value,comparison,evidenceIdeaIds[]}]`, `recommendedActions[]`.
- **Approval:** `none` (read-only). Any recommended action becomes a human task.
- **Appears:** dashboard insight cards and leadership view.

## 2. Agent-to-agent flows

Gates are marked **[GATE: role]**. Every step writes to the run record (section 3).

### Flow A: Idea submitted
1. **Trigger:** `idea.submitted`. 2. **Retrieve:** idea, idea corpus, tag vocabulary, panel config. 3. **Analyse:** Idea Intelligence runs classify, dedupe, completeness. 4. **Delegate:** Orchestrator invokes Enhancement (optional suggestions) and Review Intelligence (pre-brief, queued) and Innovation Workflow (starts SLA clock). 5. **Recommendation:** `IdeaIntelligenceResult` plus `EnhancementProposal`. 6. **[GATE: author]** accept category/tags/rewrites; **[GATE: author]** choose "join existing idea" when duplicateRisk is high. 7. **Execute:** apply accepted fields; route to the category panel (routing itself is deterministic from admin config, so no gate). 8. **Record:** run saved with approval outcomes. 9. **Update:** status = Submitted, SLA timer visible, event `idea.routed`.

### Flow B: Review SLA breached
1. **Trigger:** `review.sla_breached`. 2. **Retrieve:** idea, panel, reviewer workloads, history. 3. **Analyse:** Workflow agent computes days over SLA, picks next action. 4. **Delegate:** Review Intelligence refreshes the brief so the reviewer can act fast. 5. **Recommendation:** `WorkflowNudge`. 6. First breach: reminder auto-sends (no gate). Second breach: **[GATE: admin]** approve escalation or reassignment. 7. **Execute:** send, or reassign. 8. **Record:** nudge, recipient, outcome. 9. **Update:** idea shows "overdue" badge and new due date; dashboard attention list updates.

### Flow C: Decision recorded
1. **Trigger:** reviewer submits scores and a decision. The human decision is the trigger; the agent never produces it. 2. **Retrieve:** decision, scores, brief used, thread. 3. **Analyse:** Review Intelligence runs the integrity check (reason present and non-trivial, consistent with scores, flags divergence from brief); Recognition computes author/contributor points; Workflow determines next stage. 4. **Delegate:** Recognition (points), Workflow (owner/time allocation suggestion on accept, merge-target suggestion on merge). 5. **Recommendation:** `integrityFlags`, owner suggestion, plain-language decision notice draft for the author. 6. **[GATE: reviewer]** confirm or edit the notice draft before it is sent; **[GATE: admin/team lead]** confirm owner and hours (innovation time is granted by leadership). 7. **Execute:** status change, notice posted, points accrue, owner assigned. 8. **Record:** decision history entry (human author, reason, whether AI brief was viewed). 9. **Update:** idea timeline, profile, dashboard counts.

### Flow D: Ideathon closes to hackathon handoff
1. **Trigger:** `ideathon.closed`. 2. **Retrieve:** linked submissions, challenge, comments, votes. 3. **Analyse:** Ideathon agent clusters and ranks (suggestion only). 4. **Delegate:** Review Intelligence supplies briefs per candidate; Idea Enhancement drafts pitch summaries. 5. **Recommendation:** `IdeathonPack` stage 1 (clusters, shortlist). 6. **[GATE: admin]** confirm shortlist. Authors approve pitch summaries **[GATE: author]**. 7. Pitch day: panel and audience votes are human inputs. Winner computed deterministically by the published weighting; **[GATE: leadership]** ratifies winners. 8. **Execute:** Ideathon agent drafts hackathon problem statements; **[GATE: leadership]** approves handoff. 9. **Record/Update:** handoff record created (simulated export, no external system); winning ideas linked; Recognition awards proposed (see Flow E gates).

### Flow E: Implemented to impact to recognition
1. **Trigger:** owner marks `idea.implemented`, later `impact.measured`. 2. **Retrieve:** delivery log, contributors, time used, impact figures. 3. **Analyse:** Analytics derives realised impact vs estimate; Recognition computes contribution splits, badge eligibility, award candidacy. 4. **Delegate:** Workflow drafts the completion announcement. 5. **Recommendation:** announcement draft, `RecognitionProposal`. 6. **[GATE: owner]** verifies impact figures (self-reported numbers are labelled unverified until approved); **[GATE: team lead]** approves announcement; **[GATE: leadership]** for awards and judgement badges. 7. **Execute:** publish, apply points, grant badges. 8. **Record:** evidence refs stored. 9. **Update:** author and contributors credited on profiles, dashboard impact totals.

## 3. Event taxonomy and agent run record

Common envelope: `{ eventId, name, ts, actorId|null, actorType: "user"|"system"|"agent", entityType, entityId, anonymousContext: boolean, payload }`.

| Event | Payload fields |
|---|---|
| idea.draft_changed | ideaId, fields{changed[]}, textLength |
| idea.submitted | ideaId, category, authorId (null if anonymous), coAuthorIds[], ideathonId? |
| idea.routed | ideaId, panelId, dueAt |
| idea.status_changed | ideaId, from, to, reason? |
| idea.review_started | ideaId, reviewerId |
| review.sla_breached | ideaId, panelId, daysOver, breachCount |
| comment.added | ideaId, commentId, authorId, threadLength |
| idea.voted / idea.followed / idea.volunteered | ideaId, userId |
| idea.decision_recorded | ideaId, decision, reasonLength, scores{impact,effort,alignment}, reviewerId, mergeTargetId? |
| idea.owner_assigned | ideaId, ownerId, hoursGranted |
| delivery.update_posted | ideaId, taskId?, hoursUsed, percent |
| idea.implemented | ideaId, contributorIds[], hoursUsed |
| impact.measured | ideaId, hoursSaved?, revenueInfluenced?, verifiedBy? |
| ideathon.created / closed / shortlist_confirmed / voting_closed | ideathonId, ideaIds[], voteTallies? |
| ideathon.handoff_requested | ideathonId, ideaIds[] |
| recognition.points_awarded | userId, rule, points, evidenceRef |
| agent.proposal_decided | runId, proposalId, decision (accepted/edited/rejected), userId |
| clock.tick | simulatedDate |
| analytics.requested | period, scope |

**Agent run record (`AgentRun`):**
```
runId, agent, agentVersion, simulated (bool, always true in MVP), engine ("mock-heuristic-v1"),
trigger{eventId, eventName}, flowId?, parentRunId? (for delegated subtasks),
startedAt, endedAt, status (running|awaiting_approval|completed|rejected|failed),
steps[{stepId, kind (retrieve|analyse|delegate|recommend|approval|execute|record|update),
       label, status (pending|done|skipped|blocked), inputs{refs[]}, outputs{summaryRef|inline},
       confidence?, durationMs, note?}],
output{schemaName, payload, evidence[]},
confidence{overall, basis ("heuristic score"|"rule match"|"canned")},
approval{required, role, state (not_required|pending|approved|edited|rejected), decidedBy?, decidedAt?, reason?},
appliedChanges[{entity, field, before, after}], privacy{anonymousContext, redactedFields[]}
```
`durationMs` is theatrical in the MVP (small artificial delay), flagged in the trace legend. Confidence in the MVP is a heuristic score, not a calibrated probability; label as "match strength".

## 4. Simulation heuristics (honest labelling)

Labels: **[Computed]** real computation on mock data, **[Canned]** pre-written content selected by rule, **[Templated]** filled from real data into fixed sentence patterns.

| Capability | Heuristic | Type |
|---|---|---|
| Similarity | Lowercase, strip stopwords, light stemming; TF-IDF cosine over title+problem+solution plus Jaccard on tags; blend 0.7/0.3; threshold 0.25 shows, 0.6 = "high duplicate risk". Shared terms displayed as evidence. | Computed |
| Tag suggestion | Match tokens to a tag vocabulary with synonym map (e.g. "pipeline"→ci); top 5 by term-frequency weight, with the matching words shown. | Computed |
| Category suggestion | Keyword scoring per category from admin-configured keyword lists; confidence = margin between top two. | Computed |
| Missing-field detection | Per-field rules: empty, under N words, no number in success metric, no beneficiary noun, effort not selected. | Computed |
| Problem-statement rewrite | Detect solution-first phrasing ("we should build") and missing who/pain/cost; output templated "As [beneficiary], [pain] costs [metric]" scaffold with placeholders from detected nouns plus the author's own words. Never invents facts; unfilled slots shown as blanks. | Templated |
| Beneficiary / metric suggestion | Lookup tables by category and detected keywords. | Canned |
| Impact estimate band | Effort x reach heuristic from selected fields into low/medium/high with explicit assumptions listed. | Computed (crude) |
| Discussion summary | Extractive: sentence-split comments, score by term frequency, upvote/helpful weight, and cue words ("concern","risk","depends","blocked", "+1"); group into pros, concerns, open questions (sentences ending "?"). Selected sentences are quoted with commenter. | Computed (extractive) |
| Risks and dependencies | Cue-word and mention extraction (other teams, tools); plus a canned risk library by category. | Computed + Canned |
| Suggested scores | Reviewer-criteria checklist hits mapped to bands; shows which text triggered each. Low confidence by design. | Computed |
| SLA detection | `now - stageEnteredAt` vs panel SLA from admin config; business-day option. Demo time control advances `now`. | Computed |
| Clustering | Agglomerative clustering on TF-IDF cosine (threshold ~0.35); label = top 2 terms in cluster. | Computed |
| Shortlist | Weighted sum of votes, reviewer scores, alignment, comment diversity; weights shown. | Computed |
| Pitch summaries / hackathon statements | Templates filled from idea fields. | Templated |
| Points calculation | Published rule table (admin-editable). Design principle: weights favour decisions-accepted, implemented, verified impact, collaboration (helpful comments received, co-authoring, volunteering that led to delivery) over submission count; submission points capped per quarter, zero for duplicates or declined-for-incomplete. Every award line cites its rule and evidence. | Computed (deterministic) |
| Analytics insights | Real aggregates (stage conversion, median days in stage, participation by team, tag growth period over period); insight sentences are templates with computed numbers. | Computed + Templated |
| Challenge statement / theme drafts | Canned templates keyed by selected theme and customer-signal tags. | Canned |

Rules: the simulation must be seeded and deterministic, same input gives same output; every panel shows a "Simulated, rule-based, not a language model" tooltip with a "How this was computed" expander listing the heuristic. No output is described as "AI-generated" without the Simulated qualifier.

## 5. Kompass integration architecture (future production)

Mapping uses only verified concepts. Where a mapping depends on an unverified behaviour, the table says so.

**Agent form:** Idea Intelligence, Idea Enhancement, Review Intelligence, Recognition, Analytics = **Smart Agents** (single-purpose, tools, guardrails, memory/AI Brain reference). Ideathon agent = candidate **Agentic Team** (clustering, drafting, pitch writing are separable roles; the docs describe Sequential/Hierarchical (and Parallel) patterns). Innovation Workflow = mostly deterministic and best left in IdeaKonnekt; Kompass is only needed for the draft-message and recommendation language.

**Flows as Kompass Workflows (candidate designs):**
- Flow A: Input (JSON idea) → Embedding/AI Brain lookup for similar ideas (Embedding is a verified Tools component; using it for this is our design) → Agent (Intelligence) → Adapter (string to JSON) → Conditional (duplicateRisk) → Agent (Enhancement) → Adapter → Output.
- Flow B: Input → API (calls back to IdeaKonnekt to fetch context; the API component is verified for calling external HTTP) → Agent (Review Intelligence) → Adapter → Output.
- Flow C/E: Input → Guardrails → Agent → Adapter → Output, with any IdeaKonnekt write-back performed by IdeaKonnekt after approval, not by the workflow.
- Flow D: Subflow chaining (cluster, brief, pitch), serial execution per verified Subflow behaviour.
- MCP component: would only be used if IdeaKonnekt exposes an MCP server for tool access. Not required; optional later.
- Context component: session memory for multi-turn Enhancement dialogs.

| IdeaKonnekt need | Kompass concept | Verified? | Open question |
|---|---|---|---|
| Run agent from IdeaKonnekt on an event | Workflow with Input node (type `init`, String/JSON) | Input node verified; external invocation **UNVERIFIED** | Endpoint, auth, request/response shape? |
| Smart agent for text analysis | Smart Agent with system prompt, guardrails, model | Verified | Can output be forced to a JSON schema? |
| Structured JSON output | Agent → Adapter | Docs say JSON must pass through Adapter; schema enforcement **UNVERIFIED** | Does Adapter validate or only reshape? Failure behaviour? |
| Idea corpus for similarity/RAG | AI Brain collection (Markdown/CSV/URL sources, chunked and embedded) | Verified concept; ingestion API/refresh **UNVERIFIED** | How to sync ideas continuously; per-collection access control? |
| Fetch live IdeaKonnekt data | API component calls out | Verified (outbound) | Can workflows call a customer-hosted IdeaKonnekt API through Vault secrets (`{{vault.*}}`)? Likely, **confirm** |
| Anonymous-submission protection | Guardrails (PII, input and output) | Guardrails verified; effectiveness for anonymity **UNVERIFIED** | Custom guardrails for author-identifying style? |
| Activity log of agent runs | Traces | Verified (ClickHouse-backed, cost analysis per docs) | Can IdeaKonnekt read traces via API and correlate with `runId`? |
| Quality of agent outputs over time | Evals | Verified area; details not read | Can reviewer accept/reject feed Evals? |
| Human approval | none | **UNVERIFIED**: no approval node found | See section 6 |
| Event triggers, schedules (SLA ticks) | none | **UNVERIFIED** | Webhooks, schedulers? |
| Multi-agent Ideathon pipeline | Agentic Team (Sequential/Hierarchical/Parallel) | Verified concept | How is a Team invoked externally; output format? |
| Long responses in UI | Streaming (WebSocket and SSE per docs) | Mentioned in capabilities page | Which endpoints, and are they available to external clients? |
| Config/versioning | Workflow Draft/Active/Inactive, versioning, JSON import/export | Verified | Promotion process per environment? |

**AI Brain collections (proposed):** `ideahub-ideas` (accepted/declined idea summaries), `ideahub-decisions` (decision reasons, supports consistency checks), `ideahub-policy` (category definitions, scoring rubrics, recognition rules, innovation-time policy), `ideahub-kompass-capabilities` (so the "new Kompass capability" category can dedupe against real product), `ideahub-pitches` (past pitch packs). Anonymous ideas are indexed with author fields excluded from the source documents.

**Guardrails:** PII on input for anonymous submissions and on output of all agents; prompt-injection guard on user-written text (idea bodies and comments are untrusted input fed to LLMs); hallucination guard on summaries (require quotes from thread); custom guardrail forbidding decision language ("should be declined") in briefs, so wording stays a lean with caveats.

## 6. Integration gap list and adapter shape

**Must ask the Kompass team:**
1. Invocation: how an external app starts a Workflow, Smart Agent or Team; endpoint, auth (API key? OAuth? Vault-linked?), request/response format.
2. Sync vs async, run IDs, polling, cancellation; timeouts (docs advise avoiding long API calls ~30s, implying limits).
3. Streaming interface for external clients (WebSocket/SSE).
4. Triggers: webhooks, scheduled runs, event ingestion.
5. Human-in-the-loop or approval/pause-resume primitive.
6. Structured outputs: schema enforcement, Adapter semantics, retry on invalid JSON.
7. Traces access via API; trace-to-run correlation; retention; redaction for anonymous content.
8. AI Brain: programmatic ingestion, deletion (needed for right-to-erasure and withdrawn ideas), collection-level permissions.
9. Tenant/role model: can IdeaKonnekt users map to Kompass roles, or does IdeaKonnekt call as a service identity?
10. Whether Kompass can act as an MCP server; whether any pre-built idea-management agent exists.
11. Data residency, model choices, cost per run, rate limits.

**Adapter layer for the MVP (so nothing depends on the answers):** one interface `AgentGateway.run(agentName, event, context) -> Promise<AgentRun>`; the MVP implements it with `MockEngine` (the deterministic heuristics). The contract fixed in IdeaKonnekt is the **input envelope, the output schemas in section 1, and the AgentRun record**; transports (REST, async polling, SSE) are plug-in `KompassEngine` implementations later. Responses are validated against IdeaKonnekt's own schemas, with a fallback to "no suggestion" on failure so the app degrades safely. Every agent has a `engine` and `registryEntry` property so the UI can show which engine ran. Configuration includes a per-agent mapping field (`kompassRef`: null in MVP, "planned" label only).

**Human approval lives in IdeaKonnekt.** Regardless of Kompass answers, approval state, approver identity, and audit trail are IdeaKonnekt records: the agent returns a proposal; IdeaKonnekt stores it as `pending`; only a user action calls the execute step; Kompass workflows never write directly to decision, award or status fields. If Kompass later offers an approval node, it may be used for *notification*, but IdeaKonnekt remains the system of record.

## 7. Kompass inside the MVP UI (honest presentation)

- **Agent Registry / "Kompass integration map" screen** (admin and leadership): table of the 7 agents plus Orchestrator with columns: Agent, MVP engine ("Simulated, mock-heuristic-v1"), Planned Kompass concept (Smart Agent / Agentic Team / Workflow), Planned components (names from the verified list), Verification status chip (Verified concept / Invocation unverified), Open questions link.
- A permanent banner: "Not connected to Kompass. All agent activity in this prototype is simulated." Status indicator values are fixed to "Simulated" and "Planned"; no green "connected" dot, no fake latency or token-cost numbers presented as Kompass metrics.
- **Flow diagrams** per flow showing planned Kompass nodes in dashed outline versus IdeaKonnekt steps in solid, and approval gates in IdeaKonnekt.
- **Agent activity trace** drawer (from AgentRun) with a legend noting "In production this would be backed by Kompass Traces (planned, unverified how to access)".
- Do not display Kompass logos in a way that implies a live product integration; text labels suffice. No invented Kompass agent names; only our own agent names appear.
- A "Gap list" tab reproducing section 6 so stakeholders see what is unconfirmed.

## 8. Risks and mitigations

| Risk | Detail | Mitigation |
|---|---|---|
| Trust and over-reliance | Reviewers adopt the AI lean; authors accept rewrites uncritically. | Simulated/AI labels; evidence shown with every claim; brief collapsed until reviewer enters initial score; track "agreed with AI" rate in analytics and surface it to admins. |
| Bias in AI-assisted review | Similarity to past accepted ideas favours incumbents, certain teams, or confident writing styles; extractive summaries favour vocal commenters. | Scores and decision remain human; the brief omits author identity and team by default (blind option); integrity check compares decision rates across category, team and seniority and shows disparities to admins; rubric criteria visible to all. |
| Anonymity leakage | Writing-style cues, similar-idea matching ("you wrote something similar"), recognition points, or AI logs expose an anonymous author. | Author identity excluded from agent context (`authorId` null; policy layer redacts); no points, leaderboard or profile credit for anonymous ideas unless the author later opts to reveal; agent runs store `anonymousContext`; Enhancement never suggests text based on the author's previous submissions; in production, PII guardrail plus keeping anonymous content out of shared AI Brain collections. |
| Over-automation | Auto-sent reminders become noise; auto-points feel unfair; decisions seem machine-made. | Auto-apply whitelist (section 0); human-written reasons required; per-user notification caps; appeal path for points; admin kill switch per agent. |
| Gaming | Authors write to the heuristic; point farming via co-author or upvote rings. | Points weighted to decisions and verified impact; caps; collaboration credit requires reviewer-confirmed contributions; rule table is public. |
| Misrepresenting the prototype | Stakeholders mistake simulation for real AI or an existing Kompass integration. | Persistent labels, registry screen, documentation separating Implemented/Simulated/Planned/Unverified. |
| Prompt injection and data leakage (production) | Idea text can contain instructions to the model. | Guardrails (prompt injection), structured outputs validated by IdeaKonnekt, no write access for agents. |
| Integration assumptions | Designs depend on unverified Kompass behaviour. | Gap list, adapter isolation, all Kompass mappings marked planned. |

**Opinionated summary:** build the Orchestrator + `AgentRun` trace first, as it makes every AI feature visible and honest; make Similarity, Missing-field detection, SLA detection and Points the four genuinely computed features (they carry the demo); keep drafting features templated and labelled; keep every judgement human.
