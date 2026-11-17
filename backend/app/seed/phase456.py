"""Seed Phase 4–6 defaults: admin settings, panels, problem radar, reopen + collab.

Idempotent. Run after spine + phase23 seeds::

    cd backend && python -m app.seed.phase456
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta, timezone
from datetime import datetime

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.collab import CollabRequest
from app.models.idea import Idea
from app.models.reopen import ReopenConditionSet
from app.models.review import Decision
from app.models.user import User
from app.seed.problems import seed_problems
from app.services.admin_service import AdminService

logger = logging.getLogger("idea_hub.seed.phase456")


async def seed_phase456() -> None:
    async with AsyncSessionLocal() as session:
        admin = AdminService(session)
        await admin.ensure_defaults()
        logger.info("Admin defaults + panels ensured")

        users = {
            u.slug: u
            for u in (await session.execute(select(User))).scalars().all()
            if getattr(u, "slug", None)
        }
        # Fallback by email local-part
        if not users:
            for u in (await session.execute(select(User))).scalars().all():
                key = (u.email or "").split("@")[0]
                users[key] = u

        marcus = users.get("marcus")
        elena = users.get("elena")
        priya = users.get("priya")

        # Recurring problem clusters for Problem radar UI
        radar = await seed_problems(session)
        logger.info("Problem radar seed: %s", radar)

        # Attach reopen conditions to a parked/declined idea if any
        parked = (
            await session.execute(
                select(Idea).where(Idea.status.in_(("parked", "declined"))).limit(3)
            )
        ).scalars().all()
        now = datetime.now(timezone.utc)
        for idea in parked:
            existing = (
                await session.execute(
                    select(ReopenConditionSet).where(
                        ReopenConditionSet.idea_id == idea.id
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue
            dec = (
                await session.execute(
                    select(Decision)
                    .where(Decision.idea_id == idea.id)
                    .order_by(Decision.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            due = idea.revisit_at or (now + timedelta(days=14))
            session.add(
                ReopenConditionSet(
                    idea_id=idea.id,
                    decision_id=dec.id if dec else None,
                    rule="any",
                    conds=[
                        {
                            "id": "cond_0",
                            "type": "date",
                            "due_at": due.isoformat(),
                        },
                        {
                            "id": "cond_1",
                            "type": "demand",
                            "mode": "votes",
                            "n": 5,
                        },
                    ],
                    created_by=elena.id if elena else None,
                )
            )
            if not idea.revisit_at:
                idea.revisit_at = due
            logger.info("Reopen conditions seeded for %s", idea.title[:40])

        # Sample collab request
        if marcus and priya:
            ideas = (
                await session.execute(
                    select(Idea).where(
                        Idea.author_id == priya.id,
                        ~Idea.status.in_(("draft", "withdrawn")),
                    ).limit(1)
                )
            ).scalars().all()
            if ideas:
                idea = ideas[0]
                exists = (
                    await session.execute(
                        select(CollabRequest).where(
                            CollabRequest.idea_id == idea.id,
                            CollabRequest.from_user_id == marcus.id,
                        )
                    )
                ).scalar_one_or_none()
                if not exists:
                    session.add(
                        CollabRequest(
                            idea_id=idea.id,
                            from_user_id=marcus.id,
                            type="build",
                            message="Happy to help build the prototype.",
                            role="Builder",
                            status="pending",
                            source="seed",
                        )
                    )
                    logger.info("Collab request seeded on %s", idea.title[:40])

        await session.commit()
        logger.info("Phase 4–6 seed complete")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_phase456())


if __name__ == "__main__":
    main()
