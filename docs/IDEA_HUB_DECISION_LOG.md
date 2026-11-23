# IdeaKonnekt — Decision Log

This log records the significant product, technical, architectural and design decisions taken during the IdeaKonnekt discovery phase, together with the agent recommendations behind them, rejected options, scope changes, technical constraints, known limitations and open questions. It is maintained throughout the project and is not written retrospectively. Each entry is dated when it was recorded. Entries D-001 to D-020 were recorded before any code was written; build and test status is recorded from D-021 onwards.

- Maintained by: Agent 6 (documentation agent, Haiku tier)
- Last updated: 2026-11-16
- Project phase: Build phases 1–6 implemented; phases 5–6 not yet fully tested; phase 7 (hardening, QA, final documentation) not started

---

## How to read this log

Statuses used in this log:

| Status | Meaning |
|---|---|
| Accepted | Decided and in force. |
| Accepted (provisional) | Decided, but the underlying values or assets are placeholders to be replaced later. |
| Proposed — awaiting founder | Recommended but not yet decided. Requires founder confirmation. |
| Rejected | An option or recommendation that was considered and not adopted. |
| Deferred | Accepted in principle but postponed to a later phase. |

Each decision entry uses the same fields. "None recorded" means the source notes for this log contain no information for that field.

---

## Summary index

| ID | Topic | Status |
|---|---|---|
| D-001 | Framework for the single HTML file | Accepted |
| D-002 | Information architecture | Accepted |
| D-003 | Persona switching | Accepted |
| D-004 | Idea lifecycle state machine | Accepted (timeline values: Proposed — awaiting founder) |
| D-005 | State management and persistence | Accepted |
| D-006 | Backend-ready service boundary | Accepted |
| D-007 | Agent roster | Accepted |
| D-008 | AI honesty and human-authority policy | Accepted |
| D-009 | Kompass integration approach | Accepted |
| D-010 | Design system application | Accepted (provisional) |
| D-011 | Charts | Accepted |
| D-012 | Pipeline board interaction | Accepted (drag-and-drop Rejected) |
| D-013 | Recognition framework | Accepted (values: Proposed — awaiting founder) |
| D-014 | Anonymous submissions | Proposed — awaiting founder |
| D-015 | Scope additions beyond the brief | Accepted |
| D-016 | QA approach | Accepted |
| D-017 | Build sequence | Proposed — awaiting founder |
| D-018 | Documentation location and format | Accepted |
| D-019 | Project name | Proposed — awaiting founder |
| D-020 | Agent team and model tiers | Accepted |
| D-021 | Proceeding without founder answers | Accepted (provisional) |
| D-022 | Application file | Accepted |
| D-023 | Phase 1–3 scope delivered | Accepted |
| D-024 | Implementation decisions by Agent 3 | Accepted |
| D-025 | Fixes after independent QA | Accepted |
| D-026 | QA model tier | Accepted |
| D-027 | Testing deferred at the founder's instruction | Accepted |
| D-028 | Phase 4 delivered (Delivery and impact) | Accepted |
| D-029 | Phase 5 delivered (Ideathons, Recognition, Profiles) | Accepted |
| D-030 | Phase 6 delivered (Dashboard completion, Insights, Administration, Agent hub) | Accepted |
| D-031 | Application file state | Accepted |
| D-032 | Feature presentation | Accepted |
| D-033 | Repository location | Accepted |
| D-034 | Rename of a demo persona | Accepted |
| D-035 | Differentiating features | Accepted |
| D-036 | Problem radar delivered | Accepted |
| D-037 | Reopen conditions delivered | Accepted |
| D-038 | Application file state | Accepted |
| D-039 | Collaboration by request | Accepted |
| D-040 | Idea progress tracker | Accepted |
| D-041 | Application file state (collaboration and tracker build) | Accepted |
| D-042 | Dotkonnekt design integrated from the founder's design file | Accepted |

---

## Decisions

### D-001 Framework for the single HTML file

- Decision ID: D-001
- Date: 2026-11-15
- Topic: Framework for the single HTML file
- Context: The MVP must be one HTML file, runnable from file://, with no build step.
- Problem being addressed: None recorded.
- Options considered: (a) plain JavaScript with template literals; (b) Preact + htm via CDN; (c) React via CDN with in-browser Babel; (d) attribute-driven libraries such as Alpine.js.
- Agent recommendations: Agent 3 recommended (a) with an auto-escaping `html` tagged-template helper, with (b) as runner-up.
- Final decision: Option (a), zero runtime dependencies, one classic script.
- Reasoning: Works offline from file://, has no CDN failure mode, and plain functions are safe to edit in stages.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-002 Information architecture

- Decision ID: D-002
- Date: 2026-11-15
- Topic: Information architecture
- Context: The brief names nine modules (A to I). The information architecture could be organised by module or around the idea lifecycle.
- Problem being addressed: None recorded.
- Options considered: Organise by the nine modules; organise around the idea lifecycle.
- Agent recommendations: Agent 2 recommended a lifecycle-centred IA with 18 hash routes, idea detail as the single source of truth, Delivery as a tab on idea detail plus a `#/delivery/:id` deep link, and a separate `#/ideathons/:id/pitch` route.
- Final decision: Lifecycle-centred IA adopted. The orchestrator trimmed the separate delivery and pitch routes; Delivery and Pitch day are tabs. The `#/delivery/:id` deep link and the `#/ideathons/:id/pitch` route are both dropped.
- Reasoning: Fewer disconnected screens; one place to see an idea's status, owner and decision history.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-003 Persona switching

- Decision ID: D-003
- Date: 2026-11-15
- Topic: Persona switching
- Context: None recorded.
- Problem being addressed: One browser must demonstrate six personas.
- Options considered: None recorded.
- Agent recommendations: Agents 1, 2 and 3 all recommended a persona switcher.
- Final decision: Six named demo users across five roles (employee x2, reviewer, team lead, leadership, admin), a persistent "Viewing as" chip, and role-dependent navigation and actions.
- Reasoning: None recorded.
- Impact on the application: Role-dependent navigation and actions; persistent "Viewing as" chip.
- Dependencies: None.
- Status: Accepted

### D-004 Idea lifecycle state machine

- Decision ID: D-004
- Date: 2026-11-15
- Topic: Idea lifecycle state machine
- Context: The brief defines five stages.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 1 recommended adding Needs info and Withdrawn states, a revisit date on Parked, "what would change our mind" on Declined, and that only humans may trigger decisions.
- Final decision: Adopted. "Awaiting owner" is a derived condition, not a state. The five brief stages remain the visible stepper. Default timelines are proposals and admin-editable: pickup 3 working days, decision 10, stale prototype 14.
- Reasoning: None recorded.
- Impact on the application: The visible stepper shows the five brief stages; timeline values are admin-editable.
- Dependencies: Q3 (founder confirmation of the 3/10/14 default timelines).
- Status: Accepted (timeline values: Proposed — awaiting founder)

### D-005 State management and persistence

- Decision ID: D-005
- Date: 2026-11-15
- Topic: State management and persistence
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 3 recommended one normalised store changed through named actions; derived selectors for all counts; status history as the lifecycle source of truth; an append-only points ledger; a single localStorage key with a schema version; and an in-memory fallback with a warning.
- Final decision: Adopted as recommended.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-006 Backend-ready service boundary

- Decision ID: D-006
- Date: 2026-11-15
- Topic: Backend-ready service boundary
- Context: The MVP has no backend. Future backend or Kompass integration must be possible.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agents 3 and 4 both recommended an adapter layer.
- Final decision: Views read through selectors and act through `api.*` and `AgentGateway.run()`, both of which return promises. A mock engine implements them in the MVP.
- Reasoning: A REST backend or Kompass engine can replace the mock without changing views.
- Impact on the application: Views do not call the store or localStorage directly; all effects go through the adapter layer.
- Dependencies: None recorded.
- Status: Accepted

### D-007 Agent roster

- Decision ID: D-007
- Date: 2026-11-15
- Topic: Agent roster
- Context: The project instructions define seven product agents.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 4 recommended (i) adding a deterministic, non-LLM orchestrator; (ii) splitting Review Intelligence into a Reviewer Brief agent and a Review Integrity agent; (iii) treating Idea Intelligence and Idea Enhancement as one submit-time pipeline with two identities.
- Final decision: Keep the seven agents as the visible roster. Add the orchestrator as infrastructure (rules engine). Do NOT split Review Intelligence; the integrity check is folded into it. Recommendation (iii) is not addressed in the final decision.
- Reasoning: Preserves the roster defined by the founder while keeping approval-gate logic in one place.
- Impact on the application: The orchestrator is infrastructure, not a visible agent; Review Intelligence includes the integrity check.
- Dependencies: None recorded.
- Status: Accepted

### D-008 AI honesty and human-authority policy

- Decision ID: D-008
- Date: 2026-11-15
- Topic: AI honesty and human-authority policy
- Context: The product must be AI-native without implying real AI execution.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Recommended by Agents 2 and 4.
- Final decision: No global chatbot. AI appears inside workflows. Every agent output carries a "Simulated" label that cannot be switched off. Each capability is classified as Computed, Templated or Canned. Agents may never record accept/park/merge/decline decisions, scores of record, awards, de-anonymisation, or announcements in a person's name.
- Reasoning: None recorded.
- Impact on the application: Every agent surface shows the "Simulated" label; agent outputs cannot change decisions, scores, awards, identities or announcements.
- Dependencies: None recorded.
- Status: Accepted

### D-009 Kompass integration approach

- Decision ID: D-009
- Date: 2026-11-15
- Topic: Kompass integration approach
- Context: 16 pages of Kompass staging documentation were read. External invocation, triggers/webhooks, human-approval steps and structured-output enforcement were not found in those pages. The founder notes that the staging documentation omits some features.
- Problem being addressed: None recorded.
- Options considered: Attempt a live integration; or simulate and stay integration-ready.
- Agent recommendations: Agent 4 recommended that all MVP agents be simulated (deterministic JavaScript over mock data, no network, no LLM), with an `AgentGateway` adapter boundary and human approval held in IdeaKonnekt.
- Final decision: No live Kompass call in the MVP. Future mapping uses only documented concepts (Smart Agents, Agentic Teams, Workflows and their components, AI Brain, Guardrails, Traces). Approval state lives in IdeaKonnekt. The app shows an integration map with a permanent "Not connected to Kompass" notice. Eleven questions for the Kompass team are listed in `04_ai_kompass.md`.
- Reasoning: None recorded beyond the context above.
- Impact on the application: Integration map screen; permanent "Not connected to Kompass" notice; no live calls.
- Dependencies: Q8 (Kompass team to answer the eleven integration questions).
- Status: Accepted

### D-010 Design system application

- Decision ID: D-010
- Date: 2026-11-15
- Topic: Design system application
- Context: The Dotkonnekt Design System artifact exists, but only its file inventory could be read. Exact token values are unread. Verified from the inventory: Geist and Geist Mono fonts; purple, gold, neutral, semantic and status colour families; gradients and glows; light and dark modes; a Kompass UI kit with Sidebar, Topbar, AgentList and ChatPanel.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 2 recommended purple as the action colour, gold reserved for recognition, and neutrals carrying the interface. Agent 3 recommended that all values be provisional approximations pending `tokens.css`.
- Final decision: Sidebar and topbar shell. Purple for actions; gold reserved for recognition. Light mode default with a dark toggle. All values held in one CSS variable block labelled provisional, to be replaced when `tokens.css` is supplied. The result will not be described as the official design system until then.
- Reasoning: None recorded.
- Impact on the application: All visual values are provisional and centralised in one CSS variable block.
- Dependencies: Q6 (founder to supply `tokens.css` / `colors_and_type.css` and the logo).
- Status: Accepted (provisional)

### D-011 Charts

- Decision ID: D-011
- Date: 2026-11-15
- Topic: Charts
- Context: The application needs charts for dashboard and analytics views.
- Problem being addressed: None recorded.
- Options considered: Hand-built inline SVG; Chart.js via CDN.
- Agent recommendations: Agents 2 and 3 recommended hand-built SVG.
- Final decision: Hand-built SVG.
- Reasoning: None recorded.
- Impact on the application: No chart library dependency.
- Dependencies: None recorded.
- Status: Accepted

### D-012 Pipeline board interaction

- Decision ID: D-012
- Date: 2026-11-15
- Topic: Pipeline board interaction
- Context: The pipeline board shows ideas by stage.
- Problem being addressed: None recorded.
- Options considered: Drag-and-drop between stages; action-driven moves.
- Agent recommendations: Agent 2 flagged drag-and-drop as a risk, stating that it permits status changes with no reason, contradicting the core promise.
- Final decision: No drag-and-drop. Stages change only through actions on the idea, so every change carries a reason.
- Reasoning: None recorded beyond the context above.
- Impact on the application: The pipeline board is read-mostly; stage changes happen through idea actions.
- Dependencies: None recorded.
- Status: Accepted (drag-and-drop Rejected)

### D-013 Recognition framework

- Decision ID: D-013
- Date: 2026-11-15
- Topic: Recognition framework
- Context: The brief requires recognition that rewards quality, collaboration and business impact rather than volume.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 1 proposed an outcome-weighted points table, five levels (Spark, Contributor, Builder, Catalyst, Pioneer), ten badges, and anti-gaming rules, with votes earning no points directly. Agent 1 also proposed a small community-signal bonus of 5 points at Accepted, which is not part of the final decision text below.
- Final decision: Adopt the structure: points vest at outcomes, every ledger row cites its rule, and values are admin-editable. The specific point values remain proposals.
- Reasoning: None recorded.
- Impact on the application: Points ledger rows cite their rule; point values are editable in administration.
- Dependencies: None recorded.
- Status: Accepted (values: Proposed — awaiting founder)

### D-014 Anonymous submissions

- Decision ID: D-014
- Date: 2026-11-15
- Topic: Anonymous submissions
- Context: The brief allows optional anonymous submission for sensitive process feedback. Credit and points depend on knowing the author.
- Problem being addressed: Credit and points for anonymous ideas, and who can see the author.
- Options considered: None recorded.
- Agent recommendations: Agents 1, 2 and 5 all raised the question of who can see the author.
- Final decision: None yet (proposal only). Proposed: identity hidden in every view; points held in escrow and claimable when the author reveals themselves. Browser storage is readable on the device, so this is a display rule, not a security control.
- Reasoning: None recorded.
- Impact on the application: None until decided.
- Dependencies: Q2 (founder: can anyone see an anonymous author, and is escrow-and-reveal acceptable).
- Status: Proposed — awaiting founder

### D-015 Scope additions beyond the brief

- Decision ID: D-015
- Date: 2026-11-15
- Topic: Scope additions beyond the brief
- Context: The master instructions and the brief define the baseline modules. Agent 1 analysed gaps.
- Problem being addressed: Gaps identified by Agent 1 that the brief does not cover but that the workflows require.
- Options considered: None recorded.
- Agent recommendations: Agent 1 recommended the additions and exclusions listed in the final decision.
- Final decision: Accepted additions: notifications inbox; unified activity log; agent approval cards and run log; Needs info loop; parked revisit dates; impact method field (baseline, evidence, confidence); innovation time pool; decline with "what would change our mind". Deferred: guided demo tour (to the polish phase). Excluded: side chatbot, real file upload, email/Slack notifications, SSO, streaks or login points, leaderboard of idea counts, live Kompass calls.
- Reasoning: None recorded.
- Impact on the application: The listed additions are in scope; the listed exclusions are out of scope for the MVP.
- Dependencies: None recorded.
- Status: Accepted

### D-016 QA approach

- Decision ID: D-016
- Date: 2026-11-15
- Topic: QA approach
- Context: The MVP must be tested against the acceptance criteria before completion.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 5 produced an acceptance checklist of 70 items, all marked "Not yet tested"; a cross-module consistency matrix; quality gates per phase; a dead-control scan; and headless-browser journeys loading the file via file://.
- Final decision: Adopted.
- Reasoning: None recorded.
- Impact on the application: Acceptance checklist, consistency matrix and quality gates apply to the build. None of the 70 items has been tested.
- Dependencies: None recorded.
- Status: Accepted

### D-017 Build sequence

- Decision ID: D-017
- Date: 2026-11-15
- Topic: Build sequence
- Context: The build must proceed in manageable stages.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: Agent 3 proposed twelve slices.
- Final decision: Proposed grouping into phases: 0 Sign-off; 1 Foundation; 2 Idea core; 3 Review and pipeline; 4 Delivery and impact; 5 Ideathons, recognition, profiles; 6 Leadership, admin, agent hub; 7 Hardening and delivery.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Proposed — awaiting founder

### D-018 Documentation location and format

- Decision ID: D-018
- Date: 2026-11-15
- Topic: Documentation location and format
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Markdown files in the repository under `docs/`. Agent discovery reports are kept under `docs/discovery/`.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-019 Project name

- Decision ID: D-019
- Date: 2026-11-15
- Topic: Project name
- Context: The working name in the project is "IdeaKonnekt".
- Problem being addressed: None recorded.
- Options considered: "Project Polaris" (proposed); alternatives Lodestar and Kindle.
- Agent recommendations: None recorded.
- Final decision: None yet. Proposed: "Project Polaris". The name has not been checked against existing internal names or trademarks.
- Reasoning: None recorded.
- Impact on the application: None until decided.
- Dependencies: Q7 (founder to confirm the project name).
- Status: Proposed — awaiting founder

### D-020 Agent team and model tiers

- Decision ID: D-020
- Date: 2026-11-15
- Topic: Agent team and model tiers
- Context: Agents were run during the discovery phase on the model tiers listed below. Agent 3 produced architecture only in this phase.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Agents 1 to 4 ran on the Sonnet tier; Agents 5 and 6 ran on the Haiku tier.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

**Limitation (D-020):** The environment allows choosing a model tier but not a specific model version. The founder asked for "Claude 4.5 Haiku". The documentation agent (Agent 6) reported its own model as Haiku 5.5 (`claude-haiku-5-5`), so the Haiku-tier agents did not run on Claude 4.5 Haiku. The Sonnet version used was not reported.

### D-021 Proceeding without founder answers

- Decision ID: D-021
- Date: 2026-11-16
- Topic: Proceeding without founder answers
- Context: The founder instructed "start phase 1 - 3" without answering open questions Q1–Q7.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Proceed on the defaults proposed in the discovery plan: leadership approves hours from a pool; anonymous author hidden from all roles; timelines 3/10/14 working days as config defaults; provisional design tokens; working name "Polaris" shown as "IdeaKonnekt · Polaris".
- Reasoning: None of the open questions block phases 1–3; all defaults are reversible.
- Impact on the application: The application shows the working name "IdeaKonnekt · Polaris"; anonymous authors are hidden from all roles; timelines are config defaults.
- Dependencies: Q1–Q7 remain open.
- Status: Accepted (provisional)

### D-022 Application file

- Decision ID: D-022
- Date: 2026-11-16
- Topic: Application file
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Single file `idea-hub.html` at the repository root; 3,136 lines, 353,038 bytes after fixes; zero runtime JavaScript dependencies; the only external reference is an optional Google Fonts link for Geist with a system-font fallback.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-023 Phase 1–3 scope delivered

- Decision ID: D-023
- Date: 2026-11-16
- Topic: Phase 1–3 scope delivered
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Phase 1: app shell, hash router with role guards, six demo personas, single store with named actions, localStorage persistence under key `ideahub.v1` with in-memory fallback, services layer (`api.*`, `AgentGateway`, `MockEngine`), role-aware Home, handler audit. Phase 2: Explore, Idea detail with five tabs, Submit with simulated Idea Intelligence and Idea Enhancement, Drafts, My ideas, anonymous masking, Withdraw, minimal profile page. Phase 3: Review queue and workspace with simulated Review Intelligence brief, decision rules, owner assignment, review clocks, Pipeline with Innovation Workflow approval cards. Admin offers a working Reset demo data; other admin content is read-only. Ideathons, Recognition, Insights and Agent log are labelled placeholders naming the phase that delivers them.
- Reasoning: None recorded.
- Impact on the application: Ideathons, Recognition, Insights and Agent log show placeholders that name the phase that delivers them. Admin content other than Reset demo data is read-only.
- Dependencies: None recorded.
- Status: Accepted

### D-024 Implementation decisions by Agent 3

- Decision ID: D-024
- Date: 2026-11-16
- Topic: Implementation decisions by Agent 3
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: Re-rendering the Submit form on each keystroke (rejected).
- Agent recommendations: Made by Agent 3; accepted by the orchestrator.
- Final decision: Submit form is stateful and kept out of the global render loop so typing keeps focus; suggested scores in the reviewer brief are collapsed by default so reviewers form their own view first; scores are required for accept, park, merge and decline, and request-info needs only a question of at least 20 characters; review clock uses working days and pauses while an idea is in Needs info; workflow proposals are keyed per panel per day (reminders) or per idea (revisit), and dismissing a revisit snoozes it for 7 days; anonymity is enforced at render time and anonymous ideas have no co-authors; live assist runs are not stored, only submit, decision and workflow runs are recorded.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-025 Fixes after independent QA

- Decision ID: D-025
- Date: 2026-11-16
- Topic: Fixes after independent QA
- Context: Agent 5 found no P0 or P1 defects, one P2 and seven P3 defects (D1–D8 in the QA report), plus observations.
- Problem being addressed: The defects D1–D8 and the observations in the QA report.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: All were fixed by Agent 3 together with six further items raised by the orchestrator (pipeline fits five columns at 1200px and above; simulated latency removed from all non-agent actions and state saved synchronously; code cleanups; mobile search overlay; attachment-label warning on anonymous ideas; participation metric derived over 90 days). Decisions made during fixes: withdrawn ideas and drafts are excluded from the total and the Home page says so; "Awaiting review" means submitted, in review or needs info, matching the Pipeline; the sticky right column in the review workspace was removed; six inactive new-joiner users were added to the seed, giving 36 employees and 81% participation; anonymous submissions are not counted as participation.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-026 QA model tier

- Decision ID: D-026
- Date: 2026-11-16
- Topic: QA model tier
- Context: Discovery-phase QA strategy used Haiku.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: The QA agent for build testing ran on the Sonnet tier rather than Haiku.
- Reasoning: Testing required writing and interpreting browser automation.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-027 Testing deferred at the founder's instruction

- Decision ID: D-027
- Date: 2026-11-16
- Topic: Testing deferred at the founder's instruction
- Context: During phases 4–6 the founder instructed that testing be forgone for now, the code changes be made, and the tests be done at the end.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Phases 5 and 6 were built with a load-and-click smoke check only (no test suites, no screenshot review by the builder, no independent QA). Full testing moves to phase 7.
- Reasoning: None recorded.
- Impact on the application: Defects in phases 5–6 may exist undetected.
- Dependencies: None recorded.
- Status: Accepted

### D-028 Phase 4 delivered (Delivery and impact)

- Decision ID: D-028
- Date: 2026-11-16
- Topic: Phase 4 delivered (Delivery and impact)
- Context: Build note: phase 4 was built across interrupted agent runs (one run hit a usage limit, two were stopped by the founder); the final state was verified by the orchestrator.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Innovation-hours requests against a quarterly pool, with leadership approval or decline with reason; approval moves Accepted to Prototype. Delivery tab with contributors, hours logging (overspend flagged, not blocked), tasks, updates and a stale indicator. Stale-prototype nudge proposals. Mark Implemented requires an outcome summary, at least one impact entry and contribution shares totalling 100 percent. Announcements. Impact verification by a second person (leadership or admin, never the owner or an author).
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-029 Phase 5 delivered (Ideathons, Recognition, Profiles)

- Decision ID: D-029
- Date: 2026-11-16
- Topic: Phase 5 delivered (Ideathons, Recognition, Profiles)
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Ideathons: list; create; five phases that cannot be skipped; linked entries; agent-proposed shortlist approved by the organiser; pitch day with timer; panel scores and one audience vote per persona; results confirmed by the organiser; simulated hackathon handoff. Recognition: append-only points ledger where every row cites a rule; levels; ten badges; individual, team and impact leaderboards; Idea of the Quarter and Annual Innovation Award confirmed by leadership; reciprocal-vote flags for human review. Profiles and team pages. Decisions by Agent 3: combined ideathon score is 70 percent panel and 30 percent audience, from config; shortlist score weights 40 upvotes, 35 template completeness, 25 discussion breadth; impact bonus is a confidence base (low 25, medium 40, high 60) times a size band (1, 1.5, 2), clamped to 25–150 and split by contribution share; reciprocal-vote threshold is 2 votes each way; points are never reversed; anonymous-idea points are held in escrow and excluded from all public totals, claimable by "Reveal and claim", which is blocked when the idea has anonymous co-authors; an ideathon counts as past only once marked complete.
- Reasoning: None recorded.
- Impact on the application: Scope simplifications: the "declined then resubmitted" bonus is not implemented because there is no resubmission flow; the community-signal bonus at Accepted was dropped; the Comeback badge was redefined as accepted after being parked or sent back for more information; pitch timers and shortlist checkbox selections are not persisted.
- Dependencies: None recorded.
- Status: Accepted

### D-030 Phase 6 delivered (Dashboard completion, Insights, Administration, Agent hub)

- Decision ID: D-030
- Date: 2026-11-16
- Topic: Phase 6 delivered (Dashboard completion, Insights, Administration, Agent hub)
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Insights with period filter and hand-built charts, each with a data table; leadership summary dialog with copy. Admin with ten tabs (categories, review panels, scoring criteria, timelines, recognition, innovation time, ideathons, platform metrics, data with reset, export and import, audit log). Agent hub with activity traces, agent registry, five flows, Kompass integration map with a permanent "Not connected to Kompass" notice and 11 open questions that an admin can mark answered, and pending approvals. Global search covers ideathons and teams. All placeholder pages removed. Decisions by Agent 3: weighted review score treats effort in reverse; recognition setting changes apply to future ledger rows only; only people with the Reviewer role can be added to a panel; the "needs-info auto-park days" setting only flags an idea as stuck, there is no automatic parking; import validates, asks for confirmation and rolls back if the self-check fails; timeline changes re-date only ideas currently under review.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-031 Application file state

- Decision ID: D-031
- Date: 2026-11-16
- Topic: Application file state
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: `idea-hub.html` is 5,597 lines and 710,503 bytes after phase 6; schema version 4; build string 0.6.0-phase6; still one file with zero runtime JavaScript dependencies. Stored data from older versions resets to the seed with a visible notice.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-032 Feature presentation

- Decision ID: D-032
- Date: 2026-11-16
- Topic: Feature presentation
- Context: The founder requested a PowerPoint explaining the features, why they exist and how they will be used.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: `Idea_Hub_Features.pptx`, 18 slides after two feature slides were added, built by the orchestrator with screenshots captured from the current build.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

### D-033 Repository location

- Decision ID: D-033
- Date: 2026-11-16
- Topic: Repository location
- Context: The founder moved to another computer; the session could not reach it.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Files were delivered in the chat for the founder to save into the repository manually. The repository copies of `idea-hub.html` and the documents may therefore be out of date until saved.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

---

### D-034 Rename of a demo persona

- Decision ID: D-034
- Date: 2026-11-16
- Topic: Rename of a demo persona
- Context: The founder asked to rename the demo employee "Priya Nair" to "Ted Lasso".
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: The display name was changed in the app and the presentation. The internal id `u_priya` is unchanged.
- Reasoning: None recorded.
- Impact on the application: The demo employee displays as "Ted Lasso". The internal id `u_priya` is unchanged.
- Dependencies: None recorded.
- Status: Accepted

---

### D-035 Differentiating features

- Decision ID: D-035
- Date: 2026-11-16
- Topic: Differentiating features
- Context: The founder asked what could make the product stand out, then asked the orchestrator to pick the options likely to get the best response from the leadership team.
- Problem being addressed: None recorded.
- Options considered: (1) problem radar; (2) decisions that reopen themselves; (3) one assistant running on Kompass for real; (4) conviction points instead of upvotes; (5) accepted idea to draft prototype brief.
- Agent recommendations: None recorded.
- Final decision: Build (1) and (2) now. (3) remains blocked on the undocumented Kompass invocation method. (4) and (5) are not built.
- Reasoning: Both chosen features reinforce the visible-decision promise, are demonstrable in the single file with no backend, and reuse the existing similarity matching and the "what would change our mind" field. Whether these are unique in the market was not researched.
- Impact on the application: Features (1) and (2) were built; see D-036 and D-037. Features (3), (4) and (5) are not in the application.
- Dependencies: Option (3) depends on the Kompass invocation method, which is undocumented. Features (1) and (2) reuse the existing similarity matching and the "what would change our mind" field.
- Status: Accepted

---

### D-036 Problem radar delivered

- Decision ID: D-036
- Date: 2026-11-16
- Topic: Problem radar delivered
- Context: Delivery of option (1) from D-035.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: Ideas are grouped by similarity of their problem statements and tags (average-link clustering, threshold 0.34, tuned on the seed; singletons excluded). The seed yields 9 recurring problems after 13 seed ideas were added. Routes `#/problems` and `#/problems/:id`. States: Solved, In progress, Unsolved (recurring). Leadership and admin can rename a problem, assign a sponsor, acknowledge it, and launch an ideathon prefilled from the problem. Everyone can mark "I have this problem too" (earns no points) and submit an idea for the problem. The problem radar is shown on idea detail, in the reviewer brief, on leadership Home, in Insights and in search. Anonymous authors are counted but never named.
- Reasoning: None recorded.
- Impact on the application: The problem radar is available at the routes above and appears on the surfaces listed in the final decision. Known limits recorded by Agent 3: labels are automatic and unpolished; the threshold is sensitive to new ideas; a problem's id is tied to its earliest idea.
- Dependencies: Reuses the existing similarity matching (see D-035).
- Status: Accepted

---

### D-037 Reopen conditions delivered

- Decision ID: D-037
- Date: 2026-11-16
- Topic: Reopen conditions delivered
- Context: Delivery of option (2) from D-035.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: On Park (at least one condition is required; the revisit date counts) and on Decline (conditions optional), reviewers set reopen conditions of six types: date, raised again, dependency, capacity, demand, manual. An any/all rule applies. Conditions are evaluated from live state. Idea pages show "What would bring this back" with progress. When conditions are met, the Innovation Workflow assistant proposes reopening. A reviewer on that panel or an admin approves the reopen, which returns the idea to Under review with a fresh clock, history and notifications. Dismissing a proposal requires a reason and snoozes it for 14 days. This replaces the earlier parked-revisit proposal.
- Reasoning: None recorded.
- Impact on the application: Reopen conditions are set on Park and Decline and shown on idea pages. The Innovation Workflow assistant proposes reopening when conditions are met. Limits recorded by Agent 3: conditions can only be set when recording a decision; the earlier return-to-review action remains in the file as unused code.
- Dependencies: Uses the existing "what would change our mind" field (see D-035).
- Status: Accepted

---

### D-038 Application file state

- Decision ID: D-038
- Date: 2026-11-16
- Topic: Application file state
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: `idea-hub.html` is 6,249 lines and 806,510 bytes; schema version 5; build 0.7.0-radar-reopen.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

---

### D-039 Collaboration by request

- Decision ID: D-039
- Date: 2026-11-16
- Topic: Collaboration by request
- Context: The founder asked that a person who wants to collaborate should send a request which the owner of the idea accepts before they work together.
- Problem being addressed: Previously "I want to help build this" recorded an offer immediately, offers could only be answered once an idea was in Prototype, and co-author requests had no accept or decline control.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: One unified collaboration-request entity with two types (co-author, help build), a required message, optional role and hours. Requests go to the author and co-authors until a delivery owner is assigned, then to the owner. Team lead and admin can also answer. Decline requires a note. One re-request is allowed after a decline. Members can leave, and deciders can remove a member with a reason. Only accepted members can edit the tracker, post check-ins or edit delivery. Anonymous ideas accept help-build requests only and never name the author. Parked ideas are closed to new requests. The old volunteer entity and its actions were removed, and seeded data was migrated.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

---

### D-040 Idea progress tracker

- Decision ID: D-040
- Date: 2026-11-16
- Topic: Idea progress tracker
- Context: The founder asked for an inbuilt tracker so people can mark their own progress on an idea.
- Problem being addressed: None recorded.
- Options considered: A separate tracker beside the existing delivery task list, or one unified list.
- Agent recommendations: None recorded.
- Final decision: A "Team & progress" tab on every idea from submission onward, with milestones (assignee, due date, status Not started / In progress / Blocked / Done, blocker note), check-ins, a "My work" block, a "My tasks" view across ideas, and a derived progress bar on idea headers and cards. The tracker is the delivery task list: the separate delivery tasks and updates were removed and migrated to milestones and check-ins. The assignee changes the status of their own items. Author, co-author, owner, team lead and admin manage all items. The Innovation Workflow assistant proposes nudges for items blocked 5 days or more and for ideas with no check-in in the stale period; a person approves each nudge.
- Reasoning: Two competing lists would confuse owners in Prototype.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

---

### D-041 Application file state (collaboration and tracker build)

- Decision ID: D-041
- Date: 2026-11-16
- Topic: Application file state
- Context: None recorded.
- Problem being addressed: None recorded.
- Options considered: None recorded.
- Agent recommendations: None recorded.
- Final decision: `idea-hub.html` is 6,753 lines and 882,626 bytes; schema version 6; build 0.8.0-collab-tracker. Stored data from older versions resets to the seed.
- Reasoning: None recorded.
- Impact on the application: None recorded.
- Dependencies: None recorded.
- Status: Accepted

---

### D-042 Dotkonnekt design integrated from the founder's design file

- Decision ID: D-042
- Date: 2026-11-16
- Topic: Dotkonnekt design integrated from the founder's design file
- Context: The founder supplied a separate copy of `idea-hub.html` containing design changes and asked for them to be integrated. That file was a different line of work: it was based on the phase 1–3 build with its own phase 6 screens (insights, agent log, admin), without phases 4 and 5.
- Problem being addressed: None recorded.
- Options considered: Adopt the supplied file as the new base, or take only its design layer into the current build.
- Agent recommendations: None recorded.
- Final decision: Take only the design layer. Integrated: the tokens block, which the supplied file states was taken from the Dotkonnekt Design System artifact `tokens.css` (read 2026-11-16), including its documented deviations for text contrast; Geist and Geist Mono embedded as subsetted woff2 so the file makes no network requests (the Google Fonts link was removed); the official Dotkonnekt logo mark and wordmark in the sidebar; pill-shaped buttons with a black primary button (white in dark theme); wider letter-spacing on eyebrow labels, navigation labels and table headers; press and reduced-motion behaviour on buttons. Added by the orchestrator: values for ten token names that exist only in the current build (four extra category colours and six chart series colours), derived from the same colour ramps and marked as derived. Not taken: the supplied file's own insights, agent log and admin screens, because the current build already has fuller versions. The sidebar subtitle now reads "IdeaKonnekt" as in the supplied file, instead of "IdeaKonnekt · Polaris".
- Reasoning: The current build contains phases 4–6 and later features that the supplied file lacks.
- Impact on the application: `idea-hub.html` is now 960,682 bytes; build 0.8.1-dotkonnekt-design; schema version unchanged at 6. Verification: loaded from file:// with no page or console errors and no network requests; both fonts reported as loaded; self-check clean; the orchestrator viewed twelve screens in light theme and twelve in dark theme at reduced size. Limitation: the orchestrator did not verify the token values against the design system artifact itself, which it could not read; the icons remain hand-drawn and are not the official set. This supersedes the provisional-token status in D-010.
- Dependencies: None recorded.
- Status: Accepted

---

## Rejected recommendations

| What | Who recommended | Why rejected |
|---|---|---|
| React via CDN with in-browser Babel (option c, D-001) | Agent 3 (rejection recorded in 03_frontend.md) | Startup cost, size, fragility, and offline failure. |
| Alpine.js and attribute-driven libraries (option d, D-001) | Agent 3 (rejection recorded in 03_frontend.md) | Logic embedded in markup is harder to edit safely at 6,000+ lines, and it adds a runtime dependency. |
| Chart.js via CDN (option, D-011) | Named as runner-up by Agent 3 | Not adopted; D-011 selected hand-built SVG. Reason not recorded. |
| Drag-and-drop between pipeline stages (D-012) | Agent 2 flagged it as a risk | Permits status changes with no reason, contradicting the core promise. |
| Splitting Review Intelligence into separate Reviewer Brief and Review Integrity agents (D-007 recommendation ii) | Agent 4 | Not adopted. The integrity check is folded into Review Intelligence to keep the roster as defined by the founder. |
| Separate delivery and pitch-day routes (D-002 recommendation) | Agent 2 | Trimmed by the orchestrator; Delivery and Pitch day are tabs. Reason recorded in D-002: fewer disconnected screens. |

---

## Scope changes

### Additions to the original brief (D-015, D-004, D-007)

- Notifications inbox.
- Unified activity log.
- Agent approval cards and run log.
- Needs info loop (D-004 and D-015).
- Parked revisit dates (D-004 and D-015).
- Impact method field (baseline, evidence, confidence).
- Innovation time pool.
- Decline with "what would change our mind" (D-004 and D-015).
- Withdrawn state (D-004).
- Deterministic, non-LLM orchestrator as infrastructure (D-007).

### Exclusions from the original brief (D-015 and D-009)

- Side chatbot.
- Real file upload.
- Email and Slack notifications.
- SSO.
- Streaks or login points.
- Leaderboard of idea counts.
- Live Kompass calls.

### Deferred

- Guided demo tour (deferred to the polish phase, D-015).

---

## Technical constraints

- The entire MVP is one HTML file with inline CSS and JavaScript.
- No build step.
- Must run from file://.
- No backend; use mock data.
- Persist to localStorage, with a reset-demo-data option.
- Every visible control must be functional.
- Simulated AI must be labelled as simulated.
- Markdown documentation is allowed separately.

---

## Known limitations (as of 2026-11-16)

- Dotkonnekt token values are unread. Only the file inventory of the design system could be read. All visual values are provisional. (Superseded 2026-11-16 by D-042: token values now come from the founder's design file.)
- Kompass external invocation, triggers, approval steps and structured output are undocumented in the pages read.
- The Kompass documentation read is a staging site. The founder notes that it omits some features.
- Subagent model versions cannot be selected, only the tier. Agent 6 self-reported Haiku 5.5, not the requested Claude 4.5 Haiku; the Sonnet version is unknown (D-020).
- The 6,000 to 8,000 line estimate is for the complete MVP; the file is 3,136 lines after phases 1 to 3 (D-022).
- After confirming Withdraw, focus lands on page content because the button no longer exists.
- Tag suggestions are keyword heuristics and can be odd.
- Reviewer-brief scores and lean are rule-based heuristics.
- Anonymity is a display rule only; browser storage is readable on the device.
- An author can still type identifying text into an attachment label.
- Icons are hand-drawn, not the official Dotkonnekt set. Token values come from the founder's design file and were not checked by the orchestrator against the design system artifact.
- No Kompass connection.
- Flow diagram arrows wrap awkwardly on narrow rows.
- Admin forms re-render after a save, so unsaved edits in other fields of the same tab are lost.
- Charts have no hover tooltips; the data tables carry the detail.
- Layout of phase 5 and 6 screens has not been reviewed at mobile widths or in dark theme.
- Agent statistics rely on seeded runs plus runs recorded during use.
- Original seeded co-authors have no request record and cannot use Leave; the first request row on the Team tab shows its avatar on a separate line (cosmetic).

---

## Unresolved questions

| ID | Question | Owner | Blocks what |
|---|---|---|---|
| Q1 | Who approves innovation hours, and is there a quarterly pool? | Founder | Phase 4 (innovation time pool and approval flow) |
| Q2 | Can anyone see an anonymous author, and is escrow-and-reveal acceptable? | Founder | Phase 2 (submission) and Phase 5 (recognition for anonymous ideas) |
| Q3 | Confirm the default timelines of 3, 10 and 14 days. | Founder | Nothing; proposed values ship as editable defaults |
| Q4 | How is impact verified: self-reported or second-person confirmed? | Founder | Phase 4 (impact entry) and Phase 5 (impact bonus) |
| Q5 | Is the demo audience internal only, or also customers? | Founder | Phase 6 (prominence of the Kompass integration map) |
| Q6 | Supply `tokens.css` / `colors_and_type.css` and the logo from the design system. | Founder | Phase 1 visual fidelity; build can start on provisional tokens — Resolved 2026-11-16 by the founder's design file (D-042). |
| Q7 | Confirm the project name. | Founder | Nothing technical; naming in the app and documents |
| Q8 | The eleven integration questions for Kompass listed in `04_ai_kompass.md`, section 6. | Kompass team | Any real Kompass integration; does not block the MVP |

## Testing performed (phases 1–3)

- Builder tests (Agent 3), Playwright with Chromium, file loaded via file://, re-run by the orchestrator on 2026-11-16 after fixes: flows 21 pass; misc 5 pass; decisions 8 pass; overflow 52 pass; fixes 93 pass including 336 route visits across six personas at 375 and 1280 px with no page or console errors; routes script: 65 routes for each of six personas with no errors (reported by Agent 3; not re-run by the orchestrator).
- Independent QA (Agent 5) before fixes: 30 check rows — 25 pass, 3 fail, 1 not tested, 1 observation; dead-control scan of about 1,500 clicks found one dead control; anonymity scan across six other personas found no leaks; offline pass succeeded. The three failures and the dead control were addressed in D-025.
- The independent QA agent has NOT re-tested the build after the fixes; post-fix verification is by the builder's tests and the orchestrator's re-run and screenshot review (Home dark 1280, Pipeline 1280, and pre-fix Home and Review workspace).
- Not tested: browsers other than Chromium; screen readers; real touch devices; two tabs open at once; dark theme on pages other than Home after fixes; review-timer thresholds under changed configuration; opening the file on the founder's own machine.

### Phases 4–6

- Phase 4: builder test script phase4.js, 95 checks, all passed when re-run by the orchestrator on 2026-11-16, together with flows 21, misc 5, decisions 8, overflow 52 and fixes 93. These runs were made BEFORE phases 5 and 6 were added and have not been repeated since.
- Phase 5: smoke check only by the builder (about 30 routes as four personas with no page or console errors; one scripted pass dispatching the new actions). Not tested beyond that.
- Phase 6: smoke check only by the builder (new routes as five personas with no page or console errors; each new action dispatched once; overflow check at 375, 768 and 1920 on new views). Not tested beyond that.
- Orchestrator: loaded 14 screens across five personas while capturing screenshots for the presentation, with no page errors, and viewed 9 of them at reduced size.
- No independent QA has been run on phases 4–6. The existing phase 1–4 test scripts have not been re-run against the final file.
- Problem radar and reopen conditions: smoke check only by the builder (new and changed routes as five personas with no page or console errors; each new action dispatched once, including an approve-reopen end to end; overflow check at four widths). The orchestrator viewed four of the new screens. Not tested beyond that.
- Collaboration requests and progress tracker: smoke check only by the builder (changed routes as seven personas with no page or console errors; each new or changed action dispatched once, including request, accept, member updates own item, and request, decline, re-request). The orchestrator viewed the Team and progress tab for one idea. Not tested beyond that. The existing phase 1–4 test scripts reference actions that were removed (volunteer and delivery task actions) and will need updating before they can be re-run.

---

## Change history

| Date | Change |
|---|---|
| 2026-11-15 | Log established at end of discovery phase. |
| 2026-11-16 | Phases 1–3 built, independently tested, defects fixed; entries D-021 to D-026 added. |
| 2026-11-16 | Phases 4–6 built; testing deferred to phase 7 at the founder's instruction; entries D-027 to D-033 added. |
| 2026-11-16 | Persona renamed; problem radar and reopen conditions added; entries D-034 to D-038. |
| 2026-11-16 | Collaboration requests and progress tracker added; entries D-039 to D-041. |
| 2026-11-16 | Dotkonnekt tokens, embedded fonts and logo integrated from the founder's design file; entry D-042. |
