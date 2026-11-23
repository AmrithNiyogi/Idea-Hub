# IdeaKonnekt: knowledge base for the Help agent

This file is the source of truth the **IdeaKonnekt Help** agent answers from. Attach it to the agent as a knowledge file. Keep it in sync with the app: when a page, rule, role or number changes, update this file in the same change.

**Rules for the agent (summary):** answer only from this file. If something is not covered, say so and point to the closest page. Never invent pages, buttons, numbers or URLs. Only link to paths in section 14.

Contents:
1. What IdeaKonnekt is
2. Signing in and your account
3. Roles and what each can do
4. Navigation map
5. Ideas: writing, submitting and the team
6. Idea lifecycle and statuses
7. Review: queue, scoring and decisions
8. Reopening parked or declined ideas
9. Collaboration: co-authors and build partners
10. Ideathons
11. Groups, channels and direct messages
12. Recognition: points, levels and badges
13. Delivery, problems, insights and the newsletter
14. Redirect map
15. Agents, integrations and the AI features
16. Admin
17. Frequently asked questions
18. Limits of this knowledge

---

## 1. What IdeaKonnekt is

IdeaKonnekt is Dotkonnekt's internal platform for ideas. People submit ideas. Others discuss, follow and comment on them. Reviewers score and decide on them. Accepted ideas can move into delivery. The company runs ideathons (timed innovation campaigns). The platform also covers recognition, groups and direct messages, a problem radar, an AI newsletter, agents and integrations with external trackers.

Idea statuses, roles and the review rules described here come from the product code. Some numbers, such as recognition points, are proposals that may be tuned. When this file and the app disagree, trust the app and tell the user to check the page.

---

## 2. Signing in and your account

- **Email code (default):** enter your email and password, then the one-time code sent to your email.
- **Password:** accounts with a local password can sign in with it.
- **Microsoft SSO:** if your organisation enabled it, you can sign in with your Microsoft work account. Those accounts do not have a IdeaKonnekt password.
- **Authenticator app (MFA):** if your account has a local password, you can add an authenticator app on `/profile`. Press **Set up authenticator**, scan the QR code, enter the 6-digit code and confirm. To turn it off you need your password and a current code. Microsoft SSO-only accounts cannot set up the authenticator app yet.
- **Changing your password:** on `/profile`. If your account signs in with Microsoft, the password section says Microsoft manages the password and has a button to open the Microsoft account page.
- **Your profile:** name, title and avatar are on `/profile` (also `/settings`). Other people see your profile at `/people/<id>`.
- **Sign-in problems or a wrong email:** contact an administrator.

**Never share passwords or one-time codes with the Help agent.** It does not need them and does not store them.

---

## 3. Roles and what each can do

An account can hold more than one role. The role you are acting as (your active role) decides which sidebar items you see. Switch role from the account menu if you have several.

| Role | Purpose | Typical actions |
|------|---------|-----------------|
| **Contributor** | Everyone's base role | Submit ideas, comment, follow and vote, collaborate on others' ideas, track your own ideas, thank teammates. |
| **Reviewer** | Runs reviews for a panel | Work the review queue, pick up ideas, score them, record decisions, and show up as the reviewer on an idea. |
| **Team lead** | Runs accepted ideas | Owns delivery for accepted ideas, manages delivery tasks, updates and contributors, and logs innovation time. |
| **Leadership** | Oversight and approvals | Approvals (innovation hours and similar), insights, creating and organising ideathons, confirming winners, and recognition awards. |
| **Administrator** | Platform setup | Everything leadership can do, plus people and roles, panels and their members, categories, timelines, scoring and points settings, and demo data. |

Sidebar visibility by role (from the navigation rules):
- **My ideas:** contributors, reviewers and team leads.
- **Review:** reviewers and administrators.
- **Approvals and Insights:** leadership and administrators.
- **Agent hub:** reviewers, team leads, leadership and administrators.
- **Admin:** administrators only.
- Everything else (Home, Explore, Ideathons, Problem radar, Pipeline, Recognition, Groups, Messages, AI Newsletter, My profile, Integrations) is shown to everyone.

Organiser actions in ideathons (create, edit, move phase, shortlist, pitch scores, confirm winners, handoff) need the **leadership** or **administrator** role.

---

## 4. Navigation map

Sidebar sections, in the order they appear:

| Section | Item | Path | Who |
|---------|------|------|-----|
| (top) | Home | `/` | Everyone |
| Shape | Explore | `/explore` | Everyone |
| Shape | My ideas | `/my` | Contributors, reviewers, team leads |
| Shape | Ideathons | `/ideathons` | Everyone |
| Shape | Problem radar | `/problems` | Everyone |
| Review | Review | `/review` | Reviewers, administrators |
| Review | Approvals | `/approvals` | Leadership, administrators |
| Build | Pipeline | `/pipeline` | Everyone (what you see depends on your role) |
| Recognise | Recognition | `/recognition` | Everyone |
| Connect | Groups | `/groups` | Everyone |
| Connect | Messages | `/dms` | Everyone |
| Insight | AI Newsletter | `/news` | Everyone |
| Insight | Insights | `/insights` | Leadership, administrators |
| Insight | Agent hub | `/agents` | Reviewers, team leads, leadership, administrators |
| You | My profile | `/profile` (same page as `/settings`) | Everyone |
| You | Integrations | `/integrations` | Everyone (administrators set organisation defaults) |
| You | Admin | `/admin` | Administrators |

Pages reached from links rather than the sidebar are listed in section 14.

**Top bar:** search ("Search ideas, teams, people"), **New idea** (opens Submit), notifications, the theme toggle and your account menu. The round sparkle button at the bottom-right opens this Help chat.

---

## 5. Ideas: writing, submitting and the team

### What an idea contains
- **Title** (up to 120 characters).
- **Category**, such as tech, business, process or innovation. Pick the one that fits best.
- **Problem statement:** who is affected, what goes wrong and how often. At least 20 characters.
- **Proposed solution:** what you would build or change.
- **Who benefits:** teams, roles or customers, with rough numbers if possible.
- **Success measures:** a measurable target, for example "from X to Y by when".
- **Rough effort:** S = days, M = weeks, L = about a quarter, XL = multi-quarter.
- **Tags** (up to 8), to help others find it.

Submitting requires a title, a category, a problem, a solution, who benefits and success measures. You can save a draft at any time from `/submit`, and come back with `/submit?draft=<id>` or from **My ideas**.

### The Team section (on Submit)
- **Teammates:** search for people who worked on the idea. They are added as **co-authors** straight away, so they can edit and link the idea. Use this for everyone who really worked on it.
- **Team name:** optional, free text (up to 120 characters).
- **GitHub repository:** optional, one link in the form `https://github.com/owner/repo`. One repository per idea.

### Anonymous submissions
Tick **Submit anonymously** to hide your name from everyone, including reviewers, on the idea and in discussion. You still see it as yours.

### The Idea page (`/ideas/<id>`)
Shows the idea, its status and history, the author and co-authors, team name and GitHub link, the discussion, follows and votes, and the review decision once there is one.

### Help from the AI assistant on Submit
The Submit page has an assistant that can help you brainstorm, improve fields, and suggest similar ideas. It proposes changes; you decide what to keep. Some of these agents may still be simulated.

---

## 6. Idea lifecycle and statuses

Statuses and what they mean:

| Status | Label | What it means | What comes next |
|--------|-------|---------------|-----------------|
| `draft` | Draft | Only you can see it. | Submit it. |
| `submitted` | Submitted | Waiting in the review queue. Can be withdrawn. | A reviewer picks it up, or you withdraw it. |
| `under_review` | Under review | A reviewer is assessing it. | Needs info, accepted, parked, merged, declined, or withdrawn. |
| `needs_info` | Needs info | The reviewer asked the author a question. | The author answers, and it returns to under review. Or it can be withdrawn. |
| `accepted` | Accepted | Approved. Owner and innovation hours are set. | Prototype, or declined. |
| `parked` | Parked | Not now. A revisit date is set. | Back under review, when reconsidered. |
| `merged` | Merged | Combined into another idea. | Final. |
| `declined` | Declined | Not going ahead. A reason is always given. | Final, unless reopened (section 8). |
| `prototype` | Prototype | Being prototyped. | Implemented, parked, or declined. |
| `implemented` | Implemented | Delivered. | Final. |
| `withdrawn` | Withdrawn | The author withdrew it. | Final. |

The **Pipeline** page (`/pipeline`) groups ideas into five stages: Submitted, Under review, Decision, Prototype and Implemented.

Withdrawing is possible while an idea is submitted, under review, or needs info.

---

## 7. Review: queue, scoring and decisions

### The review queue (`/review`)
- Reviewers see ideas that are under review or need info, sorted by their due date (the review deadline), then by submission date.
- **Pick up** an idea to claim it. Only one reviewer picks it up. Once picked up, you are the reviewer on that idea. A notification tells the author a decision is due by the date shown.

### Scores
Score each idea from **1 to 5** on three dimensions:
- **Impact:** how much value it could create.
- **Effort:** how hard it is to deliver (higher score means easier, check the page wording).
- **Alignment:** how well it fits the company's current direction.

You can save scores while you are still assessing. Scores are required for every decision except "needs info".

### Decisions
Record one decision with a written reason. The reason must be **at least 20 characters**, and the author sees it.

| Decision | Result status | Extra required fields |
|----------|---------------|-----------------------|
| **Accept** | Accepted | An owner (or tick "awaiting owner") and recommended innovation hours, from 1 to 400. |
| **Park** | Parked | A revisit date in the future. |
| **Merge** | Merged | The active idea to merge into (it must be under review, needs info, accepted or prototype, and cannot be the same idea). |
| **Decline** | Declined | "What would change our mind?", at least 10 characters. |
| **Needs info** | Needs info | The question for the author, at least 20 characters. No scores needed. |

A decision with a written reason on or before the due date also earns the reviewer recognition points (section 12).

### The review brief
A Review Intelligence brief can suggest scores, risks and a likely decision. It is a suggestion. The reviewer confirms every score and decision.

---

## 8. Reopening parked or declined ideas

Parked and declined ideas can be reopened when the conditions for reopening are met. Agents can propose a reopen; reviewers or administrators approve it. Approving moves the idea back to under review and restarts the review clock using the timelines set by administrators. If you think an idea should be reconsidered, add to the discussion or contact a reviewer.

---

## 9. Collaboration: co-authors and build partners

On an existing idea, the collaboration panel lets people ask to:
- **Co-author:** join the idea as a co-author. The author or an administrator responds.
- **Build:** ask to help build it (a build partner).

Requests can be accepted or declined. Co-authors share the author's rights on the idea, such as editing and linking it to an ideathon. Points for co-authors are shared with the author where the rules say so (section 12).

---

## 10. Ideathons

An ideathon is a timed campaign with a theme, up to three challenge statements (each 20 to 300 characters), a start date and an end date.

### Phases (in this order, and never skipped)
1. **Open:** submissions are open. The organiser needs at least 2 entries before moving on.
2. **Shortlist:** the organiser approves a shortlist of 2 to 6 entries.
3. **Pitch day:** panel members score each shortlisted idea from 1 to 10, and the audience votes. Voting is closed before results.
4. **Results:** the organiser confirms 1 or 2 winners.
5. **Handoff:** each winner gets a handoff statement for the backlog. Then the ideathon is marked complete.

Once complete, an ideathon is locked.

### Entering an ideathon
- Open the ideathon and press **Submit to this ideathon**. The new idea is added to the ideathon automatically when you submit.
- Or, on the ideathon page, pick one of your existing ideas under **Or link one of your existing ideas**. Only ideas that are submitted or further along can be linked, and each idea can be in only one ideathon.
- Only an author or a co-author can link an idea. Links are only accepted while the ideathon is open.

### Organisers
Leadership and administrators can:
- create an ideathon at `/ideathons/new`
- edit it at `/ideathons/<id>/edit`. Title and dates can change until the ideathon completes. Theme and challenges can change only while it is open.
- move it to the next phase, shortlist, score, confirm winners and send handoffs

Some ideathon steps can use AI assistance to draft challenge wording, names, clusters and a shortlist suggestion. Organisers decide what to use.

---

## 11. Groups, channels and direct messages

### Groups (`/groups`)
- A group has channels (like `#general`) and a chat.
- A group can be linked to an idea, so members can talk about it in one place.
- Each member has a role in the group: **owner**, **admin** or **member**. Owners and admins can invite people, manage members and channels. Only owners can change admin roles.
- Invites can be sent to people. The invited person accepts or declines from **Groups → Invites**.
- You can create a group from the Groups page.

### Direct messages (`/dms`)
- One-to-one chats with one person. Start one from their profile or from the Messages page.
- The DM screen fills the window: the header is at the top, messages scroll in the middle and the composer stays at the bottom.
- You can insert emoji with the smiley button next to the message box.

### Message updates
Messages refresh about every 8 seconds while the page is open, and again when you return to the tab. If a message seems missing, reload the page.

---

## 12. Recognition: points, levels and badges

Recognition (`/recognition`) rewards the people who move ideas forward. Points, levels and badges are shown on the page.

### Ways to earn points (values as currently configured; check the page for the latest)
- **Submit a complete idea:** 5 points (up to 3 awards a month).
- **Idea reaches Accepted:** 30 points, shared equally by the author and co-authors.
- **Idea reaches Prototype:** 40 points, shared by the owner and current contributors.
- **Idea Implemented:** 100 points, split by the contribution shares agreed when the idea is marked implemented.
- **Verified impact bonus:** 25 points.
- **Join or merge instead of duplicating:** 10 points.
- **A comment marked helpful by the author:** 3 points (up to 5 per idea).
- **Volunteer contribution delivered:** 20 points.
- **Reviewer decision on time:** 8 points, when the written reason is given on or before the due date.
- **Pitch day finalist:** 15 points. **Pitch day winner:** 60 points (replaces the finalist points).
- **Idea of the Quarter:** 150 points, confirmed by leadership.
- **Annual Innovation Award:** 300 points, confirmed by leadership.

### Thanks
A teammate can send a thank-you note (**4 points** to the recipient). Each person can send 3 a month, and only one to the same teammate.

### Levels (by total points)
Spark (0) → Contributor (50) → Builder (200) → Catalyst (500) → Pioneer (1000).

### Badges
First Reply, Team Player, Deduplicator, Builder and Closer, awarded for specific actions shown on the page.

Administrators can change the point values under the platform's points settings. The numbers above are the defaults in the code.

---

## 13. Delivery, problems, insights and the newsletter

### Delivery
Accepted ideas can move into **delivery**, run by the team lead for that idea. Delivery has:
- **Contributors:** the people doing the work.
- **Tasks:** work items with progress.
- **Updates:** short progress notes.
- **Time logs:** time spent on the idea.
- **Contribution shares:** how credit is split, used when the idea is implemented.
- **Impact entries:** evidence of the impact achieved. Someone else can verify an impact entry with a note of what they checked (at least 10 characters).

### Problem radar (`/problems`)
Problems are grouped automatically from the problem statements and tags of ideas. You can see the problems people raise most, open one at `/problems/<key>`, and add **me too** to show you have the same problem. Leadership can add notes to a problem.

### Insights (`/insights`)
For leadership and administrators: charts and metrics on ideas, reviews, delivery and impact.

### AI Newsletter (`/news`)
A list of recent AI news and open-source AI repositories, gathered from public sources. Items are for information, not recommendations.

---

## 14. Redirect map

Only link to these paths. Use the exact path. Do not add a domain. Replace `<id>` and `<key>` with a real value the user has given you; if you do not have one, link to the list page instead.

**Home and discovery**
- `/` Home
- `/explore` Explore all ideas
- `/my` My ideas (drafts and submitted ideas)
- `/ideas/<id>` One idea
- `/problems` Problem radar
- `/problems/<key>` One problem

**Submitting**
- `/submit` Submit an idea (also "New idea" in the top bar)
- `/submit?draft=<id>` Continue a draft

**Review and approvals**
- `/review` Review queue
- `/review/<id>` Review one idea
- `/approvals` Approvals
- `/pipeline` Pipeline

**Ideathons**
- `/ideathons` Ideathons
- `/ideathons/new` New ideathon (organisers)
- `/ideathons/<id>` One ideathon
- `/ideathons/<id>/edit` Edit an ideathon (organisers)

**Recognition**
- `/recognition` Recognition

**Connect**
- `/groups` Groups
- `/groups/<id>` One group
- `/dms` Messages
- `/dms/<id>` One direct message
- `/people/<id>` Someone's profile

**Insight and agents**
- `/news` AI Newsletter
- `/insights` Insights (leadership)
- `/agents` Agent hub

**You**
- `/profile` My profile, password and authenticator app (also `/settings`)
- `/integrations` Integrations
- `/integrations/<provider>` One integration (for example `/integrations/clickup`)
- `/admin` Admin (administrators)

**Sign in**
- `/login` Sign in

---

## 15. Agents, integrations and the AI features

### Agent hub (`/agents`)
Lists the agents built into the platform. Each agent **proposes** and people **decide**. Agents do not merge, decline or reveal anonymous authors on their own. Agents in the roster:
- **Idea intelligence:** classifies drafts, suggests tags, finds similar ideas and flags missing fields. The author decides.
- **Idea enhancement:** suggests rewrites, beneficiaries and metrics. Each suggestion is applied only when the author accepts it.
- **Idea optimizer:** a chat co-pilot after submit, to improve clarity, metrics, tags and problem framing.
- **Review intelligence:** prepares a reviewer brief with risks, discussion points, suggested scores and a possible merge target.
- **Coding agent (build):** for accepted ideas, prepares an agent context and skill pack and can kick off a build.
- **Innovation workflow:** finds stuck ideas, drafts reminders and proposes reopening where the conditions are met.
- **Recognition:** explains points under the published rules and drafts award nominations.
- **Innovation analytics:** narrates participation, the funnel, bottlenecks and impact, read-only.
- **Ideathon agents:** draft challenge wording and names, cluster ideas, and suggest a shortlist and pitch order.
- **Help (this assistant):** answers questions about IdeaKonnekt.

Some agents may still be **simulated**, which means their output is example output rather than a live result. Check the agent's page for its status.

### Integrations (`/integrations`)
Connect external tools so ideas and tasks stay in step:
- **Trackers:** ClickUp, Jira, and a custom webhook tracker. A tracker link keeps an idea and a remote task in step.
- **Docs:** Notion. Link a Notion page to an idea.
- **Chat:** Microsoft Teams, through an incoming webhook.
- **MCP connections:** connect a tool server for groups, where the group owner allows it.

A **personal** connection belongs to you. An **organisation default** is set by administrators. Removing a link does not delete the remote task or page.

### Microsoft SSO and MFA
See section 2.

---

## 16. Admin

Administrators use `/admin` to:
- **People and roles:** search users, add or remove roles, set a user's main role, disable or enable accounts, and delete accounts.
- **Review panels:** create panels, change their details, add or remove members and choose a chair.
- **Categories:** create and edit the categories ideas are filed under.
- **Timelines:** set the review and delivery timelines that drive due dates.
- **Scoring:** set how the review scores are weighted.
- **Points:** set the recognition point values.
- **Audit log:** see recent administrative actions.
- **Demo data:** reset the demo data. This replaces everything with the demo data, so it should only be used in a test environment.

Deleting an account is permanent. Disabling an account is reversible.

---

## 17. Frequently asked questions

Each answer gives the page to go to. The agent should use the redirect map paths.

**How do I submit an idea?**
Press **New idea** in the top bar or open `/submit`. Fill in the title, category, problem, solution, who benefits and success measures, then press **Submit idea**. Save a draft any time.

**Can I add my teammates?**
Yes. In the **Team** section on the Submit page, search for people. They become co-authors straight away. You can also add a team name and one GitHub repository. Link: `/submit`.

**How do I join an ideathon?**
Open the ideathon from `/ideathons` and press **Submit to this ideathon**, or link an existing submitted idea on the same page. Link: `/ideathons`.

**Why can't I link my idea to an ideathon?**
Common reasons: the ideathon is no longer open, the idea is still a draft, the idea is already in another ideathon, or you are not its author or a co-author. Link: `/ideathons`.

**Why can't I change my password?**
If your account signs in with Microsoft, Microsoft manages the password. Change it in your Microsoft account. Link: `/profile`.

**How do I set up an authenticator app?**
On `/profile`, open the authenticator app section, press **Set up authenticator**, scan the QR code, enter the 6-digit code and confirm. Microsoft SSO-only accounts cannot set one up yet. Link: `/profile`.

**Why is a message not showing?**
Messages refresh about every 8 seconds. If it is still missing, reload the page. Links: `/dms`, `/groups`.

**How do I thank someone?**
Use Recognition to send a thank-you note. Each person can send 3 a month, and only one to the same teammate. Link: `/recognition`.

**What do the review scores mean?**
Reviewers score impact, effort and alignment from 1 to 5. They help the panel compare ideas. Link: `/review`.

**Why did my idea get "needs info"?**
A reviewer asked you a question. Open the idea, read the question, and answer it. The idea returns to review. Link: `/ideas/<id>`.

**Why was my idea declined or parked?**
The reviewer's written reason is on the idea. A declined idea can be reopened later; a parked one has a revisit date. Link: `/ideas/<id>`.

**What happens after an idea is accepted?**
It gets an owner and innovation hours and can move into prototype and delivery. Link: `/pipeline`.

**Who can create an ideathon?**
Leadership and administrators. Link: `/ideathons/new`.

**Can I change an ideathon after it starts?**
Its title and dates can change until it completes. Its theme and challenges can change only while it is open. Link: `/ideathons/<id>/edit`.

**Where do I connect ClickUp, Jira or Notion?**
Open Integrations. Link: `/integrations`.

**I don't have access to a page. Why?**
Some pages are limited to certain roles. Check your active role in the account menu, or ask an administrator for the role you need. Link: `/profile`.

**How do I contact an admin?**
Use this chat for general questions. For access, account or sign-in problems, contact your administrator directly.

---

## 18. Limits of this knowledge

- The agent does not have access to live data. It cannot see a specific person's ideas, an ideathon's current phase, or any live status. It should say so and link to the page.
- Numbers, such as points, limits and deadlines, come from the app's code as of the last update. If the app and this file disagree, the app wins, and this file should be updated.
- Some agent and integration features may still be simulated. Say so when it matters.
- Questions about things not listed here should get an honest "I'm not sure", plus the closest page.
