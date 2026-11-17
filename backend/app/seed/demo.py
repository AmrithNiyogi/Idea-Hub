"""Seed teams, categories, 6 demo users, and ~18 ideas across statuses.

Idempotent: skips when demo users already exist.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.idea import Idea, StatusHistory
from app.models.review import Decision, Review
from app.models.user import Team, User
from app.services.auth_service import hash_password

logger = logging.getLogger("idea_hub.seed")

TEAMS = [
    ("team_plat", "Platform Engineering"),
    ("team_ai", "Data and AI"),
    ("team_des", "Product Design"),
    ("team_cs", "Customer Success"),
    ("team_rev", "Revenue Operations"),
    ("team_ops", "People and Operations"),
]

# slug, name, title, team_slug, primary_role, extra_roles
USERS = [
    ("priya", "Priya Sharma", "Senior Product Designer", "team_des", "contributor", ["lead"]),
    ("marcus", "Marcus Webb", "Backend Engineer", "team_plat", "contributor", []),
    ("elena", "Elena Rossi", "Staff Engineer", "team_plat", "reviewer", []),
    ("tomas", "Tomas Berg", "Engineering Manager", "team_plat", "lead", ["reviewer"]),
    ("dana", "Dana Okafor", "VP Product", "team_des", "leadership", []),
    ("sam", "Sam Patel", "Business Systems Administrator", "team_ops", "admin", ["reviewer"]),
]

CATEGORIES = [
    ("tech", "Tech", "var(--cat-tech)", "Engineering, infrastructure, tooling and platform."),
    ("business", "Business", "var(--cat-business)", "Revenue, customers, pricing and go-to-market."),
    ("process", "Process Improvement", "var(--cat-process)", "Handoffs, checklists, meetings, approvals."),
    ("innovation", "New Innovation", "var(--cat-innovation)", "New products, features and agent capabilities."),
]

# Compact idea seed: k, cat, author, co, effort, tags, title, problem, solution,
# beneficiaries, metrics, status, day_offset, optional decision fields
IDEAS: list[dict[str, Any]] = [
    {
        "k": "runbook",
        "c": "tech",
        "a": "marcus",
        "co": ["elena"],
        "eff": "M",
        "tags": ["automation", "observability", "docs"],
        "t": "Auto-draft runbooks from incident timelines",
        "p": "After each production incident an SRE spends three to four hours turning the chat timeline into a runbook, and about half of incidents never get one.",
        "s": "Generate a runbook draft from the incident timeline with human approval before publishing.",
        "b": "On-call engineers (about 40) and support engineers who triage repeat incidents.",
        "m": "Runbook coverage of Sev1/Sev2 from 50% to 90%; write-up time from 3.5h to 1h.",
        "st": "accepted",
        "sub": -34,
        "dec": {
            "o": "accepted",
            "by": "elena",
            "d": -27,
            "sc": [5, 3, 4],
            "r": "Repeat incidents are expensive and the evidence is solid. Scope is a draft generator with human approval, which keeps risk low.",
            "own": "tomas",
            "h": 60,
        },
    },
    {
        "k": "embeddings",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "M",
        "tags": ["cost", "performance", "agents"],
        "t": "Cache embeddings for repeated agent prompts",
        "p": "The support assistant re-embeds the same knowledge-base chunks on every run, adding roughly $6,000 a month in model spend.",
        "s": "Put a content-hash cache in front of the embedding call and invalidate only when chunk text changes.",
        "b": "Platform and ML engineers, plus finance owning the model budget.",
        "m": "Embedding spend down 70% within a quarter; test suites under 4 minutes.",
        "st": "implemented",
        "sub": -80,
        "dec": {
            "o": "accepted",
            "by": "elena",
            "d": -72,
            "sc": [4, 2, 5],
            "r": "Clear, measurable saving with a small change surface and credible estimate.",
            "own": "tomas",
            "h": 40,
        },
    },
    {
        "k": "flaky",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "M",
        "tags": ["testing", "ci-cd", "automation"],
        "t": "Quarantine bot for flaky tests",
        "p": "Three flaky suites fail intermittently and get re-run by hand, costing roughly an hour a day.",
        "s": "A bot that quarantines flaky tests with an owner and expiry, still running them without blocking merges.",
        "b": "Every engineer who merges code and release managers chasing red builds.",
        "m": "Re-runs per week from ~45 to under 10; no quarantined test older than 30 days.",
        "st": "under_review",
        "sub": -11,
    },
    {
        "k": "staging",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "M",
        "tags": ["cost", "automation"],
        "t": "Auto-sleep staging environments outside working hours",
        "p": "Eleven staging environments run around the clock but are used about 45 hours a week, costing about $9,000 a month.",
        "s": "Sleep staging outside working hours with one-click wake-up in chat.",
        "b": "Platform team and finance; developers who need fast wake-ups.",
        "m": "Staging cloud cost down 50%; wake-up under 4 minutes.",
        "st": "prototype",
        "sub": -50,
        "dec": {
            "o": "accepted",
            "by": "elena",
            "d": -44,
            "sc": [4, 2, 4],
            "r": "Quick win with clear owner. Cost data is solid; prototype will measure wake-up risk.",
            "own": "tomas",
            "h": 30,
        },
    },
    {
        "k": "designtoken",
        "c": "tech",
        "a": "priya",
        "co": [],
        "eff": "M",
        "tags": ["design-system", "testing"],
        "t": "Design-token linter for the component library",
        "p": "Colour and spacing values drift from design tokens; last quarter we found 140 hard-coded values.",
        "s": "A linter that flags hard-coded colours and spacing and suggests matching tokens in CI.",
        "b": "Designers and front-end engineers, and customers who see inconsistent screens.",
        "m": "Hard-coded values from 140 to under 20 in two sprints.",
        "st": "needs_info",
        "sub": -10,
        "ni": {
            "by": "elena",
            "d": -6,
            "q": "Which token formats and repositories would the linter cover first, and who owns the rule set after the pilot?",
        },
    },
    {
        "k": "traceviewer",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "L",
        "tags": ["observability", "agents", "support"],
        "t": "Trace viewer for agent runs in the admin console",
        "p": "When an agent run misbehaves, support asks an engineer to read raw logs. Diagnosing a run takes about 40 minutes.",
        "s": "Add a trace viewer showing each step, inputs and tool calls with a shareable link.",
        "b": "Support and solutions engineers, and customers waiting on investigations.",
        "m": "Median time to diagnose under 10 minutes; fewer than 5 engineering escalations per month.",
        "st": "under_review",
        "sub": -2,
    },
    {
        "k": "secrets",
        "c": "tech",
        "a": "elena",
        "co": [],
        "eff": "S",
        "tags": ["security", "ci-cd"],
        "t": "Secrets scanning in pre-commit hooks",
        "p": "Two API keys were committed last year and found only by chance. Rotating each cost about two days.",
        "s": "Install a secrets scanner as pre-commit and CI check with an allow-list for fixtures.",
        "b": "All engineers; the security team that audits incidents.",
        "m": "Zero committed secrets reaching main; scan under 10 seconds per commit.",
        "st": "implemented",
        "sub": -120,
        "dec": {
            "o": "accepted",
            "by": "sam",
            "d": -110,
            "sc": [4, 1, 5],
            "r": "Cheap, proven control with clear security value. Security owns the rule set.",
            "own": "tomas",
            "h": 20,
        },
    },
    {
        "k": "sdkgen",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "L",
        "tags": ["integrations", "automation", "docs"],
        "t": "Typed SDK generation from the workflow schema",
        "p": "Teams hand-write API clients and get request shapes wrong. Support sees about eight integration tickets a month.",
        "s": "Generate typed SDKs (TypeScript and Python) from the workflow schema on every release.",
        "b": "Customers building on workflows, solutions engineers, and platform.",
        "m": "Client-error tickets from 8 to 2 per month; first successful call under 30 minutes.",
        "st": "under_review",
        "sub": -5,
    },
    {
        "k": "loadtest",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "L",
        "tags": ["performance", "testing"],
        "t": "Self-serve load-test sandbox for service teams",
        "p": "Service teams cannot load-test before launch because the shared performance environment needs a two-week booking.",
        "s": "A self-serve sandbox that spins up a production-shaped environment for four hours with automatic teardown.",
        "b": "Service teams shipping new endpoints and the platform booking process.",
        "m": "Load tests before 80% of launches; booking requests down to zero.",
        "st": "parked",
        "sub": -60,
        "dec": {
            "o": "parked",
            "by": "elena",
            "d": -52,
            "sc": [3, 4, 4],
            "r": "Valuable but depends on the new cluster budget. Revisit once the infrastructure plan is final rather than start half funded.",
            "rev": -5,
        },
    },
    {
        "k": "cronfleet",
        "c": "tech",
        "a": "marcus",
        "co": [],
        "eff": "XL",
        "tags": ["automation", "observability"],
        "t": "Replace the cron fleet with a scheduler service",
        "p": "About 70 cron jobs run on three shared servers with no central view of failures.",
        "s": "Replace the cron fleet with a managed scheduler that gives every job retries, alerts and an owner.",
        "b": "Platform and finance operations teams.",
        "m": "All jobs with an owner and an alert; no silent failures in a quarter.",
        "st": "declined",
        "sub": -75,
        "dec": {
            "o": "declined",
            "by": "elena",
            "d": -62,
            "sc": [3, 5, 3],
            "r": "The problem is real, but a full replacement is a very large migration for a small number of failures.",
            "cm": "A proposal that starts with alerts for the top 15 jobs would be reviewed again.",
        },
    },
    {
        "k": "quote",
        "c": "business",
        "a": "dana",
        "co": [],
        "eff": "M",
        "tags": ["pricing", "sales-enablement"],
        "t": "Usage-based quote calculator for sales",
        "p": "Sales reps build usage-based quotes in personal spreadsheets, so two reps quoting the same customer can differ by 15 percent.",
        "s": "A shared quote calculator that applies published usage tiers and exports a CRM-ready quote.",
        "b": "Account executives, sales engineers, and finance who re-check every quote.",
        "m": "Quote turnaround from 2 days to 4 hours; zero quotes needing finance corrections.",
        "st": "under_review",
        "sub": -9,
    },
    {
        "k": "renewal",
        "c": "business",
        "a": "dana",
        "co": [],
        "eff": "L",
        "tags": ["analytics", "customer-feedback"],
        "t": "Renewal-risk score in the CRM",
        "p": "Account managers learn about at-risk renewals when the customer says they are leaving.",
        "s": "Compute a renewal-risk score from usage, support sentiment and contract data in the CRM.",
        "b": "Account managers, CSMs, and leadership forecasting renewals.",
        "m": "At-risk accounts identified 60 days before renewal for 80% of churned accounts.",
        "st": "accepted",
        "sub": -22,
        "dec": {
            "o": "accepted",
            "by": "sam",
            "d": -9,
            "sc": [5, 4, 5],
            "r": "Strongest revenue case in this quarter's queue. Data sources exist; needs an engineering owner.",
            "own": None,
            "h": 80,
            "awaiting": True,
        },
    },
    {
        "k": "handoff",
        "c": "process",
        "a": "priya",
        "co": ["tomas"],
        "eff": "S",
        "tags": ["meetings", "onboarding"],
        "t": "Structured handoff checklist between design and engineering",
        "p": "Design-to-engineering handoffs miss acceptance criteria about half the time, causing rework mid-sprint.",
        "s": "A short checklist attached to every design ticket covering criteria, tokens and edge cases.",
        "b": "Designers and engineers on product squads.",
        "m": "Rework tickets from handoff gaps down 50% in a quarter.",
        "st": "submitted",
        "sub": -1,
    },
    {
        "k": "officehours",
        "c": "process",
        "a": "sam",
        "co": [],
        "eff": "S",
        "tags": ["meetings", "knowledge-base"],
        "t": "Weekly platform office hours with recorded answers",
        "p": "The same platform questions are asked in Slack every week and answers disappear in scrollback.",
        "s": "A standing weekly office hour with answers logged into a searchable FAQ.",
        "b": "Engineers asking platform questions and the platform team answering them.",
        "m": "Repeat Slack questions down 40%; FAQ covers top 20 topics.",
        "st": "draft",
        "sub": 0,
    },
    {
        "k": "agentbrief",
        "c": "innovation",
        "a": "elena",
        "co": ["marcus"],
        "eff": "M",
        "tags": ["agents", "templates"],
        "t": "Agent brief template for new internal copilots",
        "p": "Teams spinning up internal agents reinvent prompts and evals, so quality varies widely.",
        "s": "A shared brief template covering goal, tools, eval set and guardrails for every new agent.",
        "b": "Teams building internal agents and the AI platform group.",
        "m": "All new agents ship with an eval set; mean time to first useful run under a week.",
        "st": "under_review",
        "sub": -4,
    },
    {
        "k": "partner",
        "c": "business",
        "a": "dana",
        "co": [],
        "eff": "M",
        "tags": ["partners", "sales-enablement"],
        "t": "Partner co-marketing playbook",
        "p": "Partners run co-marketing campaigns ad hoc; each asks for different assets. Campaigns take seven weeks to launch.",
        "s": "A playbook with reusable assets, launch checklist and joint-metrics template.",
        "b": "Partner managers and marketing ops.",
        "m": "Campaign launch time from 7 weeks to under 3.",
        "st": "merged",
        "sub": -40,
        "dec": {
            "o": "merged",
            "by": "sam",
            "d": -30,
            "sc": [3, 2, 3],
            "r": "Overlaps heavily with the quote calculator enablement work; merge authors onto that thread instead of running two similar enablement tracks.",
            "tgt": "quote",
        },
    },
    {
        "k": "retrobot",
        "c": "process",
        "a": "tomas",
        "co": [],
        "eff": "M",
        "tags": ["meetings", "automation"],
        "t": "Retro action tracker bot",
        "p": "Retro action items live in slides and are forgotten within two sprints.",
        "s": "A bot that opens tickets from retro notes and nags owners before the next retro.",
        "b": "Squad leads and anyone assigned a retro action.",
        "m": "80% of retro actions closed or explicitly deferred before the next retro.",
        "st": "withdrawn",
        "sub": -15,
        "withdraw": "Author withdrew to focus on delivery ownership for accepted ideas.",
    },
    {
        "k": "a11y",
        "c": "tech",
        "a": "priya",
        "co": [],
        "eff": "M",
        "tags": ["accessibility", "design-system"],
        "t": "Automated accessibility checks in the design system CI",
        "p": "Accessibility regressions reach production because checks are manual and inconsistent across squads.",
        "s": "Run axe-core (or equivalent) in design-system CI and fail on serious violations.",
        "b": "Front-end engineers, designers, and customers using assistive tech.",
        "m": "Serious a11y violations on main reduced to zero within a quarter.",
        "st": "under_review",
        "sub": -7,
    },
]


def _roles_for(primary: str, extra: list[str]) -> list[str]:
    roles = ["contributor"]
    if primary not in roles:
        roles.append(primary)
    for r in extra:
        if r not in roles:
            roles.append(r)
    # Keep contributor first-ish but unique
    ordered = []
    for r in ["contributor", "reviewer", "lead", "leadership", "admin"]:
        if r in roles and r not in ordered:
            ordered.append(r)
    return ordered


async def seed_demo(session: AsyncSession) -> dict[str, Any]:
    """Seed spine demo data. Returns maps of slug → UUID for Phase 2+3 seeds."""
    existing = await session.execute(
        select(User).where(User.email == "priya@dotkonnekt.example")
    )
    if existing.scalar_one_or_none():
        logger.info("Demo seed already present — skipping")
        users = (
            await session.execute(select(User))
        ).scalars().all()
        ideas = (
            await session.execute(select(Idea))
        ).scalars().all()
        return {
            "user_ids": {u.slug: u.id for u in users},
            "idea_ids": {i.slug: i.id for i in ideas if i.slug},
            "skipped": True,
        }

    now = datetime.now(UTC)
    password_hash = hash_password(settings.SEED_PASSWORD)

    team_ids: dict[str, uuid.UUID] = {}
    for slug, name in TEAMS:
        team = Team(id=uuid.uuid4(), slug=slug, name=name)
        session.add(team)
        team_ids[slug] = team.id
    await session.flush()

    user_ids: dict[str, uuid.UUID] = {}
    user_rows: dict[str, User] = {}
    for i, (slug, name, title, team_slug, primary, extra) in enumerate(USERS):
        user = User(
            id=uuid.uuid4(),
            email=f"{slug}@dotkonnekt.example",
            password_hash=password_hash,
            has_password=True,
            name=name,
            title=title,
            team_id=team_ids[team_slug],
            roles=_roles_for(primary, extra),
            primary_role=primary,
            status="active",
            avatar=(i % 8) + 1,
            slug=slug,
        )
        session.add(user)
        user_ids[slug] = user.id
        user_rows[slug] = user
    await session.flush()

    # Team leads
    for team in (
        await session.execute(select(Team))
    ).scalars().all():
        if team.slug == "team_plat":
            team.lead_id = user_ids["tomas"]
        elif team.slug == "team_des":
            team.lead_id = user_ids["dana"]
        elif team.slug == "team_ops":
            team.lead_id = user_ids["sam"]

    cat_ids: dict[str, uuid.UUID] = {}
    for slug, label, color, desc in CATEGORIES:
        cat = Category(
            id=uuid.uuid4(),
            slug=slug,
            label=label,
            color=color,
            description=desc,
            enabled=True,
        )
        session.add(cat)
        cat_ids[slug] = cat.id
    await session.flush()

    idea_ids: dict[str, uuid.UUID] = {}
    idea_rows: dict[str, Idea] = {}

    for spec in IDEAS:
        author = user_ids[spec["a"]]
        co = [str(user_ids[c]) for c in spec.get("co", []) if c in user_ids]
        sub_offset = int(spec.get("sub", 0))
        submitted_at = now + timedelta(days=sub_offset) if spec["st"] != "draft" else None
        idea = Idea(
            id=uuid.uuid4(),
            slug=spec["k"],
            title=spec["t"],
            category_id=cat_ids[spec["c"]],
            problem=spec["p"],
            solution=spec["s"],
            beneficiaries=spec["b"],
            effort=spec["eff"],
            success_metrics=spec["m"],
            tags=list(spec.get("tags", [])),
            author_id=author,
            co_author_ids=co,
            status=spec["st"],
            is_draft=spec["st"] == "draft",
            submitted_at=submitted_at,
            due_at=(submitted_at + timedelta(days=10)) if submitted_at else None,
            pickup_due_at=(submitted_at + timedelta(days=3)) if submitted_at else None,
            stage_entered_at=submitted_at or now,
            created_at=submitted_at or now,
            updated_at=now,
        )
        if spec["st"] == "needs_info" and "ni" in spec:
            idea.needs_info_question = spec["ni"]["q"]
            idea.paused_at = now + timedelta(days=spec["ni"]["d"])
            idea.picked_up_at = submitted_at + timedelta(days=1) if submitted_at else None
            idea.reviewer_id = user_ids.get(spec["ni"]["by"])
        if spec["st"] == "withdrawn":
            idea.withdraw_reason = spec.get("withdraw", "")
        if spec["st"] in {"under_review", "accepted", "prototype", "implemented", "parked", "declined", "merged"} and submitted_at:
            idea.picked_up_at = submitted_at + timedelta(days=1)

        session.add(idea)
        await session.flush()
        idea_ids[spec["k"]] = idea.id
        idea_rows[spec["k"]] = idea

        # History trail
        hist_at = submitted_at or now
        session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status=None,
                to_status="draft",
                actor_id=author,
                at=hist_at - timedelta(days=1),
                reason="",
            )
        )
        if spec["st"] != "draft":
            session.add(
                StatusHistory(
                    idea_id=idea.id,
                    from_status="draft",
                    to_status="submitted",
                    actor_id=author,
                    at=hist_at,
                    reason="",
                )
            )
            session.add(
                StatusHistory(
                    idea_id=idea.id,
                    from_status="submitted",
                    to_status="under_review",
                    actor_id=None,
                    at=hist_at + timedelta(seconds=1),
                    reason="Routed to category panel",
                )
            )

        dec = spec.get("dec")
        if dec:
            decider = user_ids[dec["by"]]
            dec_at = now + timedelta(days=dec["d"])
            outcome = dec["o"]
            sc = dec.get("sc")
            owner_id = user_ids.get(dec["own"]) if dec.get("own") else None
            target_id = idea_ids.get(dec["tgt"]) if dec.get("tgt") else None
            if outcome == "merged" and target_id is None:
                # target may be created later — resolve after loop
                pass
            session.add(
                StatusHistory(
                    idea_id=idea.id,
                    from_status="under_review",
                    to_status=outcome if outcome != "needs_info" else "needs_info",
                    actor_id=decider,
                    at=dec_at,
                    reason=dec["r"],
                )
            )
            if sc:
                session.add(
                    Review(
                        idea_id=idea.id,
                        reviewer_id=decider,
                        impact=sc[0],
                        effort=sc[1],
                        alignment=sc[2],
                        comment="",
                    )
                )
            idea.reviewer_id = decider
            if outcome == "accepted":
                idea.owner_id = owner_id
                idea.awaiting_owner = bool(dec.get("awaiting") or not owner_id)
                idea.hours_recommended = dec.get("h")
            if outcome == "parked" and dec.get("rev") is not None:
                idea.revisit_at = now + timedelta(days=dec["rev"])
            if outcome == "accepted" and spec["st"] == "prototype":
                idea.owner_id = owner_id
                idea.hours_recommended = dec.get("h")
                session.add(
                    StatusHistory(
                        idea_id=idea.id,
                        from_status="accepted",
                        to_status="prototype",
                        actor_id=owner_id or decider,
                        at=dec_at + timedelta(days=5),
                        reason="Innovation hours granted",
                    )
                )
            if spec["st"] == "implemented":
                idea.owner_id = owner_id or idea.owner_id
                idea.hours_recommended = dec.get("h") or idea.hours_recommended
                session.add(
                    StatusHistory(
                        idea_id=idea.id,
                        from_status="accepted",
                        to_status="prototype",
                        actor_id=owner_id or decider,
                        at=dec_at + timedelta(days=5),
                        reason="Prototype started",
                    )
                )
                session.add(
                    StatusHistory(
                        idea_id=idea.id,
                        from_status="prototype",
                        to_status="implemented",
                        actor_id=owner_id or decider,
                        at=dec_at + timedelta(days=30),
                        reason="Shipped",
                    )
                )
            session.add(
                Decision(
                    idea_id=idea.id,
                    outcome=outcome,
                    reason=dec["r"],
                    decider_id=decider,
                    as_role="reviewer",
                    owner_id=owner_id,
                    awaiting_owner=bool(dec.get("awaiting") or False),
                    hours=dec.get("h"),
                    revisit_at=idea.revisit_at,
                    merged_into_id=None,  # filled below
                    change_mind=dec.get("cm", ""),
                    impact=sc[0] if sc else None,
                    effort=sc[1] if sc else None,
                    alignment=sc[2] if sc else None,
                    created_at=dec_at,
                )
            )

        if spec["st"] == "needs_info" and "ni" in spec:
            ni = spec["ni"]
            session.add(
                StatusHistory(
                    idea_id=idea.id,
                    from_status="under_review",
                    to_status="needs_info",
                    actor_id=user_ids[ni["by"]],
                    at=now + timedelta(days=ni["d"]),
                    reason=ni["q"],
                )
            )
            session.add(
                Decision(
                    idea_id=idea.id,
                    outcome="needs_info",
                    reason=ni["q"],
                    decider_id=user_ids[ni["by"]],
                    as_role="reviewer",
                    question=ni["q"],
                    created_at=now + timedelta(days=ni["d"]),
                )
            )

        if spec["st"] == "withdrawn":
            session.add(
                StatusHistory(
                    idea_id=idea.id,
                    from_status="under_review",
                    to_status="withdrawn",
                    actor_id=author,
                    at=now + timedelta(days=-3),
                    reason=idea.withdraw_reason,
                )
            )
        if spec["st"] == "submitted":
            # leave at submitted — also add under_review? HTML auto-routes.
            # For seed variety keep as submitted briefly then under_review:
            idea.status = "under_review"
            session.add(
                StatusHistory(
                    idea_id=idea.id,
                    from_status="submitted",
                    to_status="under_review",
                    actor_id=None,
                    at=(submitted_at or now) + timedelta(seconds=2),
                    reason="Routed to category panel",
                )
            )

    await session.flush()

    # Resolve merge targets
    for spec in IDEAS:
        dec = spec.get("dec")
        if not dec or dec.get("o") != "merged":
            continue
        tgt_slug = dec.get("tgt")
        if not tgt_slug or tgt_slug not in idea_ids:
            continue
        idea = idea_rows[spec["k"]]
        idea.merged_into_id = idea_ids[tgt_slug]
        result = await session.execute(
            select(Decision).where(
                Decision.idea_id == idea.id, Decision.outcome == "merged"
            )
        )
        decision = result.scalar_one_or_none()
        if decision:
            decision.merged_into_id = idea_ids[tgt_slug]

    await session.commit()
    logger.info(
        "Seeded %d users, %d ideas (password=%s)",
        len(user_ids),
        len(idea_ids),
        settings.SEED_PASSWORD,
    )
    return {"user_ids": user_ids, "idea_ids": idea_ids, "skipped": False}


async def run() -> None:
    """CLI entry: seed spine (+ optional Phase 2+3 if importable)."""
    logging.basicConfig(level=logging.INFO)
    async with AsyncSessionLocal() as session:
        result = await seed_demo(session)
        if result.get("skipped"):
            print("Seed skipped (already present)")
            return
        try:
            from app.seed import seed_delivery, seed_ideathons, seed_recognition

            await seed_recognition(
                session,
                user_ids=result["user_ids"],
                idea_ids=result["idea_ids"],
            )
            await seed_delivery(
                session,
                user_ids=result["user_ids"],
                idea_ids=result["idea_ids"],
            )
            await seed_ideathons(
                session,
                user_ids=result["user_ids"],
                idea_ids=result["idea_ids"],
            )
            await session.commit()
            print("Phase 2+3 seed applied")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phase 2+3 seed skipped: %s", exc)
        try:
            from app.seed.phase456 import seed_phase456

            await seed_phase456()
            print("Phase 4–6 seed applied")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phase 4–6 seed skipped: %s", exc)
        print(
            "Demo users: priya/marcus/elena/tomas/dana/sam @dotkonnekt.example "
            f"/ {settings.SEED_PASSWORD}"
        )


if __name__ == "__main__":
    asyncio.run(run())
