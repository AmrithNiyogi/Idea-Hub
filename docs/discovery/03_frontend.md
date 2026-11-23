# IdeaKonnekt — Frontend Architecture Proposal (Agent 3, Discovery)

Status: proposal only. No application code written. Library behaviours that I have not verified are marked "verify in current docs". Line counts and volumes are my own estimates, not measurements.

## 1. Framework decision

| Criterion | (a) Vanilla JS + template literals | (b) CDN reactive lib (Alpine / petite-vue / Vue 3 global / Preact+htm) | (c) React CDN + in-browser Babel |
|---|---|---|---|
| Works via file:// | Yes, nothing to load | Classic `<script src>` tags generally work from file://; verify per library | Same, but Babel-standalone is large and slow to start |
| CDN unreachable | Fully works | Blank app unless vendored inline | Blank app |
| Estimated payload | 0 KB deps | Roughly tens of KB (verify) | Several MB of Babel plus React (verify) |
| Editing by AI agents | Plain functions, easy to grep | Alpine/petite-vue push logic into HTML attributes, which is hard to edit safely at 6k+ lines | JSX transpiled at runtime; a syntax error blanks the page with poor diagnostics |
| Production evolution | Logic is separable (see section 6) | Rewrite of templates needed | Closest to a future React app, but the cost today is the highest |

**Recommendation: (a) vanilla JS with a small in-house `html` tagged-template helper, plus hand-rolled SVG charts. Zero runtime dependencies.**

Reasons:
1. The founder's hard requirement is "opens by double-click". A zero-dependency file has no failure mode when offline, on a locked-down corporate network, or when a CDN is blocked. Every other option adds a way for a demo to show a blank page.
2. The app is a set of mostly list/detail/form screens with modest per-screen interactivity. Coarse re-rendering from a single store (section 3) gives the benefits of a reactive library without the dependency.
3. Agents editing in stages benefit from ordinary functions: `renderIdeaDetail(state, id)` is easy to locate, replace and test. Attribute-embedded logic (`x-data`, `@click="..."`) spreads behaviour across markup.
4. The production path is not blocked: the store, services and selectors (sections 4 and 6) are framework-agnostic. Only the `views` layer would be rewritten in React/Vue later.

**Runner-up: Preact + htm**, vendored inline or via CDN with an inline fallback. It keeps a component model and diffing, which would help if we find focus/scroll loss in the coarse re-render approach. I am not certain of the current size, CDN URL layout or whether a no-build ESM/global build works from file:// without CORS problems; verify in current docs before adopting. Trigger for switching: if QA finds more than a handful of screens where the re-render approach breaks input state, switch only those screens, not the whole app.

Rejected: React with Babel (startup cost, size, fragility, offline failure). Alpine (logic-in-markup editability, runtime dependency).

Expected size: my estimate is 6,000-8,000 lines, roughly 400-600 KB. This is fine for a browser; the concern is editability, not performance.

One further caution on ES modules: inline `<script type="module">` is possible, but module imports of external files from file:// are commonly blocked by browsers. We will use a single classic `<script>` with an IIFE and no `import`.

## 2. Internal structure of the single file

Order of sections (each marked by a banner comment that is a unique, greppable string):

```
<head>  meta, CSP-free, <style> split into banners
  /* ==== CSS 01 TOKENS (provisional, pending tokens.css) ==== */
  /* ==== CSS 02 BASE/LAYOUT ==== */  03 COMPONENTS  04 MODULE STYLES  05 RESPONSIVE/PRINT
<body> app shell skeleton: #sidebar, #topbar, #view, #modal-root, #drawer-root, #toast-root
<script>
  // ==== JS 00 NAMESPACE & CONFIG ====      const IH = { version, flags }
  // ==== JS 01 UTILS ====                   esc, html``, dates, ids, rng(seeded), tokenise
  // ==== JS 02 SCHEMA & CONSTANTS ====      statuses, transitions, enums, DATE_FIELDS
  // ==== JS 03 SEED DATA ====               one function per entity: seedEmployees()...
  // ==== JS 04 STORE ====                   state, dispatch, subscribe, persistence, migrations
  // ==== JS 05 SELECTORS ====               pure derived data
  // ==== JS 06 SERVICES (ADAPTERS) ====     api.*, ai.*, clock
  // ==== JS 07 AGENT ENGINE ====            registry, runner, 7 agent definitions
  // ==== JS 08 UI KIT ====                  components: card, pill, table, avatar, chart-svg, modal, toast
  // ==== JS 09 ROUTER ====
  // ==== JS 10 VIEWS: <module> ====         one banner per module A-I
  // ==== JS 11 ACTIONS/HANDLERS ====        delegated data-action registry
  // ==== JS 12 BOOT ====
```

Conventions:
- **Banners**: `// ==== JS 10.4 VIEWS: REVIEW ====` and a matching `// ==== END JS 10.4 ====`. An agent edits by replacing between two unique banners; never by line number.
- **Module registration**: each module registers itself, so adding a module never touches shared code:
```js
registerModule({ id:'review', route:'/review', nav:{label:'Review', icon:'check'},
  roles:['reviewer','admin'], render: viewReview, routes:{ '/review/:id': viewReviewDetail } });
```
- **Naming**: `view*` (returns HTML string), `act*` (actions/mutations), `sel*` (selectors), `svc*` (services), `seed*`, `agent*`. CSS classes use a `ih-` prefix and BEM-lite (`ih-card__title`). IDs are prefixed by entity (`idea_`, `emp_`).
- **No cross-module imports of internals**: modules talk through selectors and `dispatch`.
- **Staged editing safety**: one module per edit; keep each view function under roughly 150 lines; a `selfCheck()` function run on boot (behind `?debug`) asserts invariants (every idea has a status history, every referenced id resolves, ledger sums equal profile points). Agents run it after each stage.
- **Header comment** at top of file: section index with banner names, so any agent can orient in one read.

## 3. Routing, rendering, events

**Routing.** Hash routes (`#/ideas/idea_42`), a route table built from the module registrations, with `:param` matching. `hashchange` triggers `renderRoute()`. Unknown routes show a 404 view with a link to the dashboard. Role gating is a soft check (persona switcher) that shows an "access denied in this persona" empty state; it is demo behaviour, not security. Query-style state (filters) is kept in the hash (`#/ideas?cat=tech&q=ci`) so back/forward and deep links work.

**Rendering.** Views are pure functions `(state, params) => htmlString`. The `html` tagged template auto-escapes interpolations and returns a marked safe string; `raw()` is the explicit opt-out. This matters because user text (comments, ideas) is injected into the DOM: every interpolated user value must be escaped by default.

Re-render strategy: the store notifies subscribers after each dispatch (batched with `queueMicrotask`/`requestAnimationFrame`). The shell has independent regions (`#sidebar` badges, `#topbar`, `#view`, `#toast-root`). Each region re-renders its own `innerHTML`. Before replacing `#view`, we capture scroll position and `document.activeElement` (id, selection range) and restore them after. For long forms (idea submission, review scoring) we do **not** re-render on keystroke: form fields hold their own DOM state, and only explicit actions (submit, save draft, add co-author) dispatch. The agent similarity panel updates its own sub-region directly on debounced input, not through the global render.

**Events.** One delegated listener per event type on `document` (`click`, `submit`, `input`, `change`, `keydown`). Elements carry `data-action="idea.upvote" data-id="idea_42"`; a handler registry maps action names to functions. Benefits: no re-binding after re-render, easy to grep every control, and a boot-time audit can scan the DOM for `data-action` values with no registered handler, which directly supports the "no dead buttons" acceptance criterion. Forms use `data-submit`.

**Modals, drawers, toasts.** Rendered into dedicated roots outside `#view`, so view re-renders do not destroy them. UI state (`ui.modal`, `ui.drawer`, `ui.toasts`) lives in a non-persisted `ui` slice. Modals trap focus, close on Esc and backdrop click, and restore focus to the opener. Confirmation modals with a mandatory text field (decline/park/merge reason) disable the confirm button until the reason is valid. Toasts auto-dismiss and support an "Undo" callback for reversible actions (vote, follow).

## 4. State management

**Store shape** (single object, normalised by id):
```js
state = { meta:{schema:3, seededAt, anchor, currentUserId, persona},
  entities:{ employees:{}, teams:{}, categories:{}, ideas:{}, comments:{}, ... },
  ui:{ /* not persisted */ } }
```
Entities are `{id: record}` maps; ordering is computed by selectors.

**Actions.** `dispatch('idea.decide', payload)` runs a named reducer-like mutation function that (a) validates (e.g. reason required, legal status transition per a transition table in section 02), (b) mutates a draft, (c) appends events (status history, points ledger, notifications, activity), then (d) notifies subscribers and schedules persistence. Cross-entity side effects happen inside the one action so state never half-updates. A rejected action returns `{ok:false, error}` and the UI shows it.

**Derived metrics are never stored.** Dashboard totals, stage counts, participation rate, points balance, badge eligibility, SLA breaches and "needs attention" are selectors over entities and events. Points balance = sum of ledger. Idea status = latest entry of status history (we store `status` as a denormalised convenience only if `selfCheck` verifies it matches; my recommendation is to derive it from history to avoid drift). Selectors are pure and memoisable by a state version counter.

**Persistence.** Serialise `entities` plus `meta` to `localStorage` under one key (e.g. `ideahub.v3`), debounced (about 300 ms) and on `beforeunload`. `meta.schema` is checked at boot: if lower, run an ordered migration chain `migrations[2→3]`; if a migration throws, or the data fails a basic shape check, offer "reset demo data" in a blocking dialog rather than crashing. A **Reset demo data** control (admin menu and error dialog) clears the key and reseeds. Also provide Export/Import JSON of state, which doubles as a backup and a backend-migration rehearsal.

**localStorage unavailable or full.** Wrap all access in try/catch. On failure the app runs in-memory, shows a persistent non-blocking banner ("Changes will not be saved on refresh"), and keeps working. On `QuotaExceededError`, strip regenerable data first (agent trace details, old notifications), retry once, then fall back to the banner. Attachments are mock metadata only (name, size, link), never file bytes, which keeps storage small. Estimated state size is well under 1 MB with the volumes below, against a commonly cited limit of roughly 5 MB per origin (verify; varies by browser). Note that file:// origins may share or isolate storage differently across browsers; QA should check refresh persistence on the actual browsers the founder uses.

## 5. Mock data model

All entities carry `id`, `createdAt`, `updatedAt` (ISO strings). Foreign keys are `xxxId`.

- **employees**: name, email, title, teamId, managerId, avatarColor, roles[] (employee, reviewer, lead, leader, admin), joinedAt
- **teams**: name, leadId, product/area tag
- **categories**: key (tech, business, process, innovation), label, panelId, slaDays, templateHints
- **ideas**: title, categoryId, problem, solution, beneficiaries, effortEstimate, successMetrics, tags[], authorId, anonymous (bool; authorId retained server-side-style but masked in views), coAuthorIds[], ideathonId?, attachments[{kind,label,url}], prototypeUrl, draft (bool), mergedIntoId?, ownerId?
- **statusHistory**: ideaId, from, to, actorId, at, reason. This is the lifecycle source of truth.
- **comments**: ideaId, authorId, body, parentId?, at
- **votes**: ideaId, employeeId, at (unique pair); **follows**, **volunteers** (ideaId, employeeId, note, at)
- **reviewPanels**: categoryId, memberIds[], chairId
- **reviews**: ideaId, reviewerId, impact, effort, alignment (1-5), comment, recommendation, at
- **decisions**: ideaId, outcome (accepted/parked/merged/declined), reason (required), deciderId, at, mergedIntoId?, ownerAssigned?
- **projects**: ideaId, ownerId, stage, budgetHours, startedAt, completedAt?; **tasks** (projectId, title, assigneeId, state, hours); **updates** (projectId, authorId, body, at); **impact** (projectId, hoursSavedPerMonth, revenueInfluenced, confidence, measuredAt)
- **timeGrants**: projectId, hours, grantedById, at; **timeLogs**: projectId, employeeId, hours, at
- **ideathons**: title, theme, startAt, endAt, pitchAt, stage (draft/open/shortlisting/pitch/closed), createdById; **challenges** (ideathonId, statement, sponsorId); **pitchEntries** (ideathonId, ideaId, order, summary, shortlisted); **pitchVotes** (entryId, voterId, kind panel|audience, score)
- **awards**: kind (quarter, annual, implementation, impact), period, ideaId?, employeeId?, teamId?, citation, grantedAt
- **pointsLedger** (event-sourced): employeeId, delta, ruleId, refType, refId, at, note. Rules live in admin config so the Recognition Agent's reasoning is transparent.
- **badges** (definitions) and **badgeAwards** (employeeId, badgeId, at, evidence refs)
- **notifications**: recipientId, kind, refType/refId, at, readAt
- **agentRuns**: agentId, trigger, simulated:true, status, steps[{label, detail, at, ms}], recommendation, approval{required, state, decidedBy, at}, outcome, refs
- **activity**: actorId (or agent), verb, refType/refId, at (feeds the dashboard feed)
- **config**: categories, scoring criteria and weights, SLA days, points rules, badge thresholds, feature flags

**Seed volumes** (my recommendation): ~30 employees across 6 teams; 4 categories; 40-50 ideas distributed across all five stages with a visible bottleneck (e.g. 4-5 ideas past SLA in review) and a few drafts; ~120 comments; ~300 votes; 8-10 projects with tasks/updates; 3 ideathons (one closed with winners, one open, one in pitch stage); ~15 awards and badge grants; ~400 ledger events; ~25 agent runs. This is large enough that filters, leaderboards and charts look real, small enough to author and persist easily. The seed must also include at least one idea in each decision outcome, one merge pair, one anonymous idea and one declined idea with a well-written reason.

**Relative dates.** Seeds declare times as offsets (`daysAgo(12)`, `hoursAgo(5)`, `inDays(3)`) resolved against the real clock at seed time, never as hardcoded calendar dates. To prevent staleness for a state saved weeks ago, `meta.anchor` records the seeding date and a `DATE_FIELDS` table (section 02) lists each entity's date fields; at boot, if the anchor is more than a few days old, all seed-origin timestamps are shifted by the difference and the anchor updated (user-created records are shifted identically, so relative ordering holds). Reset reseeds against today. Use a seeded PRNG so reseeds are deterministic.

## 6. Service/adapter layer and the simulated agent engine

**Rule: views never touch `state` mutation or `localStorage` directly. They call selectors for reads and `api.*` / `ai.*` for effects.**

```js
const api = {            // every method returns a Promise, as REST would
  ideas:   { list(q), get(id), create(d), vote(id), decide(id, d) /* ... */ },
  ...
};
const ai = {
  similarIdeas(draft), enhance(field, draft), reviewBrief(ideaId),
  threadSummary(ideaId), recommendDecision(ideaId), ...
};
```
Today `api` is implemented by `localAdapter` (store dispatch + simulated 80-300 ms latency) and `ai` by `simulatedAgentAdapter`. Later, `restAdapter` implements the same signatures, and `ai` can be pointed at a Kompass-backed adapter. Because everything returns Promises and structured results with `{ok, data, error}`, loading and error UI states exist from day one. I deliberately make no claim about how Kompass would be invoked: the context pack notes that invocation, auth, webhooks, structured output and approval nodes are undocumented, so the adapter boundary is the integration seam, and the contract (inputs, outputs, run record shape) is ours to define and later map.

**Agent engine (simulated).** Each of the seven agents is a definition: `{id, name, triggers[], retrieve(ctx), analyse(ctx), subtasks[], recommend(ctx), needsApproval, execute(approved)}`. The runner:
1. Receives a trigger (e.g. `idea.submitDraft`, `review.opened`, `idea.stuckInReview` from a timer or manual "run workflow check").
2. Creates an `agentRun` record with `simulated:true` and steps appended with simulated delays (staggered 300-900 ms), so the UI shows a live step-by-step trace (retrieve context, analyse, delegate to sub-agent, draft recommendation).
3. Uses deterministic heuristics, not random text: similar ideas via token overlap (lowercase, stopword removal, light stemming, Jaccard or TF-IDF cosine over title+problem+solution+tags) with a threshold and "why matched" terms; categorisation via keyword scoring per category; missing-info detection via field completeness rules; review briefs assembled from templates over real fields and scores; thread summaries via extractive sentence ranking; stuck-idea detection via SLA selectors; recognition via the transparent ledger rules. Output is templated prose populated from real data, so it is consistent and explainable.
4. Pauses at **approval gates**: recommendations render as cards with Approve / Edit / Reject. Nothing that changes workflow state (decision, owner assignment, award, reminder send) executes without a human click; the Review Intelligence Agent only recommends a decision, never records one.
5. On approval, calls the same `api` action a human would, records `outcome`, and writes activity/notification entries.

**Flagging.** Every agent surface carries a persistent "Simulated agent" chip and tooltip; every run record has `simulated:true` and `engine:'heuristic-v1'`; the run detail shows "No LLM was called". If a real adapter is later configured, the chip is driven by the adapter's `isSimulated` property, so it can never claim real execution while the mock is active. A global "Agent activity" drawer lists all runs.

## 7. Charts and visualisation

**Recommendation: hand-rolled SVG, no chart library.** Needs are limited: stage funnel/status board bars, participation line/area, category donut, impact bars, small sparklines, leaderboard bars. I would write about 6 small functions (`barChart`, `lineChart`, `donut`, `sparkline`, `hbar`, `funnel`) at roughly 250-350 lines total, using CSS variables for colour so they follow light/dark and the design tokens. Benefits: offline, themeable, accessible (`role="img"`, `<title>`, data table fallback), no CDN risk. Cost: more of our own code and no built-in animations/tooltips; we add a simple delegated tooltip. Runner-up: a CDN lib such as Chart.js (verify current CDN path and licence); adopt it only if a chart type beyond these proves necessary, and then with a graceful "chart unavailable" fallback.

## 8. Performance, responsiveness, risks

- **File size and navigability** (6-8k lines): mitigated by banners, registration pattern, per-module staged edits and the `selfCheck`. Risk that two agents edit overlapping sections: enforce one-module-per-stage ownership and a header section index.
- **Full-region re-render cost**: with 50 ideas, trivial. Mitigate with list virtualisation only if needed (unlikely), memoised selectors keyed by a state version, and not re-rendering on keystrokes.
- **Lost focus/scroll on re-render**: capture/restore as in section 3; keep forms out of the global render loop.
- **XSS from user-entered text**: autoescaping `html` helper; ban raw `innerHTML` with unescaped values; review by grep for `raw(`.
- **Silent JS error blanks the app**: top-level try/catch around boot and each view render, with a visible error panel offering Reset and "copy diagnostics". `window.onerror` logs to the activity panel in debug mode.
- **localStorage differences on file://**: test on target browsers; in-memory fallback and export/import as safety net.
- **Responsive**: sidebar collapses to a drawer below roughly 900 px; tables become card lists on small screens; CSS grid with `minmax`; touch targets at least 40 px. Dark/light via CSS variable swap; exact Dotkonnekt tokens remain "provisional approximation pending tokens.css". Geist fonts: unverified whether they can be embedded or loaded offline; plan a system-font fallback stack.
- **Accessibility**: semantic landmarks, focus management in modals, `aria-live` toast region, keyboard operable controls.
- **Evolution risk**: mock-only shortcuts leaking into views. Mitigated by the lint-like audit (no `localStorage`/`state` writes outside Store/Services).

## 9. Build sequence (always runnable)

Each slice ends with the file opening cleanly, `selfCheck` passing, and no dead controls.

1. **Skeleton**: shell (sidebar/topbar), tokens, router, UI kit basics, toast/modal, boot error handler, persona switcher, empty module stubs routed. Runnable with placeholders that say "coming in slice N" (not clickable dead buttons).
2. **Data core**: schema, seed generators with relative dates, store, persistence, migration, reset, export/import, selectors, `selfCheck`.
3. **Discovery (C) + idea detail**: list, search/filters, vote, follow, comment, volunteer, related ideas, status timeline. This proves the store-to-view loop.
4. **Submission (B)** with drafts, co-authors, anonymous, similarity check (first real agent heuristic) and the agent trace component.
5. **Review & decisions (D)**: queues, scoring, mandatory-reason decisions, owner assignment, SLA; Review Intelligence brief with approval gate.
6. **Delivery (E)**: projects, tasks, time grants/logs, updates, completion, impact.
7. **Dashboard (A)** over real selectors plus charts, now that data flows exist; Workflow Agent "stuck ideas" run.
8. **Ideathons (F)**: campaigns, submissions, shortlisting, pitch day voting, winners, hackathon handoff.
9. **Recognition (G) + Profiles (H)**: ledger rules, badges, levels, leaderboards, awards, history.
10. **Admin (I)**: config editors that actually alter selectors/rules (SLA, weights, points).
11. **Agent hub, analytics agent insights, notifications, polish**, responsive pass, accessibility pass.
12. **QA hardening**: dead-control audit, persistence/migration tests, cross-browser file:// check, final line-count and structure review for documentation.

Open points for the orchestrator: confirm persona-switcher approach (single demo user switching roles) versus fixed login; confirm whether Geist can be embedded (affects file size and offline typography).
