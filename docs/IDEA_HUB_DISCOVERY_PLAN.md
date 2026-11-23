# KonnektIdea — Discovery Plan (consolidated)

**Date:** 15 November 2026 · **Phase:** Discovery complete, awaiting founder review · **Status:** No application code has been written.

**Proposed project name:** Project Polaris (see section 10).

## How this plan was produced

Five specialist agents analysed their areas independently from one shared, source-verified context pack. I then reviewed, challenged and consolidated their findings. A sixth agent maintains the decision log.

| Agent | Responsibility | Model tier requested | Output |
|---|---|---|---|
| 1 | Product strategy and requirements | Sonnet | `discovery/01_product.md` |
| 2 | UI/UX and design system | Sonnet | `discovery/02_uiux.md` |
| 3 | Frontend engineering (architecture only in this phase) | Sonnet | `discovery/03_frontend.md` |
| 4 | AI, agentic workflows and Kompass | Sonnet | `discovery/04_ai_kompass.md` |
| 5 | Quality assurance (strategy only; nothing tested) | Haiku | `discovery/05_qa.md` |
| 6 | Decision log and documentation | Haiku | `IDEA_HUB_DECISION_LOG.md` |

Limitation: this environment lets me choose the Sonnet or Haiku tier for a subagent, but not a specific version. You asked for Claude 4.5 Haiku; the documentation agent reported its own model as Haiku 5.5, so the Haiku agents did not run on 4.5. The Sonnet version was not reported.

### What is verified and what is not

| Source | Status |
|---|---|
| KonnektIdea brief (project doc) | Read in full. |
| Kompass documentation (staging site) | 16 pages read. Workflow, component, smart agent, agentic team and AI Brain concepts are verified. How an external app invokes Kompass, triggers, webhooks, approval steps and structured output are **not documented** in what we read. |
| Dotkonnekt design system artifact | **Only the file inventory could be read.** Font families, colour families, token groups and the Kompass UI kit's component names are verified. Every exact value (hex, spacing, radius, type size) is unread. |
| Repo folder | Empty git repository. |

---

## 1. Analysis of the original requirements

**The core insight.** KonnektIdea is a reply guarantee, not an idea box. The brief says so itself: people stop submitting when ideas disappear. Ideathons, recognition and AI all amplify that loop. Every design choice is tested against one question: can the submitter see, right now, where their idea is, who owns the next move, and why a decision was made?

**Explicit in the brief:** four categories; a five-field template; drafts, co-authors, anonymous option, attachments; similar-idea check while typing; upvotes, comments, volunteer, follow; agent thread summaries; the five-stage flow with category panels, three scoring criteria and mandatory written reasons; innovation time; a status board; ideathons with pitch day and a hackathon link; credit, impact tracking, quarterly and annual awards.

**Implied but never stated:** a review clock with escalation; a notifications inbox (follow is meaningless without one); roles and permissions; a way for an author to answer a reviewer's question; a baseline for impact claims; an owner for every next step.

**Tensions in the brief, and how I propose to resolve them**

| # | Tension | Resolution |
|---|---|---|
| 1 | Anonymous submission vs. credit staying with the author | Identity is hidden in every view. Points accrue to a sealed escrow the author can claim by revealing themselves. Needs your confirmation (Q2). |
| 2 | Merged ideas vs. attribution | The surviving idea gains the merged authors as co-authors. The merged idea stays visible as "Merged into X" with its own decision record. |
| 3 | Who grants innovation time | The panel recommends hours on acceptance; the leadership persona approves from a quarterly pool. Needs your confirmation (Q1). |
| 4 | Parked ideas become a second black hole | Parking requires a revisit date. The workflow agent resurfaces the idea on that date. |
| 5 | Accepted but no owner | An accepted idea without an owner appears in "needs attention" with its own clock. |
| 6 | Volume vs. quality in recognition | Points vest at outcomes, not at submission. Votes earn no points (section 6 of the product report). |
| 7 | AI assistance vs. human accountability | Agents propose. Only a person can record a decision, a score, an award or an announcement. |
| 8 | Ideathon ideas vs. year-round ideas | Ideathon entries are ordinary ideas tagged to a campaign. Shortlist and winner are overlays, not lifecycle states. |

---

## 2. Product requirements

### Personas

| Persona (demo user) | Role in app | Primary job |
|---|---|---|
| Priya — submitter | Employee | Get an idea heard, know where it stands, get credit. |
| Marcus — collaborator | Employee | Find ideas worth helping, contribute, be credited. |
| Elena — reviewer | Reviewer | Clear the queue with a trustworthy brief and record defensible decisions. |
| Tomas — team lead | Team lead | Take an accepted idea through prototype within a time budget and prove impact. |
| Dana — leadership | Leadership | See whether innovation produces outcomes; grant time; spot bottlenecks. |
| Sam — administrator | Admin | Configure categories, panels, timelines, scoring and recognition. |

The names are placeholders. Six named demo users across five roles, because collaboration cannot be shown with one employee.

### Scope by module

Depth is deliberate. The spine (submission through delivery, plus the points ledger) is deep. Profiles and Admin are thin views over the same state.

| Module | Depth | Must have | Should have | Not now |
|---|---|---|---|---|
| A Dashboard | Medium | Clickable stage counts, needs-attention, recent activity, active ideathons, impact totals, role-aware layout | Participation metrics, trend sparklines | Custom widgets |
| B Submission | Deep | Four-category template with validation, drafts, co-authors, anonymous toggle, link attachments, live similar-idea panel | Enhancement suggestions with apply/dismiss, suggested tags | Real file upload (metadata only) |
| C Discovery | Deep | Search, filters (category, team, status, tag), idea detail with lifecycle stepper and decision history, upvote, comment, follow, volunteer | Thread summary, related ideas | Threaded replies, @mentions |
| D Review | Deep | SLA-sorted queue, category panels, three-criteria scoring, decision form with mandatory reason, owner assignment, status propagation | Reviewer brief, consistency flag, "needs info" loop | Calibration analytics |
| E Delivery | Medium | Owner, innovation hours granted vs. used, task check-off, updates, mark implemented with impact entry, announcement, attribution | Stale-prototype nudges | Real task-tool integration |
| F Ideathons | Medium | Create campaign, challenge statements, link ideas, shortlist, pitch day with panel and audience votes, winner, hackathon handoff | Agent-drafted challenges, theme grouping, pitch timer | Live multi-user event mode |
| G Recognition | Medium-deep | Points ledger where every row cites its rule, badges, levels, leaderboards (individual, team, impact), Idea of the Quarter | Annual Award nominations, anti-gaming flags | Monetary rewards |
| H Profiles | Thin | Submitted, co-authored, implemented, points, badges, impact, contribution history | — | Org chart |
| I Admin | Thin | Categories, panels, scoring weights, timelines, point values, platform metrics, reset demo data | Ideathon management shortcuts | Permission matrix, SSO |

### Idea lifecycle

States: Draft, Submitted, Under review, Needs info, Accepted, Parked, Merged, Declined, Prototype, Implemented, Withdrawn.

| From → To | Who | Required |
|---|---|---|
| Draft → Submitted | Author | Template complete |
| Submitted → Under review | Routed to the category panel | Panel assigned; review clock starts |
| Under review ↔ Needs info | Reviewer asks, author answers | Question / response; clock pauses |
| Under review → Accepted | Reviewer (human only) | Scores, written reason, owner or "awaiting owner" |
| Under review → Parked | Reviewer | Reason, revisit date |
| Under review → Merged | Reviewer | Target idea, reason |
| Under review → Declined | Reviewer | Reason, "what would change our mind" |
| Parked → Under review | Reviewer, or agent proposal approved by reviewer | Revisit trigger |
| Accepted → Prototype | Owner, after leadership grants hours | Hours granted, tasks created |
| Prototype → Implemented | Owner | Outcome summary, impact entry with baseline, contributors |
| Draft/Submitted → Withdrawn | Author | Optional reason |

Every transition writes a timeline entry with who, when and why. The five brief stages remain the visible stepper; the extra states are how an idea sits within a stage. Default timelines (pickup 3 working days, decision 10, stale prototype 14) are **proposals** and will be admin-editable.

### Gaps in the brief and recommended additions

| # | Addition | Why it matters | Decision |
|---|---|---|---|
| 1 | Persona switcher | One browser must demonstrate six journeys | Accept |
| 2 | Notifications inbox | Delivers the reply guarantee | Accept |
| 3 | One activity log feeding timeline, feed, notifications and points | Keeps modules consistent | Accept |
| 4 | Agent approval cards and run log | Makes the agentic loop and the human gate visible | Accept |
| 5 | "Needs info" loop | Stops declines for missing detail | Accept |
| 6 | Parked revisit dates | Prevents a second black hole | Accept |
| 7 | Impact method (baseline, evidence, confidence) | Makes impact credible | Accept |
| 8 | Innovation time pool with balance | The brief's time grants need a ledger | Accept |
| 9 | Decline with "what would change our mind" | Turns rejection into learning | Accept |
| 10 | Guided demo tour | Reliable founder demo | Defer to the polish phase |

**Recommended not to build:** a side chatbot, real file upload, email or Slack notifications, SSO, streaks or login points, a leaderboard of idea counts, drag-and-drop stage changes, and any live Kompass call.

---

## 3. Information architecture and user journeys

The sitemap is organised around the idea lifecycle rather than the module list. The idea detail page is the single source of truth for an idea; Delivery is a tab on it, not a separate world.

| Route | Purpose |
|---|---|
| `#/home` | Role-aware dashboard |
| `#/explore` | Search and filter ideas |
| `#/ideas/:id` | Idea detail: stepper, tabs for Overview, Discussion, Decision history, Delivery, Activity |
| `#/submit`, `#/submit/drafts` | New idea, my drafts |
| `#/my` | My ideas: submitted, co-authored, following, volunteering |
| `#/review`, `#/review/:id` | Review queue and review workspace |
| `#/pipeline` | Status board with stage counts and stuck ideas |
| `#/ideathons`, `#/ideathons/:id` | Campaign list and detail (Submissions, Shortlist, Pitch day, Results, Handoff tabs) |
| `#/recognition` | Leaderboards, awards, how points work |
| `#/people/:id` | Profile |
| `#/insights` | Leadership analytics |
| `#/agents` | Agent activity log and Kompass integration map |
| `#/admin` | Configuration tabs and reset |

**Shell:** left sidebar plus topbar, matching the Kompass UI kit's shell. The topbar carries global search, notifications, theme toggle and the persona switcher with a persistent "Viewing as …" chip. Navigation, Home layout and action buttons change with the role. A route the current role cannot use shows a "switch persona to try this" panel rather than a dead end.

**Journeys (each demonstrable end to end)**

| Persona | Journey |
|---|---|
| Priya | Start an idea → similar-idea panel offers an existing idea to join → apply suggested metrics → add co-author → save draft → submit → see the stepper and review date → receive the decision with its reason → points appear on her profile. |
| Marcus | Filter Explore → read the thread summary → upvote, comment, follow → volunteer → credited as contributor at implementation. |
| Elena | Open queue sorted by time remaining → read the brief → score → record a decision (empty reason is blocked) → assign owner → status updates everywhere. |
| Tomas | Pick up an accepted idea → request hours → tick tasks, post updates → approve an agent-drafted nudge → mark implemented with impact → announcement published. |
| Dana | Leadership dashboard → read the bottleneck insight → drill into the stuck stage → approve hours → sponsor a challenge → confirm Idea of the Quarter. |
| Sam | Change a review timeline → adjust a scoring weight → edit a point value and see the ledger change → edit a panel → reset demo data. |

**Golden path for a demo (about 8 minutes):** leadership insight shows Process ideas stuck → Priya submits a Process idea → Marcus engages → Elena reviews and accepts with Tomas as owner → Tomas delivers and records hours saved → pitch day on a seeded ideathon with handoff → Recognition ledger and profiles update → Admin changes a point value.

---

## 4. Single-file HTML architecture

**Decision: plain JavaScript, no runtime dependencies.** A small `html` tagged-template helper escapes all interpolated text. One classic `<script>`, no imports.

Reasons: the file must work from `file://` with no network; nothing can fail to load; and the code stays as plain named functions that can be edited safely in stages. Runner-up: Preact with htm, to be reconsidered only if re-rendering proves painful. React with in-browser Babel and attribute-driven libraries were rejected.

**File layout, in fixed order:** design tokens → base and component styles → HTML shell → utilities → schema and seed data → store and actions → selectors → services (`api`, `AgentGateway`) → simulated agent engine → UI kit → router → one view section per module → event wiring → boot. Each section sits between unique banner comments so an edit targets a named block, never a line number.

**Rendering and events:** hash router; views are functions returning markup; each region re-renders itself; form inputs are kept out of the global render loop so typing never loses focus. Events use delegation on `data-action` attributes, with a boot-time audit that reports any control with no registered handler — this enforces the "no dead buttons" rule mechanically.

**Charts:** hand-built inline SVG (bars, funnel, donut, sparkline). No chart library.

**Estimated size:** 6,000–8,000 lines. This is an estimate, not a measurement.

---

## 5. Mock data and state management

- **One normalised store**, changed only through named actions (`submitIdea`, `recordDecision`, `logTime` …). Each action validates, then writes the status history, activity entry, notifications and points entries in one step.
- **Nothing derived is stored.** Dashboard counts, stage counts, points balances, levels and overdue flags are computed by selectors, so two screens cannot disagree.
- **Status history is the source of truth** for an idea's lifecycle; the **points ledger is append-only**, each row citing the rule that produced it.
- **Persistence:** one `localStorage` key with a schema version. A failed or unknown version offers a reset rather than crashing. If storage is unavailable the app runs in memory with a visible warning.
- **Seed data (proposed):** about 30 employees in 6 teams, 40–50 ideas across all states, around 120 comments and 300 votes, 8–10 delivery projects, 3 ideathons (past, live, upcoming), about 25 agent runs. The seed deliberately includes a review bottleneck, an anonymous idea, a merged pair and a declined idea.
- **Dates are stored as offsets from today**, so the demo never looks stale.
- **Backend readiness:** views never touch the store or the mock directly. They read through selectors and act through `api.*` and `AgentGateway.run()`, which return promises. Replacing the local adapter with REST or Kompass later does not touch the views.

Entities: employees, teams, categories, ideas, comments, votes, follows, volunteers, panels, reviews, decisions, status history, projects, tasks, updates, time grants and logs, ideathons, challenges, pitch entries and votes, awards, points ledger, badges, notifications, agent runs, admin config.

---

## 6. AI agent and Kompass workflow architecture

### Principles

1. AI lives inside the task the person is already doing. There is no global chatbot.
2. Agents propose; people decide. An agent may never record an accept/park/merge/decline decision, a score of record, an award, a de-anonymisation or an announcement in someone's name.
3. Only reversible, low-stakes actions apply without approval (suggested tags as chips, reminders drafted, points under published rules).
4. Every agent output is labelled **Simulated**, and each capability is classified as *Computed* (real calculation on the mock data), *Templated* or *Canned*. The run detail states that no language model was called.

### Roster

The seven agents in your instructions stay as the visible roster. Two adjustments:

- **Added:** a deterministic orchestrator (a rules engine, not an AI agent). It routes events, enforces approval gates and writes run records. It is also the seam where Kompass plugs in later.
- **Rejected:** Agent 4 recommended splitting Review Intelligence into a brief agent and an integrity agent. I folded the integrity check (score/decision consistency flag) into Review Intelligence to keep the roster you defined.

| Agent | Appears in | MVP simulation | Human gate |
|---|---|---|---|
| Idea Intelligence | Submit; idea detail | Computed: weighted term and tag overlap for similar ideas with "why matched" terms; category and tag suggestion; missing-field check | Author applies or dismisses |
| Idea Enhancement | Submit | Templated: problem-statement prompts, suggested metrics and beneficiaries by category | Author applies or dismisses |
| Review Intelligence | Review workspace | Computed + extractive: brief, thread summary built from real comment sentences, risk flags, suggested scores, consistency flag | Reviewer; the decision form starts empty |
| Innovation Workflow | Pipeline, Home, notifications | Computed: overdue and stale detection, parked revisit, drafted reminders | Reviewer or owner approves each nudge |
| Ideathon | Ideathon detail | Computed grouping and shortlist ranking; templated challenge, pitch summary and hackathon problem statement | Organiser approves shortlist and handoff |
| Recognition | Recognition, profiles | Computed: points under published rules, badge eligibility, award nominations, reciprocal-vote flag | Leadership confirms awards |
| Innovation Analytics | Insights, Home | Computed aggregates with templated narrative | None; read-only |

### Agent flows

Each follows trigger → retrieve context → analyse → delegate → recommend → human approval → execute → record → update, and renders as an expandable trace.

| Flow | Sequence | Approval |
|---|---|---|
| A. Idea drafted and submitted | Intelligence (similar, tags, gaps) → Enhancement (suggestions) → route to panel | Author |
| B. Review overdue | Workflow detects breach → Review Intelligence refreshes the brief → reminder drafted | Reviewer or panel lead |
| C. Decision recorded | Workflow notifies followers → Recognition proposes ledger entries → next action created | Human decision is the trigger |
| D. Ideathon closes | Ideathon groups entries → proposes shortlist → pitch summaries → problem statement for hackathon | Organiser, twice |
| E. Idea implemented | Workflow requests impact entry → Analytics updates → Recognition proposes points, badges, nomination | Owner; leadership for awards |

### Kompass: future integration, mapped only to documented concepts

The MVP makes **no live Kompass call**. The table shows where Kompass would fit, and what is still unknown.

| KonnektIdea need | Kompass concept | Documented? | Open question |
|---|---|---|---|
| Text-analysis agents (Intelligence, Enhancement, Review, Recognition, Analytics) | Smart Agents (system prompt, model, tools, guardrails, memory) | Yes | Can output be constrained to a schema? |
| Ideathon pipeline (group, brief, pitch) | Agentic Team (sequential / hierarchical) | Yes | How is a team invoked externally? |
| Multi-step flows A–E | Workflows using Input, Agent, LLM, Adapter, Conditional, API, Subflow, Guardrails, Output | Components yes | — |
| Starting a workflow from KonnektIdea | Input component (String or JSON) | Component yes; **external invocation not documented** | Endpoint, authentication, request and response format |
| Structured results | Agent → Adapter | Adapter needed for JSON: yes; validation: no | Does Adapter validate or only reshape? |
| Idea and decision corpus | AI Brain collections | Yes | Programmatic ingestion and deletion |
| Fetching live KonnektIdea data | API component with Vault secrets | Yes (outbound calls) | Network path to an KonnektIdea API |
| Protecting anonymous submissions | Guardrails (PII, prompt injection; custom) | Yes | Effectiveness for author-identifying text |
| Agent activity log | Traces | Yes | Readable by an external app? |
| Human approval | — | **Not found** | Any pause/approve primitive? |
| Scheduled checks and event triggers | — | **Not found** | Webhooks or schedulers? |

**Design consequence:** approval state, approver and audit trail are KonnektIdea records regardless of what Kompass offers. KonnektIdea fixes its own input envelope, output schemas and run record; the transport to Kompass is a replaceable engine behind `AgentGateway`.

**In the MVP UI:** `#/agents` shows the agent registry, every simulated run, and an integration map with "Simulated" and "Planned" chips and a permanent "Not connected to Kompass" notice. The 11 questions for the Kompass team are listed in `discovery/04_ai_kompass.md`, section 6.

---

## 7. Dotkonnekt UI/UX direction

| Aspect | Direction | Basis |
|---|---|---|
| Typeface | Geist for interface text, Geist Mono for numbers, IDs and agent traces, with a system fallback | Families verified; loading method to be confirmed |
| Colour roles | Purple for actions and navigation; gold reserved for recognition (earned things); neutrals carry the interface; status colours for lifecycle states | Families verified; **all values provisional** |
| Shell | Sidebar plus topbar | Matches the Kompass UI kit's components |
| Mode | Light by default (projected demos, dense tables); dark available through the theme toggle | Both modes exist in the design system |
| Surfaces | Cards, pills and tags, eyebrow labels with dividers | Component names verified |
| Gradients and glows | Restricted to agent surfaces and recognition moments | Families verified; restraint is my choice |
| Agent treatment | One consistent pattern: agent chip, "Simulated" pill, single accent border, footer line | New pattern for this product |
| Icons | A small hand-drawn inline SVG set | The official icon files could not be read |
| Responsive | Sidebar collapses to icons, then to a drawer; side panels stack on narrow screens | — |

All colour, spacing, radius, shadow and type values will live in **one CSS variable block** labelled provisional. When the real `tokens.css` is available, swapping it in is a change to that block alone. Until then I will not describe the result as the official Dotkonnekt design system.

Rejected: drag-and-drop on the pipeline board. It would allow a stage change with no written reason, which contradicts the product's central promise. Stages change only through actions on the idea.

---

## 8. Development roadmap

Each phase ends with the file runnable, the handler audit clean and the phase's QA gate passed.

| Phase | Scope | Gate |
|---|---|---|
| 0. Sign-off | Your review of this plan; design tokens supplied; open questions answered | Scope, architecture and design direction agreed |
| 1. Foundation | Shell, tokens, router, store, seed data, persistence, persona switcher, reset, basic Home | Loads from `file://` with no console errors; persistence and reset work |
| 2. Idea core | Explore, idea detail, submit with Intelligence and Enhancement agents, drafts, My ideas, notifications | Submit, vote, comment, follow, volunteer reflected everywhere |
| 3. Review and pipeline | Queue, review workspace, brief, decisions, needs-info loop, timelines, pipeline board, Workflow agent | Decision rules enforced; status propagates |
| 4. Delivery and impact | Owner, innovation time pool, tasks, updates, implemented with impact, announcements | Completion updates metrics and attribution |
| 5. Ideathons, recognition, profiles | Campaigns, shortlist, pitch day, handoff; ledger, badges, levels, leaderboards, awards; profiles | Voting rules hold; every points row cites a rule |
| 6. Leadership, admin, agent hub | Full dashboard, Insights, Admin configuration, agent log and Kompass map | Admin changes take effect across the app |
| 7. Hardening and delivery | Cross-module integration, full QA pass, responsive and accessibility checks, final documentation | Full checklist run with results recorded; no open critical defects |

**QA approach:** an acceptance checklist of about 70 concrete items (all currently "Not yet tested"), a cross-module consistency matrix, automated journeys in a headless browser loading the file from `file://`, a dead-control scan, four viewport sizes, and a text scan for anonymity leaks. Detail in `discovery/05_qa.md`.

**Risks**

| Risk | Mitigation |
|---|---|
| Design tokens stay unread | Provisional token block; you supply `tokens.css` |
| One very large file becomes fragile | Banner-delimited sections, handler audit, QA gate per phase |
| Simulated AI mistaken for real AI | One shared "Simulated" component; no way to switch labels off |
| Anonymity leaks through derived views | Leak scan in QA. Note that browser storage is readable on the device, so anonymity in the MVP is a display rule, not a security control |
| Kompass integration assumptions prove wrong | Nothing in the MVP depends on the unanswered questions |

---

## 9. Decision log

`IDEA_HUB_DECISION_LOG.md` is established with the discovery-phase decisions, the constraints, known limitations and unresolved questions. It will be updated by the documentation agent at each phase.

---

## 10. Project name

**Recommended: Project Polaris.** Kompass is the compass; Polaris is the star you steer by. The name says what the product is for: giving every idea a fixed point to navigate towards, and a visible answer. Alternatives: Lodestar, Kindle. I have not checked any of these against existing internal names or trademarks.

---

## Decisions needed from you

1. **Innovation time:** does a leadership budget-holder approve hours from a quarterly pool, as proposed?
2. **Anonymous ideas:** can anyone (reviewers, admins) see the author? Is escrow-and-reveal for credit acceptable?
3. **Timelines:** may I ship pickup 3 / decision 10 / stale 14 days as editable defaults?
4. **Impact verification:** self-reported, or confirmed by a second person?
5. **Audience:** internal staff only, or also customers seeing KonnektIdea as a Kompass reference? This sets how prominent the Kompass map is.
6. **Design tokens:** can you export `tokens.css` (or `colors_and_type.css`) and the logo SVG from the design system artifact into the repo?
7. **Name:** Project Polaris, or another?
