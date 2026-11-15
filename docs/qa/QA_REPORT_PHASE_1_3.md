# QA Report: Idea Hub MVP, build phases 1-3
Tester: Agent 5 (independent). File under test: /home/claude/build/idea-hub.html (not modified). Scripts: /home/claude/build/qa/. Chromium via Playwright, file://, fonts blocked, plus one fully offline pass.

## (a) Summary
- No P0 and no P1. 8 defects: 1 x P2, 7 x P3, plus a few observations.
- 30 check rows below: 25 PASS (one with a note), 3 FAIL, 1 NOT TESTED, 1 observation. About 230 scripted assertions sit behind them.
- Dead-control scan: 1,500 de-duplicated clicks (employee 469, reviewer 527, admin 504) over 33 routes. Only real dead control: "Add tag" with empty input (D6). Other zero-effect clicks were links to the tab already open.
- Main risk: long unbroken text breaks layout (D1). XSS is not a problem.

## (b) Checks
| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | Dark theme toggles, persists; screens viewed: Home, Explore, Idea, Submit, Review, Pipeline | PASS | Contrast and legibility fine; D2 on Home |
| 1b | Light viewed: Home 1280; Home, Idea, Review, Pipeline 375 | PASS | D2 |
| 1c | Light Explore/Submit/Idea/Review/Pipeline at 1280; dark 375 | NOT TESTED | Captured, never viewed |
| 2a | Typing keeps focus and caret while assist refreshes | PASS | Mid-string caret preserved |
| 2b | Similar ideas: match % and terms; Open, Follow, Join, "Mine is different" | PASS | "64%"; request recorded in `coAuthorRequests` |
| 2c | Category/tag chips and enhancement suggestions apply and dismiss | PASS | Category-chip dismiss not exercised; D7 |
| 2d | Co-author add/remove; anonymous toggle disables co-authors | PASS | |
| 2e | Attachment validation; required fields | PASS | "not a url" and `javascript:` rejected; 7 inline errors, nothing created |
| 2f | Save draft, resume (list, direct URL, after reload), delete; draft privacy | PASS | All fields restored; hidden from others, Explore and direct URL |
| 3 | My ideas tabs follow actions | PASS | Counts equal rows; unfollow and unvolunteer remove rows |
| 4 | Anonymous ideas (new plus seeded `idea_anon`) vs 6 other personas | PASS | Scanned cards, detail (5 tabs, collapsed details opened), activity, bell panel, global and Explore search by name, similar panel, home, pipeline, review queue and workspace, agent log, author profile (count excludes anonymous ideas) |
| 4b | Author-typed attachment label "Priya Nair doc" | Observation | Shown verbatim; user content that can de-anonymise |
| 5a | Withdraw; needs-info loop (clock paused, answer returns to review) | PASS | D4 |
| 5b | Merge (target gains co-author, "Merged into" shown); park with revisit date; decline with "what would change our mind" | PASS | Missing or past dates blocked |
| 5c | Accept with owner vs awaiting owner, then take ownership; reviewer cannot decide own idea | PASS | |
| 6 | Home KPIs, tile links, Explore, Pipeline columns, bell badge, vote/comment counts, profile, notifications equal store (3 personas, before and after submit, vote, comment, accept) | PASS | D3 |
| 7a | Reload keeps state; reset restores seed (counts, statuses, config, votes, users, panels, comments) | PASS | Actions land after 50-140 ms; a reload inside that window loses them |
| 7b | Corrupt JSON (garbage, truncated, null, wrong shape, wrong schema) | PASS | Visible "Saved data was reset" banner |
| 7c | `setItem` throws; `localStorage` getter throws | PASS | In-memory banner; app usable |
| 7d | Valid-shape but broken entities | PASS, note | Error screen with "Reset demo data", not blank; not auto-recovered |
| 7e | Fully offline | PASS | Boots and renders; only font request fails |
| 8 | Dead-control scan | PASS | D6 |
| 9 | Role guards (7 route/persona pairs), switch button, API refusal | PASS | |
| 10a | Dialog: Escape, backdrop, Cancel; trap; focus returns on Escape/Cancel; focus ring | PASS | `role=dialog`, `aria-modal=true`; ring on 14 Tab stops |
| 10b | Background inert; focus after Confirm; popover focus | FAIL | D5 |
| 11a | Hostile markup renders as text | PASS | No `<img>`, zero `alert()` in title, problem, comment, tag, reason, question, attachment |
| 11b | 300-character unbroken string keeps layout | FAIL | D1 |
| 12 | Every agent block labelled "Simulated"; no live Kompass claim; decision form empty after brief | PASS | 65 blocks, 5 personas, 22 routes; only negations of a Kompass connection |
| 13a | No horizontal overflow at 375/768/1280/1920, seed data, 3 personas x 23 routes | PASS | |
| 13b | Same with long content | FAIL | D1 |

## (c) Defects
**D1 (P2) Long unbroken text overflows the page.**
- Routes: `#/ideas/:id`, `#/review/:id`, `#/explore`, `?tab=activity`, global-search dropdown, submit form. Any persona.
- Repro: submit an idea (or `api.ideas.submit`) with one of these, then open the routes.
  - 300-character problem or solution: detail page +2,646px (the Review Intelligence summary repeats it and escapes its card).
  - 120-character title: +784px.
  - 300-character attachment label: +2,010px.
  - 300-character tag (the UI accepts it, there is no length cap): +1,060px on detail and review, +1,052px on Explore.
  - Decline with a 300-character reason: Activity tab +1,804px.
  - Search dropdown for a long title: +134px sideways.
- Expected: wrap or truncate, no horizontal scroll. Actual: horizontal page scroll. Comments, beneficiaries and success wrap correctly.

**D2 (P3) Home "Where ideas are now" labels collide.** Home, any persona, 1280 and 375, light and dark. "SubmittedUnder review" and "DecisionPrototypeImplemented" run together; "Implemented" passes the card edge.

**D3 (P3) Home tiles disagree with the pipeline.** "Awaiting review 14" ("submitted or in review") excludes the one `needs_info` idea; Pipeline Submitted 3 + Under review 12 = 15 includes it. The five tiles also do not sum to Total 37 (no tile for needs-info, parked, declined, merged).

**D4 (P3) Withdraw text contradicts behaviour.** The dialog says the idea "stays visible as withdrawn". It is absent from default Explore and Total ideas, and appears only under Status = Withdrawn.

**D5 (P3) Dialog and popover accessibility.** Background not `inert` or `aria-hidden` behind a modal; focus goes to `<body>` after Confirm and after Escape on the persona or bell popover; opening a popover does not move focus into it.

**D6 (P3) "Add tag" with empty input does nothing.** `#/submit`, any persona, no feedback.

**D7 (P3) Enhancement block is silent until a category is chosen.** `#/submit`: title and problem typed, no category, no Idea Enhancement block and no hint.

**D8 (P3) Review workspace right column scrolls on its own.** `#/review/idea_flaky` as Elena, 1280: `.rv-right` is 1,869px inside an 814px container. The decision form is only reachable by scrolling inside it, and "Risks and dependencies" is clipped at the bottom with no visible cue. I did not check scrollbar visibility.

Observations: every action (including the theme toggle) has 50-140 ms simulated latency; vote buttons are 30px tall at 375; `__ideaHub.buildSeed()` overwrites live state when called; Ideathons, Recognition, Agent log and Admin editing are labelled "arrives in build phase N" placeholders; Home shows "Taking part 100%", and I could not tell if that is intended.

## (d) Visual observations (screenshots I viewed)
- Dark 1280, Home, Idea, Submit, Review, Pipeline (full pages) and Explore (viewport): text contrast is good, badges, meters and the agent card read clearly. Only defect is D2.
- Light 1280 Home matches dark. Funnel bar labels are very small (about 8px).
- Light 375 Home, Idea, Review, Pipeline stack cleanly with no overlap. The Idea tab row cuts "Decision history" at the edge (it scrolls).
- Pipeline 1280 scrolls horizontally inside its container: Prototype cards are truncated and Implemented is off-screen until scrolled.
- Hostile long text, 1280 idea detail: title and problem run past their card and the Review Intelligence panel clips text (D1).
- Full-page screenshots show the sidebar background ending at 900px. I took this to be a sticky-sidebar artifact and did not count it.

## (e) Not tested
- Row 1c screenshots (captured, not viewed); dark-theme interactive states and mobile drawer.
- Buttons inside modals and popovers beyond Cancel, backdrop and Escape (the scan clicked page content in the default state, de-duplicated by signature).
- Admin editing, Ideathons, Recognition, Agent log (placeholders).
- Cross-tab `storage` sync, screen readers, real touch devices.
- Review-timer warning and overdue thresholds: seen only on seed data, not by changing config or dates.
- One `radio.check({force:true})` on a review score failed once ("state did not change"); 8 reruns passed. Unconfirmed possible race when the form re-renders.
