"""Seed recurring problem-radar ideas (Phase 6).

Problem clusters are computed on read from idea title + problem + tags
(Jaccard ≥ 0.34, size ≥ 2). The spine demo ideas are intentionally diverse
and rarely cluster, so the radar stays empty without this additive seed.

Idempotent by idea slug. Safe to re-run after ``seed_demo`` / ``seed_phase456``::

    cd backend && uv run python -m app.seed.problems
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.idea import Idea, StatusHistory
from app.models.problem import ProblemMeToo, ProblemMeta
from app.models.review import Decision
from app.models.user import User
from app.services.problem_service import ProblemService

logger = logging.getLogger("idea_hub.seed.problems")

# Compact specs tuned so Jaccard(title+problem+tags) ≥ 0.34 within each group.
# Authors map to spine demo users only (no invented accounts).
RADAR_IDEAS: list[dict[str, Any]] = [
    # --- Silent scheduled jobs (unsolved) ---
    {
        "k": "jobalerts",
        "c": "tech",
        "a": "marcus",
        "eff": "S",
        "tags": ["automation", "observability", "scheduled-jobs"],
        "t": "Failure alerts for silent scheduled-job failures",
        "p": (
            "Scheduled jobs fail silently with no alert. Silent scheduled job "
            "failures go unnoticed for days because nobody owns the job or gets "
            "notified when a scheduled job fails silently."
        ),
        "s": (
            "Send a channel alert whenever a scheduled job fails or misses its "
            "finish window, with a link to the last log lines."
        ),
        "b": "Finance analysts and on-call engineers who depend on scheduled jobs.",
        "m": "Failed scheduled jobs noticed within 15 minutes; zero late invoices from silent failures.",
        "st": "declined",
        "sub": -40,
        "dec": {
            "o": "declined",
            "by": "elena",
            "d": -30,
            "sc": [3, 2, 3],
            "r": "An alert for one job treats the symptom. Prefer a platform answer with named owners.",
            "cm": "A platform-wide proposal covering scheduled jobs with named owners.",
        },
    },
    {
        "k": "jobowner",
        "c": "tech",
        "a": "priya",
        "eff": "M",
        "tags": ["automation", "observability", "scheduled-jobs", "docs"],
        "t": "Owner registry for scheduled jobs that fail silently",
        "p": (
            "Scheduled jobs fail silently and have no named owner. When a "
            "scheduled job fails silently nobody notices and nobody knows who "
            "should fix the silent failure."
        ),
        "s": (
            "A registry that lists every scheduled job with an owner and contact "
            "channel, and flags jobs whose owner has left."
        ),
        "b": "On-call engineers, support leads, and finance who depend on the exports.",
        "m": "100% of scheduled jobs with a named owner; find the owner under 5 minutes.",
        "st": "parked",
        "sub": -18,
        "dec": {
            "o": "parked",
            "by": "elena",
            "d": -9,
            "sc": [3, 3, 3],
            "r": "Sound registry, but it depends on where scheduled jobs will run long term.",
            "rev": 14,
        },
    },
    {
        "k": "jobstale",
        "c": "tech",
        "a": "tomas",
        "eff": "S",
        "tags": ["automation", "observability", "scheduled-jobs"],
        "t": "Weekly report of scheduled jobs that fail silently",
        "p": (
            "Scheduled jobs fail silently and dashboards go stale. There is no "
            "owner to alert when a scheduled job fails silently, so silent "
            "failures stay hidden."
        ),
        "s": (
            "A weekly report listing every scheduled job that failed or skipped "
            "a run, sent to the team that depends on its output."
        ),
        "b": "Analysts and data engineers who rely on scheduled jobs for dashboards.",
        "m": "Silent job failures found within a day; stale-dashboard complaints down by half.",
        "st": "declined",
        "sub": -7,
        "dec": {
            "o": "declined",
            "by": "elena",
            "d": -3,
            "sc": [2, 2, 3],
            "r": "Third time this quarter silent scheduled-job failures were raised. Prefer one platform answer.",
            "cm": "Owner registry or platform scheduler is accepted and a report is still needed.",
        },
    },
    # --- Agent template regressions (in progress) ---
    {
        "k": "agentcanary",
        "c": "innovation",
        "a": "elena",
        "eff": "M",
        "tags": ["agents", "testing", "support", "agent-templates"],
        "t": "Canary checks when agent templates regress",
        "p": (
            "Agent template changes break agent behaviour silently. "
            "Customer-facing agent regressions only show up in support tickets "
            "after an agent template change breaks behaviour customers depend on."
        ),
        "s": (
            "Run canary conversations against each customer-facing template after "
            "every change and flag answers that drift from the approved ones."
        ),
        "b": "Customer success, support, and customers who rely on agent templates.",
        "m": "Agent regressions caught before release; regression tickets down from 8 to 2 a month.",
        "st": "accepted",
        "sub": -26,
        "dec": {
            "o": "accepted",
            "by": "sam",
            "d": -15,
            "sc": [4, 3, 5],
            "r": "Customer-visible regressions are expensive; a canary set is small and low risk.",
            "own": "tomas",
            "h": 30,
        },
    },
    {
        "k": "agentdiff",
        "c": "tech",
        "a": "marcus",
        "eff": "M",
        "tags": ["agents", "testing", "observability", "agent-templates"],
        "t": "Behaviour diff after agent template changes",
        "p": (
            "Agent template edits break agent behaviour customers depend on. "
            "After an agent template change, agent regressions surface only "
            "through support tickets because nobody sees the behaviour diff."
        ),
        "s": (
            "After each template edit, replay recorded conversations and show a "
            "side-by-side diff of the answers before and after the change."
        ),
        "b": "Template authors and the support team that triages regressions.",
        "m": "Every template edit ships with a behaviour diff; support-found regressions down 70%.",
        "st": "under_review",
        "sub": -13,
    },
    {
        "k": "agentalert",
        "c": "innovation",
        "a": "dana",
        "eff": "M",
        "tags": ["agents", "support", "testing", "agent-templates"],
        "t": "Alert when agent template changes cause regressions",
        "p": (
            "Agent template or wording changes break agent behaviour. Support "
            "tickets are the only signal for agent regressions after an agent "
            "template change breaks behaviour customers depend on."
        ),
        "s": (
            "Track a simple answer-quality score for each customer-facing agent "
            "and alert the template owner when it drops after a change."
        ),
        "b": "Account teams and customers using agents in production.",
        "m": "Time to notice an agent regression from 9 days to under 1 day.",
        "st": "under_review",
        "sub": -5,
    },
    # --- Temporary access not removed (unsolved) ---
    {
        "k": "vendoracc",
        "c": "process",
        "a": "sam",
        "eff": "M",
        "tags": ["security", "compliance", "automation", "access"],
        "t": "Expire temporary contractor access automatically",
        "p": (
            "Temporary contractor and vendor access is requested by email and "
            "temporary access is rarely removed. Finished contractors keep "
            "temporary access because access removal is manual."
        ),
        "s": (
            "Give every contractor account an end date that matches the contract, "
            "with automatic expiry and a renewal request."
        ),
        "b": "Security and compliance teams, and managers who sponsor contractors.",
        "m": "Zero active accounts for finished contractors at each quarterly audit.",
        "st": "declined",
        "sub": -55,
        "dec": {
            "o": "declined",
            "by": "elena",
            "d": -48,
            "sc": [4, 3, 4],
            "r": "Better handled as part of a broader access-expiry programme, not a one-off contractor tool.",
            "cm": "A shared access-expiry programme ships and contractors still keep access.",
        },
    },
    {
        "k": "offboard",
        "c": "process",
        "a": "priya",
        "eff": "M",
        "tags": ["security", "compliance", "automation", "access"],
        "t": "Remove temporary access for leavers within a day",
        "p": (
            "Temporary access for leavers and contractors is requested by email "
            "and rarely removed. Temporary access stays active for days because "
            "access removal is manual and late."
        ),
        "s": (
            "Trigger an access review from HR when someone leaves or changes "
            "team, and remove unused shared-tool access within one working day."
        ),
        "b": "Security, IT, and the managers of leavers.",
        "m": "Leavers losing all shared-tool access within one working day.",
        "st": "declined",
        "sub": -50,
        "dec": {
            "o": "declined",
            "by": "elena",
            "d": -42,
            "sc": [3, 3, 3],
            "r": "Overlaps with contractor access expiry; keep one owner for temporary access removal.",
            "cm": "Access expiry ships and leavers still keep access for more than a few days.",
        },
    },
    # --- Idle staging / cloud cost (in progress) ---
    {
        "k": "gpuidle",
        "c": "tech",
        "a": "marcus",
        "eff": "S",
        "tags": ["cost", "automation", "staging"],
        "t": "Shut down idle staging and GPU environments",
        "p": (
            "Idle staging environments and GPU test clusters run around the "
            "clock and cost thousands a month. Nobody owns shutting down idle "
            "staging environments outside working hours."
        ),
        "s": (
            "Tag every test cluster with an owner and an expiry, and shut down "
            "any cluster with no activity for four hours."
        ),
        "b": "ML and platform engineers, and finance owning the cloud budget.",
        "m": "Idle cluster spend down 80% within a month.",
        "st": "under_review",
        "sub": -9,
    },
    {
        "k": "stagesleep",
        "c": "tech",
        "a": "tomas",
        "eff": "S",
        "tags": ["cost", "automation", "staging"],
        "t": "Auto-sleep idle staging environments overnight",
        "p": (
            "Idle staging environments run around the clock and cost thousands "
            "a month. Staging environments sit idle outside working hours with "
            "nobody owning auto-sleep of idle staging environments."
        ),
        "s": "Sleep idle staging environments overnight with one-click wake-up in chat.",
        "b": "Platform team and developers who need fast wake-ups.",
        "m": "Staging cloud cost down 50%; wake-up under 4 minutes.",
        "st": "under_review",
        "sub": -4,
    },
    # --- At-risk renewal signals (in progress) ---
    {
        "k": "signals",
        "c": "business",
        "a": "dana",
        "eff": "M",
        "tags": ["analytics", "customer-feedback", "renewals"],
        "t": "One view of at-risk customer renewal signals",
        "p": (
            "At-risk customer renewal signals live in different tools. Account "
            "teams notice at-risk renewals weeks late because customer usage "
            "support and survey signals are scattered."
        ),
        "s": (
            "Combine usage, ticket and survey signals into one customer view "
            "with a simple risk flag and the evidence behind it."
        ),
        "b": "Account managers, customer success, and product managers.",
        "m": "At-risk customers flagged at least 30 days before renewal for 80% of cases.",
        "st": "under_review",
        "sub": -14,
    },
    {
        "k": "riskview",
        "c": "business",
        "a": "sam",
        "eff": "M",
        "tags": ["analytics", "customer-feedback", "renewals"],
        "t": "Shared at-risk renewal signal for account teams",
        "p": (
            "Account teams learn about at-risk renewals late because renewal "
            "risk signals are scattered. At-risk customer renewal signals from "
            "usage and support should be one view."
        ),
        "s": "Publish a shared at-risk renewal signal in the CRM with the evidence behind it.",
        "b": "Account managers and leadership forecasting renewals.",
        "m": "At-risk renewals visible to every account owner at least 45 days out.",
        "st": "under_review",
        "sub": -8,
    },
    # --- Dropped escalations (unsolved) ---
    {
        "k": "escalate",
        "c": "process",
        "a": "priya",
        "eff": "M",
        "tags": ["support", "escalations", "meetings"],
        "t": "Single owner for customer escalations to engineering",
        "p": (
            "Customer escalations bounce between support and engineers with no "
            "clear owner. Dropped customer escalations leave customers waiting "
            "while the right engineer is found."
        ),
        "s": (
            "Name one escalation owner each week and give support a single place "
            "to hand over an escalation with the context attached."
        ),
        "b": "Support engineers, on-call engineers, and customers waiting on an answer.",
        "m": "Median time to first engineer response under 1 hour; zero dropped escalations.",
        "st": "declined",
        "sub": -33,
        "dec": {
            "o": "declined",
            "by": "elena",
            "d": -22,
            "sc": [3, 2, 3],
            "r": "Overlaps with triage and severity work still in review; decide those first.",
            "cm": "Triage and severity are decided and escalations are still dropped.",
        },
    },
    {
        "k": "escalrota",
        "c": "process",
        "a": "marcus",
        "eff": "S",
        "tags": ["support", "escalations", "meetings"],
        "t": "Weekly escalation rota for support to engineering",
        "p": (
            "Customer escalations have no clear owner between support and "
            "engineers. A weekly escalation owner would stop dropped customer "
            "escalations while support finds the right engineer."
        ),
        "s": "Publish a weekly escalation rota and a single intake channel for support.",
        "b": "Support engineers and the engineering rota.",
        "m": "Zero dropped customer escalations in a quarter; first response under 1 hour.",
        "st": "parked",
        "sub": -20,
        "dec": {
            "o": "parked",
            "by": "elena",
            "d": -12,
            "sc": [3, 2, 3],
            "r": "Useful, but wait until the single-owner escalation decision lands.",
            "rev": 21,
        },
    },
]

# Friendly leadership labels keyed by a representative idea slug in the cluster.
META_BY_SLUG: dict[str, str] = {
    "jobalerts": "Silent scheduled-job failures",
    "agentcanary": "Agent template regressions",
    "vendoracc": "Temporary access not removed",
    "gpuidle": "Idle staging and GPU spend",
    "signals": "Scattered at-risk renewal signals",
    "escalate": "Dropped customer escalations",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def seed_problems(session: AsyncSession) -> dict[str, Any]:
    """Insert overlapping radar ideas, then annotate clusters with metoo + labels.

    Args:
        session (AsyncSession): Open DB session (caller commits).

    Returns:
        dict[str, Any]: Counts of ideas created, clusters labelled, and metoo rows.

    Side Effects:
        Inserts ``ideas``, ``status_history``, ``decisions``, ``problem_meta``,
        and ``problem_me_too`` rows. Does not invent users or passwords.
    """
    users = {
        u.slug: u
        for u in (await session.execute(select(User))).scalars().all()
        if getattr(u, "slug", None)
    }
    if not users:
        for u in (await session.execute(select(User))).scalars().all():
            key = (u.email or "").split("@")[0]
            users[key] = u

    cats = {
        c.slug: c
        for c in (await session.execute(select(Category))).scalars().all()
    }
    if not users or not cats:
        logger.warning("Problem radar seed skipped — users or categories missing")
        return {"created": 0, "labelled": 0, "metoo": 0, "skipped": True}

    existing_slugs = {
        slug
        for slug in (
            await session.execute(
                select(Idea.slug).where(Idea.slug.is_not(None))
            )
        ).scalars().all()
        if slug
    }

    now = _now()
    created = 0
    for spec in RADAR_IDEAS:
        if spec["k"] in existing_slugs:
            continue
        author = users.get(spec["a"])
        cat = cats.get(spec["c"])
        if not author or not cat:
            logger.warning(
                "Skip radar idea %s — missing author=%s cat=%s",
                spec["k"],
                spec["a"],
                spec["c"],
            )
            continue

        sub_offset = int(spec.get("sub", -7))
        submitted_at = now + timedelta(days=sub_offset)
        idea = Idea(
            id=uuid.uuid4(),
            slug=spec["k"],
            title=spec["t"],
            category_id=cat.id,
            problem=spec["p"],
            solution=spec["s"],
            beneficiaries=spec["b"],
            effort=spec["eff"],
            success_metrics=spec["m"],
            tags=list(spec.get("tags", [])),
            author_id=author.id,
            co_author_ids=[],
            status=spec["st"],
            is_draft=False,
            submitted_at=submitted_at,
            picked_up_at=submitted_at + timedelta(days=1),
            due_at=submitted_at + timedelta(days=10),
            pickup_due_at=submitted_at + timedelta(days=3),
            stage_entered_at=submitted_at,
            created_at=submitted_at,
            updated_at=now,
        )
        if spec["st"] == "parked" and spec.get("dec", {}).get("rev") is not None:
            idea.revisit_at = now + timedelta(days=int(spec["dec"]["rev"]))
        if spec["st"] == "accepted" and spec.get("dec", {}).get("own"):
            owner = users.get(spec["dec"]["own"])
            if owner:
                idea.owner_id = owner.id
                idea.hours_recommended = spec["dec"].get("h")

        session.add(idea)
        await session.flush()
        created += 1

        session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status=None,
                to_status="draft",
                actor_id=author.id,
                at=submitted_at - timedelta(days=1),
                reason="",
            )
        )
        session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status="draft",
                to_status="submitted",
                actor_id=author.id,
                at=submitted_at,
                reason="",
            )
        )
        session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status="submitted",
                to_status="under_review",
                actor_id=None,
                at=submitted_at + timedelta(seconds=1),
                reason="Routed to category panel",
            )
        )

        dec = spec.get("dec")
        if dec:
            decider = users.get(dec["by"])
            if decider:
                dec_at = now + timedelta(days=dec["d"])
                sc = dec.get("sc")
                owner = users.get(dec["own"]) if dec.get("own") else None
                session.add(
                    StatusHistory(
                        idea_id=idea.id,
                        from_status="under_review",
                        to_status=dec["o"],
                        actor_id=decider.id,
                        at=dec_at,
                        reason=dec["r"],
                    )
                )
                session.add(
                    Decision(
                        idea_id=idea.id,
                        outcome=dec["o"],
                        reason=dec["r"],
                        decider_id=decider.id,
                        as_role="reviewer",
                        owner_id=owner.id if owner else None,
                        awaiting_owner=False,
                        hours=dec.get("h"),
                        revisit_at=idea.revisit_at,
                        change_mind=dec.get("cm", ""),
                        impact=sc[0] if sc else None,
                        effort=sc[1] if sc else None,
                        alignment=sc[2] if sc else None,
                        created_at=dec_at,
                    )
                )
        logger.info("Radar idea seeded: %s", spec["k"])

    await session.flush()

    # Annotate clusters (keys depend on member idea ids).
    svc = ProblemService(session)
    ideas = await svc._ideas()
    clusters = svc._cluster(ideas)
    slug_to_id = {
        i.slug: i.id
        for i in (await session.execute(select(Idea))).scalars().all()
        if i.slug
    }
    labelled = 0
    metoo = 0
    me_users = [u for u in (users.get("marcus"), users.get("priya"), users.get("dana")) if u]

    for cl in clusters:
        members: list[Idea] = cl["ideas"]
        member_slugs = {m.slug for m in members if m.slug}
        key = cl["cluster_key"]

        label = None
        for slug, nice in META_BY_SLUG.items():
            if slug in member_slugs:
                label = nice
                break
        if label:
            row = await session.get(ProblemMeta, key)
            if row is None:
                row = ProblemMeta(cluster_key=key, custom_label=label)
                session.add(row)
                labelled += 1
            elif not row.custom_label:
                row.custom_label = label
                labelled += 1

        for u in me_users:
            exists = (
                await session.execute(
                    select(ProblemMeToo).where(
                        ProblemMeToo.cluster_key == key,
                        ProblemMeToo.user_id == u.id,
                    )
                )
            ).scalar_one_or_none()
            if exists:
                continue
            session.add(ProblemMeToo(cluster_key=key, user_id=u.id))
            metoo += 1

    await session.flush()
    logger.info(
        "Problem radar seed: created=%s clusters=%s labelled=%s metoo=%s",
        created,
        len(clusters),
        labelled,
        metoo,
    )
    return {
        "created": created,
        "clusters": len(clusters),
        "labelled": labelled,
        "metoo": metoo,
        "slugs": sorted(slug_to_id.keys() & {s["k"] for s in RADAR_IDEAS}),
    }


async def seed_problems_standalone() -> None:
    """Run problem-radar seed in its own session and commit."""
    async with AsyncSessionLocal() as session:
        result = await seed_problems(session)
        await session.commit()
        print(f"Problem radar seed: {result}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_problems_standalone())


if __name__ == "__main__":
    main()
