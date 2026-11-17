"""Seed ideathon campaigns (past + live pitch-day).

Call after spine users/ideas exist::

    from app.seed.ideathons import seed_ideathons
    await seed_ideathons(session, user_ids=..., idea_ids=...)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ideathon import (
    AudienceVote,
    Ideathon,
    IdeathonEntry,
    IdeathonHandoff,
    PitchScore,
)


async def seed_ideathons(
    session: AsyncSession,
    *,
    user_ids: Mapping[str, uuid.UUID],
    idea_ids: Mapping[str, uuid.UUID],
) -> dict:
    """Create one completed and one live pitch-day ideathon when keys exist."""
    dana = user_ids.get("dana")
    theo = user_ids.get("theo") or dana
    elena = user_ids.get("elena")
    if not dana:
        return {"ideathons": 0}

    now = datetime.now(timezone.utc)
    created = 0

    # Past completed
    past_entries = [
        idea_ids[k]
        for k in ("embeddings", "secrets", "onepagers")
        if k in idea_ids
    ]
    if len(past_entries) >= 2:
        past = Ideathon(
            title="Agent Efficiency Sprint",
            theme="Ship smarter, not harder",
            challenges=[
                "How might we cut redundant model calls without losing answer quality?",
                "How might we keep secrets out of source without slowing developers?",
            ],
            sponsor_id=theo or dana,
            organiser_id=dana,
            start_at=now - timedelta(days=155),
            end_at=now - timedelta(days=70),
            phase="handoff",
            phase_log=[
                {"phase": "open", "at": (now - timedelta(days=155)).isoformat(), "by": str(dana)},
                {"phase": "handoff", "at": (now - timedelta(days=65)).isoformat(), "by": str(dana)},
            ],
            shortlist=past_entries[:3],
            shortlisted_at=now - timedelta(days=70),
            winners=[past_entries[0]],
            results_at=now - timedelta(days=67),
            confirmed_by=dana,
            voting_closed_at=now - timedelta(days=68),
            completed_at=now - timedelta(days=60),
        )
        session.add(past)
        await session.flush()
        for iid in past_entries:
            session.add(
                IdeathonEntry(
                    ideathon_id=past.id,
                    idea_id=iid,
                    linked_by=dana,
                    linked_at=now - timedelta(days=140),
                )
            )
        session.add(
            IdeathonHandoff(
                ideathon_id=past.id,
                idea_id=past_entries[0],
                statement=(
                    "Problem: duplicate embedding calls waste spend and latency.\n"
                    "Build a content-hash cache with hit-rate dashboards and CI rollout.\n"
                    "Success: median suite time down; cache hit rate above 70 percent.\n"
                    "Handoff from Ideathon — Agent Efficiency Sprint."
                ),
                sent_by=dana,
                edited=False,
                created_at=now - timedelta(days=62),
            )
        )
        created += 1

    # Live pitch day
    live_keys = [k for k in ("supportdraft", "runbook", "gallery", "renewal") if k in idea_ids]
    if len(live_keys) >= 2:
        live_ids = [idea_ids[k] for k in live_keys]
        live = Ideathon(
            title="Customers First Challenge",
            theme="Delight the customer",
            challenges=[
                "How might we help new customers reach their first live workflow in days instead of weeks?",
                "How might we answer customers faster without losing the human touch?",
            ],
            sponsor_id=theo or dana,
            organiser_id=dana,
            start_at=now - timedelta(days=45),
            end_at=now - timedelta(days=3),
            phase="pitch",
            phase_log=[
                {"phase": "open", "at": (now - timedelta(days=48)).isoformat(), "by": str(dana)},
                {"phase": "shortlist", "at": (now - timedelta(days=3)).isoformat(), "by": str(dana)},
                {"phase": "pitch", "at": (now - timedelta(days=1)).isoformat(), "by": str(dana)},
            ],
            shortlist=live_ids[:4],
            shortlisted_at=now - timedelta(days=2),
            winners=[],
        )
        session.add(live)
        await session.flush()
        for iid in live_ids:
            session.add(
                IdeathonEntry(
                    ideathon_id=live.id,
                    idea_id=iid,
                    linked_by=dana,
                    linked_at=now - timedelta(days=30),
                )
            )
        if elena:
            for iid in live.shortlist:
                session.add(
                    PitchScore(
                        ideathon_id=live.id,
                        idea_id=iid,
                        user_id=elena,
                        score=7,
                    )
                )
        # Sample audience votes from non-author demo users
        for handle in ("tomas", "marcus", "priya"):
            uid = user_ids.get(handle)
            if not uid or not live.shortlist:
                continue
            session.add(
                AudienceVote(
                    ideathon_id=live.id,
                    idea_id=live.shortlist[0],
                    user_id=uid,
                )
            )
        created += 1

    await session.flush()
    return {"ideathons": created}
