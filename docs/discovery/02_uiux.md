# IdeaKonnekt — UI/UX and Design System Analysis (Agent 2, Discovery)

Date: 2026-11-15. Analysis and design direction only. No application code. Verified facts and provisional assumptions are separated in section 6. Nothing here is an official Dotkonnekt value unless it is listed under "Verified".

## 1. Information architecture

Routes use hash routing (`#/...`). The product's core promise is a visible decision on every idea, so the sitemap is organised around the idea lifecycle, not around the module list.

| Route | Purpose | Key components |
|---|---|---|
| `#/home` | Role-aware dashboard | KPI strip, lifecycle funnel, needs-attention list, activity feed, Workflow Agent digest card |
| `#/explore` | Discover ideas | Search, filter bar (category, team, tag, status, product), idea cards, sort, "ideas I follow" toggle |
| `#/ideas/:id` | Single source of truth for one idea | Header, lifecycle stepper, tabs (Overview, Discussion, Decision history, Delivery, Activity), vote/follow/volunteer actions, similar ideas, agent brief |
| `#/submit` | New idea | Template form, category picker, anonymous toggle, co-authors, attachments, live similar-idea panel, Enhancement Agent chips, draft save |
| `#/submit/drafts` | My drafts | Draft list, resume or delete |
| `#/my` | My ideas | Tabs: Submitted, Co-authored, Following, Volunteering; each row shows status and next step |
| `#/review` | Reviewer queue | Panel selector, SLA-sorted queue, filters (overdue, unscored) |
| `#/review/:id` | Review workspace | Reviewer brief, scoring sliders, discussion summary, decision form (mandatory reason), owner assignment |
| `#/pipeline` | Status board (stage counts and stuck ideas) | Five-column board, SLA and stale badges, bottleneck callout |
| `#/delivery/:id` | Implementation view of one idea | Owner, innovation-time meter, simulated task list, update log, impact capture, "mark implemented" |
| `#/ideathons` | Campaign list | Active, upcoming, past; create button |
| `#/ideathons/:id` | Campaign detail | Phase stepper, challenge statement, linked submissions, shortlist, Pitch Day tab, results, hackathon handoff |
| `#/ideathons/:id/pitch` | Pitch-day live mode | Pitch order, timer, panel scoring, audience vote, live tally |
| `#/recognition` | Recognition hub | Leaderboards (individual, team, impact), Idea of the Quarter, Annual Award, rules explainer, badge catalogue |
| `#/people/:id` | Profile | Level, points ledger, badges, contribution history, impact generated |
| `#/insights` | Leadership analytics | Participation, implementation rate, bottlenecks, themes, Analytics Agent narrative |
| `#/admin` | Admin (tabs below) | Categories, Panels, Scoring criteria, Timelines, Recognition rules, Ideathons, Platform metrics, Data (reset) |
| `#/agents` | Agent Activity Log | All simulated runs with trigger, steps, outcome, approvals; also explains the Kompass mapping |

Restructuring recommendations are in section 8. In short: Delivery is a mode of the idea detail rather than a separate world, and Pipeline is the entry point to Delivery.

## 2. Navigation model

**Shell.** Copy the verified Kompass pattern: left Sidebar plus Topbar. Primary nav lives in the sidebar. The sidebar collapses to icons at medium widths and becomes a drawer on mobile.

**Primary nav (sidebar), by role:**

| Item | Employee | Reviewer | Team lead | Leadership | Admin |
|---|---|---|---|---|---|
| Home | yes | yes | yes | yes | yes |
| Explore | yes | yes | yes | yes | yes |
| Submit (primary button, pinned) | yes | yes | yes | no | no |
| My ideas | yes | yes | yes | no | no |
| Review | no | yes | no | no | yes |
| Pipeline | read-only | yes | yes (owns Delivery) | yes | yes |
| Ideathons | yes | yes | yes | yes | yes |
| Recognition | yes | yes | yes | yes | yes |
| Insights | no | no | no | yes | yes |
| Admin | no | no | no | no | yes |
| Agent Log | no | yes | yes | yes | yes |

Role changes the nav, the Home layout, and which action buttons render on an idea. A route the role cannot see shows a friendly "this view is for reviewers, switch persona to try it" panel, so a shared link does not dead-end during demos.

**Secondary nav.** Tabs inside a page (idea detail, admin, recognition). Breadcrumbs on idea, review and ideathon detail pages.

**Global topbar (left to right):** breadcrumb or page title; global search (opens a command-palette style overlay searching ideas, people, ideathons; keyboard `/`); notifications bell (simulated Workflow Agent reminders, decisions on followed ideas, approvals waiting); theme toggle; persona switcher (avatar plus role label).

**Persona switcher.** One demo user per persona, mapped to a fixed named mock employee, so the story is coherent (for example, the employee persona owns the ideas shown in "My ideas"). Dropdown lists five personas with a one-line description of what that persona can do. A persistent coloured "Demo mode: viewing as Reviewer" chip sits in the topbar so presenters never lose track. Switching preserves the current route if it is permitted, otherwise it goes to Home. A guided "Demo tour" menu item could jump to a scripted journey per persona (recommended, not required for MVP).

**Reset demo data** belongs in `#/admin` > Data and also in the persona menu footer, with a confirm dialog. It should not be a prominent topbar button, to avoid accidental clicks.

## 3. How AI appears inside workflows

Principle: every AI surface is attached to a decision or a task the user is already doing, and is produced by a named agent with a visible trigger. There is no global chat panel. (The Kompass kit has a ChatPanel, which is verified; we deliberately do not reuse it as the main AI entry point. A scoped "Ask this agent about this idea" input inside an agent card is acceptable.)

**Patterns:**

1. **Inline suggestion chips** (Submit). Idea Intelligence suggests category and tags; Enhancement suggests missing metrics and beneficiaries. Click to apply, click x to dismiss; applied chips are logged.
2. **Live similar-ideas panel** (Submit, right column). Updates as the title and problem field change (debounced, with a short "agent is thinking" state). Each match offers "Join as co-author", "Follow", "Open", or "Mine is different" (dismissal reason is recorded).
3. **Agent brief card** (Idea detail and Review). A compact card at the top of the reviewer's workspace: summary, risks and dependencies, discussion summary, suggested scores with rationale, recommended decision. The recommendation is visually separate from the human decision form, and the form starts empty.
4. **Approval card** (anywhere an agent proposes an action: send reminder, nominate for award, create hackathon problem statement, reassign stale idea). Shows proposed action, evidence, "Approve", "Edit", "Reject". The outcome is written to the idea's activity timeline and the Agent Log.
5. **Agent activity timeline** (Idea detail > Activity; `#/agents`). A vertical stepper mirroring the agentic loop: Trigger, Context retrieved, Analysis, Subtasks delegated, Recommendation, Approval, Execution, Outcome recorded. Each step is expandable to show what the mock agent "saw".
6. **Nudge banners** (Pipeline, Home). Innovation Workflow Agent flags stuck ideas with a one-click approval to send a follow-up.
7. **Narrative strip** (Insights, Dashboard). Analytics Agent writes two or three sentences of leadership insight, each linked to the chart it refers to.
8. **Explain-this-score affordance** (Recognition). Recognition Agent lists the transparent rule that produced each point award; this doubles as the anti-gaming message.

**Consistent "simulated agent" treatment.** Every agent-produced block carries the same three elements:
- An agent chip: small icon, agent name (for example "Review Intelligence"), and the word **Simulated** in a distinct pill.
- A left accent border in the agent colour treatment (one accent for all agents, not seven colours).
- A footer line: "Simulated output from mock data. In production this would run as a Kompass workflow." Expandable "How this would work" opens the trigger, inputs and outputs. That text must not name unverified Kompass endpoints or approval nodes; it should say "integration approach to be confirmed".

A global Admin toggle, "Show simulation labels", should not exist; labels are always on.

## 4. Key screen blueprints

**Dashboard (`#/home`, employee variant; other roles swap the middle band)**
```
[Eyebrow: GOOD MORNING]  Welcome back, Priya            [Submit an idea]
[KPI] Total ideas | Awaiting review | Accepted | In delivery | Implemented | Active ideathons
[Lifecycle funnel: Submitted > Review > Decision > Prototype > Implemented, with counts]
+-----------------------------+  +--------------------------------+
| Needs your attention        |  | Agent digest (Simulated)       |
| - Your idea "X" decided     |  | Workflow Agent: 3 ideas stale  |
| - Review overdue (rev.)     |  | [Approve nudges]               |
| - Volunteer request         |  +--------------------------------+
+-----------------------------+  | Engagement + impact tiles      |
| Recent activity feed        |  | (hours saved, revenue infl.)   |
+-----------------------------+  +--------------------------------+
```
Reviewer variant puts "My queue and SLA" first. Leadership variant puts impact and bottlenecks first. Team lead variant puts "My delivery items and time budget" first.

**Submit idea (`#/submit`)**
```
Eyebrow: NEW IDEA        [Save draft]  [Submit]
+--------------------------------------+  +---------------------------+
| Category cards (4)                   |  | Similar ideas (Simulated) |
| Title                                |  |  Match 1  82%  [Join]     |
| Problem  (chips: add metric?)        |  |  Match 2  64%  [Follow]   |
| Proposed solution                    |  |  Match 3  51%  [Open]     |
| Who benefits  | Rough effort (S/M/L) |  |---------------------------|
| What success looks like              |  | Completeness checklist    |
| Co-authors (people picker)           |  | Suggested tags (chips)    |
| Attachments / prototype links        |  | Estimated impact range    |
| [ ] Submit anonymously (explainer)   |  +---------------------------+
+--------------------------------------+
```
The similar-ideas panel is sticky on desktop and collapses into an expandable bar above the form on mobile. On submit, the user lands on the new idea's detail page with the stepper at "Submitted" and a stated review SLA ("A Tech panel reviewer will pick this up within N days"; N comes from Admin timelines).

**Idea detail (`#/ideas/:id`)**
```
Breadcrumb  Explore > Tech > Idea title
[Category pill][Status pill]  Title            [Upvote 42] [Follow] [I want to help]
Author, co-authors, owner, tags
LIFECYCLE STEPPER: Submitted - Under review - Decision - Prototype - Implemented
  (each step: date, actor; current step highlighted; next action text)
Tabs: Overview | Discussion | Decision history | Delivery | Activity
Overview: problem, solution, beneficiaries, effort, success metrics, attachments
Right rail: Agent brief (Simulated), Similar/related ideas, Volunteers
Decision history: timeline of each decision with decider, date, scores, written reason
```
Every state of the idea shows "What happens next, and who owns it" as one sentence under the stepper. That sentence is the visible-decision promise.

**Review workspace (`#/review/:id`)**
```
Left (60%): idea content, discussion with Review Intelligence summary on top
Right (40%, sticky):
  Agent brief (Simulated): summary | risks | suggested scores | recommendation
  Scoring: Impact [1-5] Effort [1-5] Alignment [1-5]  (category-specific criteria)
  Reviewer comment
  Decision: ( ) Accept ( ) Park ( ) Merge into [picker] ( ) Decline
  Reason (required, min length, inline error)
  Owner assignment (required if Accept)
  [Record decision]
```
Queue (`#/review`) is a table sorted by SLA remaining, with overdue rows flagged.

**Pipeline status board (`#/pipeline`)**
```
Stage counts bar: Submitted 14 | Under review 9 | Decided 6 | Prototype 5 | Implemented 11
Five columns of idea cards; each card: title, category dot, owner, days in stage
Stuck badges (over SLA or stale); filter: category, team, "stuck only"
Bottleneck callout (Workflow Agent, Simulated): "Process panel is 6 days over SLA" [Send reminder]
```
Drag-and-drop is optional and risky (see section 8). Recommended: the board is read-mostly, and moves happen through the actions on the idea (decision, "start prototype", "mark implemented"), so stage changes always carry a reason and audit trail.

**Ideathon detail (`#/ideathons/:id`)**
```
Eyebrow: IDEATHON  Title + dates + phase stepper (Open - Shortlist - Pitch day - Results - Handoff)
Challenge statement card (sponsor, goal)
Tabs: Submissions | Shortlist | Pitch day | Results | Handoff
Submissions: linked ideas, "Submit to this ideathon" button, Ideathon Agent groups by theme
Shortlist: Agent proposed shortlist (approval card), human confirms
Pitch day: order list, 5:00 timer per pitch, panel score entry, audience vote button
  (one vote per persona, enforced), live tally bars, "Close voting"
Results: winner banner, points awarded (links to Recognition)
Handoff: generated problem statement (Simulated) -> "Send to hackathon backlog"
```

**Recognition (`#/recognition`)**
```
Tabs: Leaderboard | Teams | Impact | Awards | How points work
Leaderboard filters: period, scope. Row: rank, person, level, points, breakdown mini-bar
  (Quality / Collaboration / Delivery / Impact)  -> click opens profile
Idea of the Quarter card; Annual Award nominations (approval card from Recognition Agent)
"How points work": transparent rule table with weights
```
Default sort should be composite recognition score, not idea count, and the breakdown bar makes the "quality over volume" principle visible.

**Profile (`#/people/:id`)**
```
Header: avatar, name, team, level badge, total points, "next level in N points"
Stat tiles: Ideas submitted | Co-authored | Implemented | Hours saved | Revenue influenced
Tabs: Contributions | Badges | Points ledger | Recognition
Contributions: timeline across roles (author, co-author, volunteer, reviewer, owner)
Points ledger: each row cites the rule applied
```

## 5. Component inventory (lean)

1. App shell: Sidebar, Topbar, page container.
2. Persona switcher and role chip.
3. Button (primary, secondary, ghost, danger), icon button.
4. Pill and tag (category, status, agent "Simulated", badge level).
5. Card (default, interactive, agent card variant).
6. Eyebrow label plus divider.
7. KPI tile with optional delta and sparkline.
8. Lifecycle stepper (horizontal; vertical variant for activity timeline).
9. Data table (sortable, row actions).
10. Form controls: input, textarea, select, radio cards, toggle, slider, people picker, tag input.
11. Filter bar and search overlay.
12. Tabs.
13. Modal and drawer, confirm dialog.
14. Toast.
15. Agent card, approval card, agent timeline.
16. Board column and idea card.
17. Avatar and avatar stack.
18. Progress bar and time-budget meter.
19. Chart primitives: bar, horizontal bar, funnel, sparkline, line (all inline SVG).
20. Empty state and inline validation message.

Twenty items is the ceiling; resist adding more.

## 6. Dotkonnekt visual direction

### Verified (from the design system file inventory only)
- Fonts: Geist and Geist Mono (variable weight).
- Colour families: purple, gold, neutrals, semantic, status, gradients; also glows.
- Light and dark modes both exist.
- Token groups: radii, shadows, spacing, motion, type scale (display, h1-h2, body, eyebrow, mono).
- Component previews: buttons, cards, inputs, tags/pills, eyebrow plus divider.
- Kompass UI kit: Sidebar, Topbar, AgentList, ChatPanel, KompassIcons.
- Icon sets exist: core brand, Kompass features, industry use-cases. Logo exists in light and dark variants.

### Provisional approximation pending tokens.css
None of the following is official. All must be replaced by values from `tokens.css` / `tokens.json` once they can be read. Implementation should centralise them as CSS custom properties so replacement is a single edit.

| Token (our name) | Provisional value | Note |
|---|---|---|
| `--brand-primary` | a mid purple, around `#6D4AFF` | Hue family verified, exact value unknown |
| `--brand-accent` | a warm gold, around `#E0A526` | Same |
| `--neutral-0 / 50 / 900 / 950` | white, cool light grey, deep grey, near-black | Same |
| `--success / warning / danger / info` | conventional green, amber, red, blue | Semantic family verified, values unknown |
| `--radius-sm / md / lg` | 6 / 10 / 16 px | Guess |
| `--space-1..8` | 4px base scale | Guess |
| Type scale | eyebrow 11px uppercase with tracking; body 14px; h2 20px; h1 28px; display 40px | Guess |
| Shadow | single soft elevation plus one overlay elevation | Guess |

### Application of the system
- **Purple is the action colour**: primary buttons, active nav, focus rings, links, selected states. **Gold is the recognition colour**: points, badges, awards, "Idea of the Quarter", and nothing else. That separation helps users read gold as "earned", which strengthens Recognition.
- **Neutrals carry the interface.** Most of any screen should be neutral surfaces and text, with purple appearing only where something is actionable.
- **Agents get one treatment**: purple-tinted surface (low-opacity purple, not a gradient), the Simulated pill, and a subtle glow reserved for the agent "thinking" state only. Using a single glow location keeps it meaningful.
- **Gradients**: at most one, on the Home hero strip or the level badge. Not on cards, buttons or charts.
- **Geist for UI, Geist Mono for numbers that need alignment** (KPI values, points ledger, scores, IDs, timers) and for the Simulated pill text. Eyebrow labels (small uppercase) head each page section and card group, consistent with the verified eyebrow plus divider component.
- **Pills** express category (neutral with colour dot), status (status family), and level (gold). Keep pill shapes identical so only colour carries meaning, and always pair colour with text.
- **Cards**: flat with hairline border in light mode; slightly lifted surface in dark mode.

**Light vs dark default: light.** Reasons: the founder asks for premium, enterprise-ready and intuitive, and demos are usually projected or screen-shared, where light mode is more legible. Light mode also suits dense tables and the board. Dark mode ships as a toggle (verified to exist in the system) and persists in localStorage. Risk: our dark palette is provisional too, so it should be visually QA'd, and it is the first thing to cut if time runs short. The dark toggle is a differentiator but not a requirement.

**Data visualisation without heavy dependencies.** Hand-built inline SVG and CSS bars, generated by tiny helper functions: bar, stacked bar, funnel, sparkline, simple line. No charting library. Rationale: file stays standalone, the datasets are small, and we control colours via tokens. Use categorical colour sparingly: the primary purple for the main series, neutrals for comparison, gold only for recognition metrics. Every chart gets a text equivalent (table or caption).

**Iconography.** We cannot read the brand icon files, so we must not imitate them. Use a small hand-authored inline SVG icon set (about 30 simple stroke icons, consistent 1.5px stroke, `currentColor`), defined once as an SVG sprite and referenced by id. State in the decision log that these are placeholders to be swapped for the Kompass or core brand icons once readable. Logo: use a text wordmark placeholder "dotkonnekt" in Geist, labelled as a placeholder, not a reconstruction of the real logo.

**Font loading caveat.** Geist must load via an external font source or be absent when opened offline from `file://`. Specify a system-font fallback stack, and treat exact rendering as an open issue. I do not have a verified CDN URL; confirm one before implementation.

## 7. Responsive behaviour and accessibility

**Breakpoints (provisional):** desktop 1200+ (full sidebar, two-column layouts), tablet 768-1199 (icon sidebar, single main column with right rail dropping below), mobile below 768 (drawer nav, stacked cards; board columns become a horizontal scroll or a stage selector; tables become card lists).

**Accessibility basics:**
- Contrast at WCAG AA for text and controls in both themes; verify once real tokens are known, since our palette is an approximation.
- Full keyboard operation: visible focus ring (purple), logical tab order, `Esc` closes overlays, focus trap in modals, `/` focuses search.
- Semantic landmarks (nav, main, header), headings in order, labelled form controls, `aria-live` for toasts and agent "thinking" results.
- Never use colour alone: statuses have text, charts have captions, votes show counts.
- Stepper uses `aria-current="step"`.
- Respect `prefers-reduced-motion` (disables glow and transitions); respect `prefers-color-scheme` only for first-run default if we choose to, otherwise default light.
- Minimum 44px touch targets on mobile.

## 8. UX risks and recommendations

1. **Disconnected screens (biggest risk).** Recommended merges and restructures:
   - Merge Delivery into the idea detail as a tab, with `#/delivery/:id` as a deep link to it. Pipeline is the index for it.
   - Treat "Decision" as a visible stage with its own history tab, not as a hidden review-side artefact. Employees see decisions and reasons without entering Review.
   - Merge Insights into Home for leadership (Home variant) plus a deeper `#/insights` page, rather than a distinct "analytics module".
   - Make Profile the home of "contribution history"; Recognition links to it instead of duplicating it.
   - Ideathon submissions are ordinary ideas with a campaign tag, so they appear in Explore and Pipeline too. This keeps them from becoming a parallel system.
2. **Persona overload for demos.** Five personas can confuse viewers. Mitigate with the role chip, a "what can this persona do" description, and an optional scripted tour.
3. **Simulated AI mistaken for real AI.** Mitigate with the always-on Simulated pill and footer. Do not use language such as "AI analysed your data" without the label.
4. **AI feels like decoration.** Each agent surface must change something: apply a tag, link a co-author, pre-fill a decision reason draft, send a nudge. Agent output that cannot be acted on should be cut.
5. **Agent recommendation biasing reviewers.** Keep the human decision form empty by default and show recommendation separately; log whether the reviewer agreed or overrode.
6. **Anonymous submission.** Specify clearly who can see the author (nobody in the UI; admin visibility is an open policy question for the founder). Anonymous ideas must still be credited if implemented, so define how credit works (for example a private claim step). Flag for founder input.
7. **Gaming recognition.** Points shown with their rules and a quality/collaboration/impact breakdown; avoid a raw "most ideas" leaderboard as the default.
8. **Drag-and-drop on the board** looks impressive but permits status changes with no reason, contradicting the core promise. Keep moves action-driven.
9. **Over-building.** There are about 19 routes. For build order, I recommend priority: Idea detail, Submit, Explore, Review, Pipeline, Home, then Ideathons, Recognition, Profile, Admin, Insights, Agent Log. The last four can be thinner if needed, but must still be functional rather than decorative.
10. **Design-token uncertainty.** Everything visual must reference CSS custom properties so real tokens can be dropped in. Record in the decision log that the current look is an approximation, and request that someone with access paste `tokens.css`, which is the single most valuable unblock for design fidelity.
11. **Open questions for the founder:** is anonymous author visible to admins; does the Annual Award need a nomination and voting flow in the MVP; who owns the innovation-time grant (leadership persona or admin).

*Limitations of this analysis: no tokens, icons or logo were read; all numeric design values and the CDN font approach are provisional or unverified; no Kompass integration detail is asserted beyond what CONTEXT.md lists as verified.*
