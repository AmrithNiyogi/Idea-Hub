# IdeaKonnekt: Presenter Guide (Hackathon Demo)

Goal: in about 5 minutes, show how one idea goes from "I have an idea" to "it's being built", with the platform doing the boring work.

---

## Before you go on stage (checklist)

1. Start the stack (backend folder):
    - `./scripts/dev-services.sh up`
    - `uv run alembic upgrade head`
    - `uv run python -m app.seed.demo`
    - `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
2. Start the frontend (frontend folder): `npm run dev` → open http://localhost:5173
3. Log in once in a test window. Login uses an emailed code. If email is slow, the code also prints in the uvicorn console (dev mode). Keep that terminal visible as a backup.
4. Demo accounts and password are in `backend/README.md` (use the Contributor and Reviewer accounts below).
5. Open two browser windows (or one normal + one private window). Log in as a contributor in one and a reviewer in the other. Switching accounts is faster this way.
6. Have one idea title ready to type live (see Step 3).

---

## The story in one line

> "Good ideas die in chat threads. IdeaKonnekt gives every idea a path: submit, check for duplicates, review with a clear decision, fund, build, and get recognized."

---

## Step 1: Hook (30 seconds)

- Say: "Raise your hand if you've had an idea that got lost in a group chat."
- Show the Home screen. Point at the pipeline or your own ideas.

---

## Step 2: Log in as a contributor (30 seconds)

- Log in with a contributor account (Priya).
- Say: "Login is email plus password, then a one-time code. Same security standard as our admin tools."

---

## Step 3: Submit an idea, the wow moment (1 minute)

1. Open **Submit**.
2. Type a realistic title, for example: `Auto-draft runbooks from incident timelines`.
3. As you type the problem statement, pause and point at the **similar ideas** panel.
   - Say: "It checks for duplicates while I type. If someone already has this idea, I can join them and still earn points."
4. Point at the **idea intelligence** hints: suggested category, suggested tags, and missing fields.
5. Optional: open the **co-pilot chat** and ask it to help fill a field. It fills the form for you.
6. Complete the template (all 8 items) and submit.
7. Point at what happened automatically:
   - The idea moved to **Under review**.
   - Pickup and decision deadlines were set (3 and 10 days).
   - The right review panel got notified.
   - Say: "No one had to route this. The clock started on submit."

---

## Step 4: Review as a reviewer (1.5 minutes)

1. Switch to a reviewer account (Elena) in the other window.
2. Open **Review**. The idea is in the queue, with an overdue count if any.
3. Open the idea. Show the **reviewer brief**:
   - Comments sorted into pros, concerns, and questions.
   - Suggested impact, effort, and alignment scores.
   - A suggested decision.
   - Say: "The brief suggests. A human decides. It never writes the scores for us."
4. Record a decision:
   - Add scores.
   - Write a reason (at least 20 characters). Say: "We require a written reason, so decisions are never a mystery."
   - Choose **Accept** (it asks for an owner and hours) or **Park** (it asks for a revisit date).
5. Submit. Show the idea status change.

**Governance moment (strong impression):** Try to decide on your own idea, or on an idea you co-authored. The platform blocks it. Say: "Conflict-of-interest rules are built in. You cannot approve yourself."

---

## Step 5: Show the leadership view (45 seconds)

- Open **Insights** (log in as leadership if needed).
- Point at:
  - The funnel (how ideas moved through stages).
  - Review speed against SLA, and where the bottleneck is.
  - The rule-generated insight cards.
- Say: "Leadership sees where ideas get stuck, without asking anyone for a status update."

---

## Step 6: Build handoff (45 seconds)

- Open an accepted idea and show the **agent context** or build option.
- Say: "One click creates a context pack: the idea, its history, the decision, the discussion, and the tasks. Developers or coding agents can start from it with no re-explaining."
- If a Kompass coding agent is configured, say it is sent there. If not, say it runs a simulated timeline (be honest about this).

---

## Step 7: Recognition (30 seconds, optional)

- Open **Recognition** to show the points leaderboard.
- Say: "Points come from submitting, reviewing on time, delivering, and verified impact. Duplicates earn nothing; joining an existing idea earns points. That encourages collaboration over copies."

---

## Step 8: Close (30 seconds)

> "In five minutes: an idea was checked for duplicates, routed with deadlines, decided with a reason, traced to delivery, and recognized. That is IdeaKonnekt."

Then take questions.

---

## If something goes wrong on stage

| Problem | What to do |
|---|---|
| Login code email is slow | Use the code printed in the uvicorn console (dev mode). |
| Page is blank or errors | Refresh once. If still broken, switch to the screenshots in your slides and keep narrating. |
| Duplicate-check panel shows nothing | Type a longer problem statement with words from the seeded ideas (for example: "runbook", "incident", "agent"). |
| Build step shows a simulated timeline | Say so plainly: "This is the simulated path. The live path needs the coding agent connected." |
| Wrong account | Use the second window you prepared. |

---

## Do not say (keep it honest)

- Do not claim the live coding agent or external integrations (Jira, ClickUp, Teams, Notion) are running unless you have checked they are connected.
- Do not promise the AI news feed is live during the demo. It depends on external sites.
- Do not claim the product is fully production-ready. It is a working prototype.

---

## Notes for the team (not for the audience)

- Known risk: the frontend has one failing test (`Login.test.tsx`, "shows loading while auth bootstraps"). It is not on the main demo path, but fix or avoid it if time allows.
- Verify the sidebar labels and the exact page names on the day, since the UI may have changed after this guide was written.
- Practice the full run once with a timer. Target 5 minutes, leave 2 minutes for questions.
