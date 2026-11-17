"""Seed badge catalog + sample ledger rows.

Call from spine seed after users/ideas exist::

    from app.seed.recognition import seed_recognition
    await seed_recognition(session, user_ids=..., idea_ids=...)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.recognition_rules import BADGE_DEFS, REC_RULES
from app.models.recognition import Badge, BadgeAward, PointsLedgerEntry
from app.repositories.recognition_repository import RecognitionRepository


async def seed_recognition(
    session: AsyncSession,
    *,
    user_ids: Mapping[str, uuid.UUID],
    idea_ids: Optional[Mapping[str, uuid.UUID]] = None,
) -> dict:
    """Ensure badges exist and add a few demo ledger rows / awards.

    Args:
        session: Async SQLAlchemy session.
        user_ids: Map of demo handle → user UUID (e.g. priya, marcus, elena…).
        idea_ids: Optional map of idea keys → UUIDs for ledger idea_id refs.

    Returns:
        Counts of rows touched.
    """
    repo = RecognitionRepository(session)
    await repo.ensure_badges(list(BADGE_DEFS))

    idea_ids = idea_ids or {}
    now = datetime.now(timezone.utc)
    created = 0

    samples: list[tuple[str, str, str, Optional[str]]] = [
        ("priya", "submit", "Submitted complete idea", "gallery"),
        ("priya", "accepted", "Idea accepted", "gallery"),
        ("marcus", "helpful", "Comment marked helpful", "gallery"),
        ("elena", "ontime_review", "On-time review decision", "gallery"),
        ("tomas", "prototype", "Prototype started", "embeddings"),
        ("tomas", "implemented", "Idea implemented", "embeddings"),
    ]
    for handle, rule_id, note, idea_key in samples:
        uid = user_ids.get(handle)
        if not uid or rule_id not in REC_RULES:
            continue
        iid = idea_ids.get(idea_key) if idea_key else None
        dedupe = f"{rule_id}|{uid}|{iid or ''}|seed"
        if await repo.find_by_dedupe(dedupe):
            continue
        session.add(
            PointsLedgerEntry(
                dedupe_key=dedupe,
                user_id=uid,
                rule_id=rule_id,
                points=int(REC_RULES[rule_id]["points"]),
                idea_id=iid,
                note=note,
                escrow=False,
                created_at=now,
            )
        )
        created += 1

    # Demo badges
    if "elena" in user_ids:
        await repo.award_badge(
            BadgeAward(
                user_id=user_ids["elena"],
                badge_id="sharp_reviewer",
                note="Seed demo",
            )
        )
    if "tomas" in user_ids:
        await repo.award_badge(
            BadgeAward(
                user_id=user_ids["tomas"],
                badge_id="closer",
                idea_id=idea_ids.get("embeddings"),
                note="Seed demo",
            )
        )

    await session.flush()
    return {"ledger_rows": created, "badges": len(BADGE_DEFS)}
