"""Add demo content to a live database, attributed to the accounts already in it.

Run (the DB URL is read from the environment, never from the repo):

    DB_URL=postgresql+asyncpg://user:pass@host/db uv run python -m app.seed.hosted_content

Optional env:
- NORMAL_EMAIL / NORMAL_PASSWORD: create a normal email+password account if it is missing.
- DRY_RUN=1: run everything, print counts, then roll back.

Adds rows only, with one exception: sets ``owner_id`` to the author on accepted or later
ideas that have no owner, so the delivery views have someone to show. Never deletes.
Re-running skips ideas whose title already exists, groups already linked to an idea,
delivery projects already present, and points already awarded (dedupe keys).

Side Effects:
- Inserts users (only when NORMAL_EMAIL is set), ideas, status history, reviews,
  comments, votes, groups, members, channels and messages. One transaction.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.category import Category
from app.models.engagement import Comment, Vote
from app.models.groups import GroupChannel, GroupMember, GroupMessage, HubGroup
from app.models.idea import Idea, StatusHistory
from app.models.ideathon import AudienceVote, Ideathon, IdeathonEntry, IdeathonHandoff, PitchScore
from app.constants.recognition_rules import REC_RULES
from app.models.delivery import ContributionShare, DeliveryContributor, DeliveryProject, ImpactEntry, TimeLog
from app.models.recognition import PointsLedgerEntry
from app.models.review import Decision, Review
from app.models.user import User
from app.seed.demo import IDEAS
from app.services.auth_service import _unique_slug, hash_password
from app.services.groups_service import DEFAULT_CHANNELS

REVIEWED_STATUSES = {"under_review", "accepted", "parked", "declined", "merged", "prototype", "implemented"}
GROUP_STATUSES = {"under_review", "accepted", "prototype", "implemented"}

COMMENT_BANK = [
    "This matches a problem our team hit last quarter. Happy to share the numbers.",
    "Could we scope the first version to one team before rolling it out?",
    "I'd like to help with the success metrics section.",
    "Who owns this if it gets accepted?",
    "The effort estimate looks low to me. Can someone check it against the backlog?",
    "Strong idea. Linking it to the reopen conditions so it isn't lost if we park it.",
]

GROUP_LINES = [
    "Thanks for taking this on. I've pinned the problem statement in the idea page.",
    "Proposal: we start with a two-week spike before committing hours.",
    "I can own the data side. Who has access to the incident export?",
    "Blocker: we still need sign-off from the platform team on the integration.",
    "Decision logged in #decisions: spike first, review again after two weeks.",
    "Sharing the draft plan here, comments welcome.",
]


def _rng(key: str) -> random.Random:
    """Deterministic per key, so re-runs pick the same people and wording."""
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:12], 16))


def _normalize_url(raw: str) -> tuple[str, dict[str, Any]]:
    """Accept postgresql:// or asyncpg URLs; turn sslmode into asyncpg's ssl flag."""
    parts = urlsplit(raw)
    scheme = "postgresql+asyncpg" if parts.scheme in {"postgresql", "postgres"} else parts.scheme
    query = parse_qs(parts.query)
    connect_args: dict[str, Any] = {}
    if query.get("sslmode", [""])[0] not in {"", "disable"}:
        connect_args["ssl"] = "require"
    clean = urlunsplit((scheme, parts.netloc, parts.path, "", ""))
    return clean, connect_args


async def _active_users(session: AsyncSession) -> list[User]:
    rows = await session.execute(select(User).where(User.status == "active").order_by(User.created_at))
    return list(rows.scalars().all())


async def _ensure_normal_user(session: AsyncSession, email: str, password: str) -> None:
    email = email.strip().lower()
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        return
    session.add(
        User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(password),
            has_password=True,
            name=email.split("@", 1)[0],
            title="",
            team_id=None,
            roles=["contributor"],
            primary_role="contributor",
            status="active",
            avatar=1,
            slug=await _unique_slug(session, email.split("@", 1)[0]),
        )
    )
    await session.flush()


async def seed_content(session: AsyncSession) -> dict[str, int]:
    """Create ideas, reviews, comments, votes and groups across the existing accounts."""
    counts = {"ideas": 0, "reviews": 0, "comments": 0, "votes": 0, "groups": 0, "messages": 0, "ideathons": 0, "delivery": 0, "points": 0, "contributors": 0}
    users = await _active_users(session)
    if len(users) < 2:
        raise SystemExit("Need at least two active users in the database.")
    reviewers = [u for u in users if "reviewer" in (u.roles or []) or "admin" in (u.roles or [])]
    categories = {c.slug: c for c in (await session.execute(select(Category).where(Category.enabled.is_(True)))).scalars()}
    if not categories:
        raise SystemExit("No enabled categories. Load categories before seeding content.")
    fallback_cat = next(iter(categories.values()))
    now = datetime.now(UTC)
    taken_titles = set((await session.execute(select(Idea.title))).scalars().all())

    for n, spec in enumerate(IDEAS):
        if spec["t"] in taken_titles:
            continue
        rng = _rng(spec["k"])
        author = users[n % len(users)]
        others = [u for u in users if u.id != author.id]
        co_authors = rng.sample(others, k=min(len(others), rng.choice([0, 0, 1, 2])))
        submitted_at = now + timedelta(days=int(spec.get("sub", 0))) if spec["st"] != "draft" else None
        slug = spec["k"]
        if (await session.execute(select(Idea.id).where(Idea.slug == slug))).first():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        idea = Idea(
            id=uuid.uuid4(),
            slug=slug,
            title=spec["t"],
            category_id=(categories.get(spec["c"]) or fallback_cat).id,
            problem=spec["p"],
            solution=spec["s"],
            beneficiaries=spec["b"],
            effort=spec["eff"],
            success_metrics=spec["m"],
            tags=list(spec.get("tags", [])),
            author_id=author.id,
            co_author_ids=[str(u.id) for u in co_authors],
            status=spec["st"],
            is_draft=spec["st"] == "draft",
            submitted_at=submitted_at,
            due_at=(submitted_at + timedelta(days=10)) if submitted_at else None,
            pickup_due_at=(submitted_at + timedelta(days=3)) if submitted_at else None,
            stage_entered_at=submitted_at or now,
            created_at=submitted_at or now,
            updated_at=now,
        )
        session.add(idea)
        await session.flush()
        counts["ideas"] += 1

        session.add(StatusHistory(idea_id=idea.id, from_status=None, to_status="draft", actor_id=author.id,
                                  at=(submitted_at or now) - timedelta(days=1), reason=""))
        if submitted_at:
            session.add(StatusHistory(idea_id=idea.id, from_status="draft", to_status="submitted",
                                      actor_id=author.id, at=submitted_at, reason=""))
            session.add(StatusHistory(idea_id=idea.id, from_status="submitted", to_status="under_review",
                                      actor_id=None, at=submitted_at + timedelta(seconds=1),
                                      reason="Routed to category panel"))

        decision = spec.get("dec")
        if decision and reviewers and spec["st"] in REVIEWED_STATUSES:
            reviewer = rng.choice(reviewers)
            idea.reviewer_id = reviewer.id
            session.add(StatusHistory(idea_id=idea.id, from_status="under_review", to_status=decision["o"],
                                      actor_id=reviewer.id, at=now + timedelta(days=int(decision.get("d", 0))),
                                      reason=decision["r"]))
            decided_at = now + timedelta(days=int(decision.get("d", 0)))
            session.add(Decision(
                idea_id=idea.id, outcome=decision["o"], reason=decision["r"], decider_id=reviewer.id,
                as_role="reviewer", owner_id=None, awaiting_owner=False, hours=None, revisit_at=None,
                merged_into_id=None, change_mind="", question="",
                impact=decision["sc"][0] if decision.get("sc") else None,
                effort=decision["sc"][1] if decision.get("sc") else None,
                alignment=decision["sc"][2] if decision.get("sc") else None,
                created_at=decided_at,
            ))
            counts["decisions"] = counts.get("decisions", 0) + 1
            if decision.get("sc"):
                impact, effort, alignment = decision["sc"]
                session.add(Review(idea_id=idea.id, reviewer_id=reviewer.id, impact=impact, effort=effort,
                                   alignment=alignment, comment=""))
                counts["reviews"] += 1

        for text in rng.sample(COMMENT_BANK, k=rng.randint(2, 4)):
            session.add(Comment(id=uuid.uuid4(), idea_id=idea.id, author_id=rng.choice(others).id,
                                body=text, kind="comment", created_at=now))
            counts["comments"] += 1
        for voter in rng.sample(others, k=min(len(others), rng.randint(3, 8))):
            session.add(Vote(id=uuid.uuid4(), idea_id=idea.id, user_id=voter.id, created_at=now))
            counts["votes"] += 1

        if spec["st"] in GROUP_STATUSES:
            await _add_group(session, idea, author, co_authors, reviewers, others, rng, now, counts)

    await session.flush()
    await _add_ideathons(session, users, reviewers, counts, now)
    await _add_delivery_and_points(session, users, counts, now)
    return counts


async def _add_delivery_and_points(session: AsyncSession, users: list[User],
                                   counts: dict[str, int], now: datetime) -> None:
    """Delivery projects, impact and recognition points for ideas past acceptance (leadership view)."""
    ideas = (await session.execute(select(Idea).where(Idea.status.in_(
        ["accepted", "prototype", "implemented"])).order_by(Idea.created_at))).scalars().all()
    existing_keys = set((await session.execute(select(PointsLedgerEntry.dedupe_key))).scalars().all())

    def award(rule: str, user_id: uuid.UUID, idea_id: uuid.UUID | None, ref: str, points: int) -> None:
        key = f"hosted:{rule}:{ref}:{user_id}"
        if key in existing_keys:
            return
        existing_keys.add(key)
        session.add(PointsLedgerEntry(id=uuid.uuid4(), dedupe_key=key, user_id=user_id, rule_id=rule,
                                      points=points, idea_id=idea_id, ref_id=ref, note=REC_RULES.get(rule, {}).get("label", rule),
                                      escrow=False, created_at=now))
        counts["points"] += 1

    submitted = (await session.execute(select(Idea).where(Idea.is_draft.is_(False)))).scalars().all()
    for idea in submitted:
        if idea.status not in {"withdrawn"}:
            award("submit", idea.author_id, idea.id, str(idea.id), REC_RULES["submit"]["points"])
    for idea in ideas:
        author_id = idea.author_id
        if idea.owner_id is None:
            idea.owner_id = author_id
        award("accepted", author_id, idea.id, str(idea.id), REC_RULES["accepted"]["points"])
        if idea.status in {"prototype", "implemented"}:
            award("prototype", author_id, idea.id, str(idea.id), REC_RULES["prototype"]["points"])
        if (await session.execute(select(DeliveryProject.id).where(DeliveryProject.idea_id == idea.id))).first():
            continue
        implemented = idea.status == "implemented"
        rng = _rng(f"delivery:{idea.id}")
        project = DeliveryProject(
            idea_id=idea.id, hours_granted=rng.choice([40, 60, 80]), started_at=now - timedelta(days=20),
            implemented_at=now - timedelta(days=5) if implemented else None,
            outcome=f"Shipped the first version of {idea.title.lower()}." if implemented else "",
            created_at=now, updated_at=now,
        )
        session.add(project)
        await session.flush()
        counts["delivery"] += 1
        session.add(TimeLog(project_id=project.id, user_id=author_id, work_date=(now - timedelta(days=8)).date(),
                            hours=float(rng.choice([6, 8, 10])), note="Build and review"))
        co = [u for u in users if str(u.id) in (idea.co_author_ids or []) ]
        if implemented:
            # Shares must total 100 percent.
            co_pct = 40 // len(co) if co else 0
            shares = [(author_id, 100 - co_pct * len(co))] + [(u.id, co_pct) for u in co]
            for uid, pct in shares:
                session.add(ContributionShare(project_id=project.id, idea_id=idea.id, user_id=uid,
                                              roles=["Owner" if uid == author_id else "Contributor"], pct=pct))
            verifier = next((u for u in users if u.id != author_id), None)
            entry = ImpactEntry(
                project_id=project.id, idea_id=idea.id, impact_type="hours_saved", value=float(rng.choice([20, 35, 50])),
                unit="hours per month", baseline=70.0, evidence="Measured from the team's own tracker, 60 days before and after.",
                confidence="high", created_by=author_id, created_at=now - timedelta(days=6), verify_note="",
            )
            if verifier:
                entry.verified_by = verifier.id
                entry.verified_at = now - timedelta(days=2)
                entry.verify_note = "Checked the figure against the source data."
            session.add(entry)
            await session.flush()
            award("implemented", author_id, idea.id, str(idea.id), REC_RULES["implemented"]["points"])
            if verifier:
                award("impact_verified", author_id, idea.id, str(entry.id), 60)
    await session.flush()
    await _add_contributors(session, counts, now)
    await _backfill_decisions(session, counts)


async def _backfill_decisions(session: AsyncSession, counts: dict[str, int]) -> None:
    """Decision rows for reviewer transitions that have history but no Decision (idempotent)."""
    rows = (await session.execute(select(StatusHistory).where(
        StatusHistory.from_status == "under_review",
        StatusHistory.to_status.in_(["accepted", "parked", "declined", "merged"]),
        StatusHistory.actor_id.is_not(None),
    ))).scalars().all()
    for h in rows:
        exists = await session.execute(select(Decision.id).where(
            Decision.idea_id == h.idea_id, Decision.decider_id == h.actor_id, Decision.outcome == h.to_status))
        if exists.first():
            continue
        review = (await session.execute(select(Review).where(
            Review.idea_id == h.idea_id, Review.reviewer_id == h.actor_id))).scalars().first()
        session.add(Decision(
            idea_id=h.idea_id, outcome=h.to_status, reason=h.reason or "Decision recorded.", decider_id=h.actor_id,
            as_role="reviewer", owner_id=None, awaiting_owner=False, hours=None, revisit_at=None,
            merged_into_id=None, change_mind="", question="",
            impact=review.impact if review else None, effort=review.effort if review else None,
            alignment=review.alignment if review else None, created_at=h.at,
        ))
        counts["decisions"] = counts.get("decisions", 0) + 1
    await session.flush()


async def _add_contributors(session: AsyncSession, counts: dict[str, int], now: datetime) -> None:
    """Contribution history rows (DeliveryContributor) for every delivery project that has none."""
    projects = (await session.execute(select(DeliveryProject))).scalars().all()
    for project in projects:
        if (await session.execute(select(DeliveryContributor.id).where(
                DeliveryContributor.project_id == project.id))).first():
            continue
        idea = await session.get(Idea, project.idea_id)
        if idea is None:
            continue
        owner_id = idea.owner_id or idea.author_id
        added = project.started_at or now
        session.add(DeliveryContributor(project_id=project.id, user_id=owner_id, role="Owner",
                                        added_by=owner_id, added_at=added))
        counts["contributors"] += 1
        for co_id in idea.co_author_ids or []:
            uid = uuid.UUID(str(co_id))
            if uid == owner_id:
                continue
            session.add(DeliveryContributor(project_id=project.id, user_id=uid, role="Builder",
                                            added_by=owner_id, added_at=added + timedelta(days=1)))
            counts["contributors"] += 1
    await session.flush()


# (phase, entries, shortlist size) per ideathon; one ideathon per phase.
IDEATHON_PLAN = [
    ("open", 2, 0),
    ("shortlist", 3, 2),
    ("pitch", 3, 2),
    ("results", 2, 1),
    ("handoff", 2, 1),
]
IDEATHON_TITLES = [
    ("Customers First Challenge", "Delight the customer"),
    ("Agent Efficiency Sprint", "Ship smarter, not harder"),
    ("Engineering Flow Week", "Remove the waiting"),
    ("Trust and Safety Jam", "Make the safe path the easy path"),
    ("Cost Discipline Cup", "Spend less, ship more"),
]
EXCLUDED_IDEA_STATUSES = {"draft", "withdrawn", "declined", "merged"}


async def _add_ideathons(session: AsyncSession, users: list[User], reviewers: list[User],
                         counts: dict[str, int], now: datetime) -> None:
    """One ideathon per phase, built from ideas not yet linked to an ideathon."""
    organisers = [u for u in users if {"admin", "leadership"} & set(u.roles or [])] or users[:1]
    judges = reviewers or users[:2]
    linked = set((await session.execute(select(IdeathonEntry.idea_id))).scalars().all())
    pool = [
        i for i in (await session.execute(select(Idea).order_by(Idea.created_at))).scalars().all()
        if i.status not in EXCLUDED_IDEA_STATUSES and i.id not in linked
    ]
    for n, (phase, n_entries, n_short) in enumerate(IDEATHON_PLAN):
        title, theme = IDEATHON_TITLES[n]
        if (await session.execute(select(Ideathon.id).where(Ideathon.title == title))).first():
            continue
        if len(pool) < n_entries:
            print(f"Skipping ideathon '{title}': not enough unlinked ideas ({len(pool)} left).")
            continue
        entries, pool = pool[:n_entries], pool[n_entries:]
        rng = _rng(title)
        organiser = organisers[n % len(organisers)]
        phases = [p for p, _, _ in IDEATHON_PLAN[: IDEATHON_PLAN.index((phase, n_entries, n_short)) + 1]]
        days_ago = {"open": 40, "shortlist": 25, "pitch": 12, "results": 8, "handoff": 3}
        log = [
            {"phase": p, "at": (now - timedelta(days=days_ago[p])).isoformat(), "by": str(organiser.id)}
            for p in phases
        ]
        shortlist = [e.id for e in entries[:n_short]] if phase != "open" else []
        ideathon = Ideathon(
            id=uuid.uuid4(), title=title, theme=theme, kind="ideathon",
            challenges=[f"How might we {theme.lower()} for our teams in the next quarter?"],
            sponsor_id=organiser.id, organiser_id=organiser.id,
            start_at=now - timedelta(days=45), end_at=now + timedelta(days=14),
            phase=phase, phase_log=log, shortlist=shortlist,
            shortlist_edited=False, winner_override=False, winners=[],
            shortlisted_at=now - timedelta(days=days_ago["shortlist"]) if shortlist else None,
            created_at=now - timedelta(days=45),
        )
        if phase in {"results", "handoff"}:
            ideathon.voting_closed_at = now - timedelta(days=days_ago["results"] + 1)
            ideathon.winners = [shortlist[0]]
            ideathon.results_at = now - timedelta(days=days_ago["results"])
            ideathon.confirmed_by = organiser.id
        session.add(ideathon)
        await session.flush()
        counts["ideathons"] += 1

        for e in entries:
            session.add(IdeathonEntry(ideathon_id=ideathon.id, idea_id=e.id, linked_by=organiser.id,
                                      linked_at=now - timedelta(days=days_ago["open"] - 1)))
        if phase == "pitch":
            for idea_id in shortlist:
                for judge in judges[:2]:
                    session.add(PitchScore(ideathon_id=ideathon.id, idea_id=idea_id, user_id=judge.id,
                                           score=rng.randint(5, 9), created_at=now))
            for voter in rng.sample(users, k=min(len(users), 4)):
                session.add(AudienceVote(ideathon_id=ideathon.id, idea_id=shortlist[0], user_id=voter.id,
                                         created_at=now))
        if phase == "handoff":
            winner = entries[0]
            session.add(IdeathonHandoff(
                ideathon_id=ideathon.id, idea_id=winner.id, sent_by=organiser.id,
                statement=(f"Problem: {winner.problem}\nSuccess: {winner.success_metrics}\n"
                           f"Handoff from Ideathon: {title}."),
                edited=False, status="Backlog (simulated)", created_at=now - timedelta(days=3),
            ))


async def _add_group(session: AsyncSession, idea: Idea, author: User, co_authors: list[User],
                     reviewers: list[User], others: list[User], rng: random.Random,
                     now: datetime, counts: dict[str, int]) -> None:
    """One chat group per idea: author as admin, co-authors and a reviewer as members."""
    if (await session.execute(select(HubGroup.id).where(HubGroup.idea_id == idea.id))).first():
        return
    group = HubGroup(id=uuid.uuid4(), name=f"{idea.title[:150]} team", description="Linked from idea detail",
                     kind="group", idea_id=idea.id, created_by=author.id, created_at=now, updated_at=now)
    session.add(group)
    await session.flush()
    members = {author.id: "admin"}
    for u in co_authors:
        members[u.id] = "member"
    if reviewers:
        members.setdefault(rng.choice(reviewers).id, "member")
    for u in rng.sample(others, k=min(len(others), 2)):
        members.setdefault(u.id, "member")
    for uid, role in members.items():
        session.add(GroupMember(id=uuid.uuid4(), group_id=group.id, user_id=uid, role=role, joined_at=now))
    counts["groups"] += 1

    channels: dict[str, GroupChannel] = {}
    for slug, name, desc, order in DEFAULT_CHANNELS:
        ch = GroupChannel(id=uuid.uuid4(), group_id=group.id, slug=slug, name=name, description=desc,
                          kind="text", sort_order=order, created_by=author.id)
        session.add(ch)
        channels[slug] = ch
    await session.flush()

    member_ids = list(members)
    for i, line in enumerate(GROUP_LINES):
        session.add(GroupMessage(id=uuid.uuid4(), channel_id=channels["general"].id,
                                 author_id=member_ids[i % len(member_ids)], body=line, message_type="text",
                                 meta={}, created_at=now + timedelta(minutes=i)))
        counts["messages"] += 1


async def run() -> None:
    raw = os.environ.get("DB_URL", "").strip()
    if not raw:
        raise SystemExit("DB_URL is required.")
    url, connect_args = _normalize_url(raw)
    engine = create_async_engine(url, connect_args=connect_args)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    dry = os.environ.get("DRY_RUN") == "1"
    try:
        async with maker() as session:
            email = os.environ.get("NORMAL_EMAIL", "").strip()
            if email:
                await _ensure_normal_user(session, email, os.environ["NORMAL_PASSWORD"])
            counts = await seed_content(session)
            if dry:
                await session.rollback()
                print("DRY RUN, rolled back:", counts)
            else:
                await session.commit()
                print("Committed:", counts)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
