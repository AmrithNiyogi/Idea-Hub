# IdeaKonnekt — Product Strategy and Requirements Analysis (Agent 1, Discovery)

Source of truth: CONTEXT.md only. All numbers below are PROPOSALS, not facts. No Kompass or Dotkonnekt facts are assumed beyond CONTEXT.md.

## 1. Requirements analysis

**Core insight.** The product is not an idea box; it is a *reply guarantee*. People stop submitting when ideas vanish. Every design choice should be tested against: "can the submitter see, right now, where their idea is, who owns the next move, and why a decision was made?" Ideathons, rewards and AI are amplifiers of that loop, not substitutes for it.

**Explicit:** four categories; template submission; drafts, co-authors, anonymous option, attachments; similar-idea check while typing; upvote/comment/volunteer/follow; thread summaries for reviewers; 5-stage flow; per-category panels; impact/effort/alignment scoring; mandatory written decision reasons; innovation time granted by leadership and tracked; stage-count board; ideathons with pitch day and dual voting; credit stays with author; impact tracking; quarterly and annual awards.

**Implied (not stated, but required for it to work):** a review SLA clock and escalation; a named owner on every decision; notifications/inbox (follow is meaningless without it); a way for submitters to respond to a decision (appeal/revise); idea edit history; roles and permissions; a baseline for "impact" (hours saved needs a before number).

**Tensions and ambiguities, with recommended resolutions**

| # | Tension | Recommendation |
|---|---|---|
| 1 | Anonymous submission vs. credit and points | Anonymous to *everyone except a sealed author record*. Author can later "reveal" to claim credit and points; until then, points accrue to a private escrow shown only to the author. Reviewers and admins never see identity. |
| 2 | Merge vs. attribution | Merge creates a surviving idea; all merged authors become co-authors with full credit; merged ideas stay visible as "Merged into X" with their own decision history (never deleted). |
| 3 | Who grants innovation time? | Brief says "leadership". Proposal: the accepting panel *recommends* hours; a leadership budget-holder *approves*; portal shows a per-quarter pool and remaining balance. Decision is split to keep panels from over-committing. |
| 4 | Parked ideas | Parked must carry a *revisit date or revisit trigger* (e.g. "after Q1 roadmap"). Workflow agent resurfaces them. Otherwise "parked" becomes the new black hole. |
| 5 | "Accepted" vs. "Prototype" | Accepted with no owner is a hidden stall. Proposal: Accepted requires an owner or auto-enters "Awaiting owner" with its own SLA. |
| 6 | Volume vs. quality | The brief rewards credit; module G demands non-volume rewards. Resolved in section 7. |
| 7 | Declined ideas | Declined must say why and offer "what would change our mind". Allow one resubmission linked to the original. |
| 8 | AI recommends, humans decide | Reviewer agent may never write a decision; the UI must make the human approval gate unmistakable. |
| 9 | Ideathon ideas vs. year-round ideas | Ideathon entries are ordinary ideas tagged with a campaign, so they inherit the lifecycle; shortlist and winner are *overlays*, not states. |

## 2. Personas

| Persona | Primary jobs-to-be-done |
|---|---|
| Priya, Submitter | Get an idea heard without it being duplicated or ignored; know where it stands; get credit. |
| Marcus, Collaborator | Find ideas worth helping with; contribute time or comments; be credited for it. |
| Elena, Reviewer (panel member) | Clear a queue fast with a trustworthy brief; score consistently; record defensible decisions. |
| Tomas, Team lead (implementation) | Take an accepted idea to delivery inside a small time budget; report progress; prove impact. |
| Dana, Leadership | See whether innovation is producing business outcomes; grant time; spot bottlenecks; sponsor challenges. |
| Sam, Administrator | Configure categories, panels, SLAs, scoring and recognition without code; keep the platform healthy. |

## 3. Feature priorities per module (MVP demo)

Legend: M Must, S Should, C Could, W Won't-now. "Thin" = convincing surface, shallow logic; "Deep" = real state changes and cross-module effects.

| Module | Depth | Must | Should | Could | Won't-now |
|---|---|---|---|---|---|
| A Dashboard | Medium | Stage counts (clickable to filtered list), needs-attention list, recent activity, active ideathons, impact totals | Role-aware view (leadership vs. employee), participation metric | Trend sparkline | Custom widgets |
| B Submission | **Deep** | 4-category template with all fields, validation, save draft, submit creates idea, similar-idea panel (simulated), anonymous toggle | Co-author picker, link attachments, enhancement-agent suggestions with accept/reject per suggestion | Auto-tag chips | Real file upload (use name + link only) |
| C Discovery | **Deep** | Search, category/team/status/tag filters, detail page with lifecycle timeline, upvote, comment, follow, volunteer | Thread summary (simulated), related ideas | Sort by "most discussed" | Threaded replies, @mentions |
| D Review | **Deep** | Queue with SLA badges, scoring (3 criteria), decision form with mandatory reason, owner assignment, status propagation | Reviewer brief (simulated), category panels, decision recommendation (human confirm) | Conflict-of-interest recusal | Calibration analytics |
| E Delivery | Medium | Owner, hours allocated vs. used, task list with check-off (simulated task system), update posts, mark implemented with impact entry | Completion announcement in feed | Gantt-like view | Real task-tool integration |
| F Ideathons | Medium | Create campaign, challenge statements, link ideas, shortlist, pitch-day vote (panel + audience), winner, handoff as problem statement | Agent-drafted challenge statements, grouping of related entries | Pitch timer | Live-event mode, real scheduling |
| G Recognition | Medium-deep | Transparent points ledger, badges, levels, leaderboard, Idea of the Quarter | Team recognition, Annual Award shortlist, "why did I get these points" explainer | Peer thanks | Monetary rewards |
| H Profiles | Thin | Ideas, co-authored, implemented, points, badges, impact | Contribution history timeline | Skills tags | Org chart |
| I Admin | **Thin** | Edit categories, SLA days, scoring weights, point values; reset demo data; platform metrics | Panel membership editing | Audit log | Permission matrix, SSO |

**Critical view.** Nine modules in one file is feasible only if the *spine* (A to E plus ledger) is deep and the rest is thin but connected. Admin and Profiles should be mostly read-views over the same state. Ideathons and Recognition should reuse the idea store rather than own parallel data. Persona switching (a header "view as" control) is a Must: without it one browser cannot show six journeys.

## 4. Lifecycle state machine (proposal)

States: **Draft, Submitted, Under Review, Needs Info, Accepted, Parked, Merged, Declined, Prototype, Implemented, Withdrawn** (Awaiting-owner is a sub-state of Accepted).

| From | To | Who | Required data | SLA behaviour |
|---|---|---|---|---|
| Draft | Submitted | Author | Template fields complete | Starts triage clock |
| Submitted | Under Review | System/Workflow agent (auto-route by category) | Panel assigned | Panel pickup due in 3 working days (proposed; admin-configurable) |
| Under Review | Needs Info | Reviewer | Question to author | Review clock paused; author has 10 days (proposed) or idea auto-parks |
| Needs Info | Under Review | Author | Response | Clock resumes |
| Under Review | Accepted | Panel (human) | Scores, written reason, owner or "awaiting owner" | Decision due 10 working days from pickup (proposed); breach escalates to panel lead then admin |
| Under Review | Parked | Panel | Reason, revisit date/trigger | Resurfaced at revisit date |
| Under Review | Merged | Panel | Target idea, reason; authors become co-authors | None |
| Under Review | Declined | Panel | Reason, "what would change our mind" | One linked resubmission allowed |
| Parked | Under Review | Workflow agent/panel | Trigger met | Fresh review clock |
| Accepted | Prototype | Owner (with leadership time approval) | Hours approved, task created | Owner assignment due in 5 days |
| Prototype | Implemented | Owner | Outcome summary, impact entry (hours saved/revenue influenced, with method), contributors list | Stale if no update in 14 days (proposed) |
| Prototype | Parked/Declined | Owner/panel | Reason | None |
| Draft/Submitted | Withdrawn | Author | Optional reason | None |

Rules: every transition writes a timeline entry (who, when, reason). Reasons mandatory on Needs Info, Accepted, Parked, Merged, Declined. Only humans trigger Accepted/Parked/Merged/Declined; agents may only propose. Anonymous authors can transition via a sealed channel.

## 5. User journeys

**Priya (Submitter).** 1 Open Submit, pick category. 2 Type problem; simulated Intelligence agent flags two similar ideas. 3 Choose "join" on one or continue. 4 Enhancement agent suggests metrics; accept two. 5 Add co-author, link, save draft then submit. 6 See idea on lifecycle timeline with SLA. 7 Get notification of decision with reason. 8 See points arrive on profile.

**Marcus (Collaborator).** 1 Browse, filter by Tech and team. 2 Open idea, read agent thread summary. 3 Upvote, comment, follow. 4 Click "I want to help build". 5 Owner accepts the volunteer. 6 Log contribution on Prototype. 7 Appear as credited contributor on Implemented.

**Elena (Reviewer).** 1 Open queue sorted by SLA risk. 2 Read reviewer brief (simulated) with risks. 3 Score impact/effort/alignment. 4 Review agent proposes a decision; she overrides or confirms. 5 Write reason (blocked if empty). 6 Assign owner. 7 Status updates everywhere; author notified.

**Tomas (Team lead).** 1 See "Awaiting owner" alert. 2 Take ownership; request hours. 3 Leadership approval lands; Prototype begins. 4 Check off tasks; post update. 5 Workflow agent nudges on stale ideas; he approves a drafted reminder. 6 Mark Implemented with impact data. 7 Announcement and attribution published.

**Dana (Leadership).** 1 Open dashboard in leadership view. 2 Read analytics agent insight (simulated) on bottleneck. 3 Drill into stuck stage. 4 Approve hour pool requests. 5 Sponsor an ideathon challenge. 6 Review impact totals and Idea of the Quarter nomination.

**Sam (Admin).** 1 Open Admin. 2 Change a review SLA. 3 Adjust a scoring weight; see it reflect in the review form. 4 Edit a point value; ledger preview recalculates. 5 Manage panel members. 6 Reset demo data.

**Golden path (about 8 minutes, one connected story).** 1 *Dashboard* as Dana: bottleneck insight shows "Process" ideas stuck in review. 2 Switch to Priya; *Submit* a Process idea ("shorter release checklist"); similar-idea agent surfaces an existing one; enhancement agent adds a metric. 3 Submit; it appears in *Discovery*; switch to Marcus, upvote, comment, volunteer. 4 Switch to Elena; *Review* queue shows the new idea with SLA; brief, score, decision form rejects empty reason; accept with owner Tomas. 5 Tomas in *Delivery*: hours granted, tasks ticked, update posted, mark Implemented with 120 hours/quarter saved. 6 *Ideathon*: run Pitch day on an existing campaign, cast panel and audience votes, winner becomes a hackathon problem statement. 7 *Recognition*: ledger shows points for Priya (quality-weighted, impact bonus), Marcus (collaboration), Elena (timely review); a badge unlocks. 8 *Profile* and *Dashboard* now show updated counts and impact; *Admin* changes a point value and the ledger preview shifts.

## 6. Gaps and recommended additions (ranked)

| # | Addition | Rationale | Cost in single file |
|---|---|---|---|
| 1 | Persona switcher ("view as") | Makes six journeys demonstrable | Low |
| 2 | Notification inbox + follow updates | Delivers the reply guarantee | Low-med |
| 3 | Unified activity log feeding timeline, feed, ledger | One source of truth keeps modules connected | Low (architectural) |
| 4 | Agent approval queue with simulated-AI badge and run log | Shows the agentic loop and human gate visibly | Medium |
| 5 | "Needs Info" state and author response | Stops reviewers rejecting for missing detail | Low |
| 6 | Parked revisit dates with auto-resurface | Prevents second black hole | Low |
| 7 | Impact method field (baseline, evidence, confidence) | Makes impact credible, not vanity | Low |
| 8 | Guided demo mode / "tour" with scripted golden path | Founder demos reliably | Medium |
| 9 | Decline with "what would change our mind" + linked resubmit | Turns rejection into learning | Low |
| 10 | Innovation time pool (quarterly balance) | Brief says leadership grants hours; needs a ledger | Low-med |

**Recommend NOT building now:** real chatbot panel; real file upload; email/Slack integration; real SSO or permissions; threaded comments and @mentions; gamified streaks or daily-login points (rewards volume); public leaderboard of idea counts; live ideathon event mode; any live Kompass call (invocation is unverified).

## 7. Recognition framework (all values PROPOSALS)

Principle: points follow *outcomes and collaboration*, not submissions. Most points are earned downstream of a decision.

| Event | Points | Notes |
|---|---|---|
| Submit complete idea (template quality passes check) | 5 | Capped at 3 awards per month |
| Idea reaches Accepted | 30 | Author and co-authors share |
| Idea reaches Prototype | 40 | Owner and contributors |
| Idea Implemented | 100 | Split by contribution share |
| Verified impact bonus | 25 to 150 | Scaled by evidence-confidence and size band |
| Join/merge into an existing idea instead of duplicating | 10 | Rewards deduplication |
| Substantive comment marked "helpful" by author | 3 | Max 5 per idea |
| Volunteer contribution accepted and delivered | 20 | Delivery-tied |
| Reviewer decision within SLA with reason | 8 | Rewards the reply guarantee |
| Pitch day finalist / winner | 15 / 60 | |
| Idea of the Quarter | 150 | Chosen by panel and leadership |
| Declined idea resubmitted and later accepted | 10 bonus | Rewards iteration |

Upvotes earn no points directly; a small "community signal" bonus (5) applies only at Accepted.

**Levels (proposed):** Spark 0, Contributor 50, Builder 200, Catalyst 500, Pioneer 1000.

**Badges (proposed):** First Reply (first decision received), Team Player (3 co-authored ideas), Deduplicator, Builder (volunteer delivered), Closer (idea Implemented), Impact 100 (100+ hours saved verified), Sharp Reviewer (10 on-time reviews), Pitch Winner, Comeback (declined then accepted), Quarter Champion.

**Anti-gaming rules:** no self-voting or self-"helpful" marks; points for submission capped monthly and zero if template quality check fails; duplicates earn nothing but joining earns; impact bonus requires baseline plus a second-person verification; reciprocal vote rings flagged by Recognition agent for human review; points vest at outcome events, so withdrawn or declined ideas never inflate totals; anonymous points sit in escrow until reveal; all rules visible on a rules page, and every ledger row cites its rule.

## 8. Open questions for the founder (max 6)

1. Who is the final authority on innovation hours: panel, team lead's manager, or a leadership budget-holder, and is there a quarterly pool?
2. Should anonymous authors ever be able to claim credit, and if so is the escrow-and-reveal model acceptable?
3. What are the real SLAs (pickup days, decision days), or may we ship the proposed 3/10/14 as admin-editable defaults?
4. How is "impact" verified in practice: self-reported, manager-confirmed, or finance-confirmed? This determines the bonus design.
5. Are cash or material rewards in scope for the Annual Award, or recognition only?
6. For the demo, is the audience internal Dotkonnekt staff, or will it be shown to customers as a Kompass reference use case? That changes how prominently the Kompass simulated integration should appear.

*Unverified and out of scope for this analysis: how an external app invokes a Kompass workflow or agent, human-approval nodes, webhooks, structured outputs, and the exact Dotkonnekt design tokens (see CONTEXT.md sections 3 and 4).*
