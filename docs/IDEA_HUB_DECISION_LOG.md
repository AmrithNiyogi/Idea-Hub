# Idea Hub — Decision Log

This log records the significant product, technical, architectural and design decisions taken during the Idea Hub discovery phase, together with the agent recommendations behind them, rejected options, scope changes, technical constraints, known limitations and open questions. It is maintained throughout the project and is not written retrospectively. Each entry is dated when it was recorded. Nothing described in this log has been built or tested.

- Maintained by: Agent 6 (documentation agent, Haiku tier)
- Last updated: 2026-11-15
- Project phase: Discovery (no application code written)

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
- Agent recommendations: Agent 4 recommended that all MVP agents be simulated (deterministic JavaScript over mock data, no network, no LLM), with an `AgentGateway` adapter boundary and human approval held in Idea Hub.
- Final decision: No live Kompass call in the MVP. Future mapping uses only documented concepts (Smart Agents, Agentic Teams, Workflows and their components, AI Brain, Guardrails, Traces). Approval state lives in Idea Hub. The app shows an integration map with a permanent "Not connected to Kompass" notice. Eleven questions for the Kompass team are listed in `04_ai_kompass.md`.
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
- Context: The working name in the project is "Idea Hub".
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

## Known limitations (as of 2026-11-15)

- Dotkonnekt token values are unread. Only the file inventory of the design system could be read. All visual values are provisional.
- Kompass external invocation, triggers, approval steps and structured output are undocumented in the pages read.
- The Kompass documentation read is a staging site. The founder notes that it omits some features.
- Subagent model versions cannot be selected, only the tier. Agent 6 self-reported Haiku 5.5, not the requested Claude 4.5 Haiku; the Sonnet version is unknown (D-020).
- The file size (6,000 to 8,000 lines) is an estimate.
- No application code has been written.
- Nothing has been tested.

---

## Unresolved questions

| ID | Question | Owner | Blocks what |
|---|---|---|---|
| Q1 | Who approves innovation hours, and is there a quarterly pool? | Founder | Phase 4 (innovation time pool and approval flow) |
| Q2 | Can anyone see an anonymous author, and is escrow-and-reveal acceptable? | Founder | Phase 2 (submission) and Phase 5 (recognition for anonymous ideas) |
| Q3 | Confirm the default timelines of 3, 10 and 14 days. | Founder | Nothing; proposed values ship as editable defaults |
| Q4 | How is impact verified: self-reported or second-person confirmed? | Founder | Phase 4 (impact entry) and Phase 5 (impact bonus) |
| Q5 | Is the demo audience internal only, or also customers? | Founder | Phase 6 (prominence of the Kompass integration map) |
| Q6 | Supply `tokens.css` / `colors_and_type.css` and the logo from the design system. | Founder | Phase 1 visual fidelity; build can start on provisional tokens |
| Q7 | Confirm the project name. | Founder | Nothing technical; naming in the app and documents |
| Q8 | The eleven integration questions for Kompass listed in `04_ai_kompass.md`, section 6. | Kompass team | Any real Kompass integration; does not block the MVP |

---

## Change history

| Date | Change |
|---|---|
| 2026-11-15 | Log established at end of discovery phase. |
