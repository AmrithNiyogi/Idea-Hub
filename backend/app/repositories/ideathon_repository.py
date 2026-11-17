"""Persistence helpers for ideathon campaigns."""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ideathon import (
    AudienceVote,
    Ideathon,
    IdeathonEntry,
    IdeathonHandoff,
    PitchScore,
)


class IdeathonRepository:
    """Repository for ideathons, entries, scores, votes, handoffs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> Sequence[Ideathon]:
        result = await self.session.execute(
            select(Ideathon).order_by(Ideathon.start_at.desc())
        )
        return result.scalars().all()

    async def get(
        self, ideathon_id: uuid.UUID, *, with_children: bool = True
    ) -> Optional[Ideathon]:
        stmt = select(Ideathon).where(Ideathon.id == ideathon_id)
        if with_children:
            stmt = stmt.options(
                selectinload(Ideathon.entries),
                selectinload(Ideathon.pitch_scores),
                selectinload(Ideathon.audience_votes),
                selectinload(Ideathon.handoffs),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, it: Ideathon) -> Ideathon:
        self.session.add(it)
        await self.session.flush()
        return it

    async def entry_for_idea(
        self, idea_id: uuid.UUID
    ) -> Optional[IdeathonEntry]:
        result = await self.session.execute(
            select(IdeathonEntry).where(IdeathonEntry.idea_id == idea_id)
        )
        return result.scalar_one_or_none()

    async def entries_for(
        self, ideathon_id: uuid.UUID
    ) -> Sequence[IdeathonEntry]:
        result = await self.session.execute(
            select(IdeathonEntry).where(IdeathonEntry.ideathon_id == ideathon_id)
        )
        return result.scalars().all()

    async def get_pitch_score(
        self,
        ideathon_id: uuid.UUID,
        idea_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[PitchScore]:
        result = await self.session.execute(
            select(PitchScore).where(
                PitchScore.ideathon_id == ideathon_id,
                PitchScore.idea_id == idea_id,
                PitchScore.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_audience_vote(
        self, ideathon_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[AudienceVote]:
        result = await self.session.execute(
            select(AudienceVote).where(
                AudienceVote.ideathon_id == ideathon_id,
                AudienceVote.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def handoff_exists(
        self, ideathon_id: uuid.UUID, idea_id: uuid.UUID
    ) -> bool:
        result = await self.session.execute(
            select(IdeathonHandoff.id).where(
                IdeathonHandoff.ideathon_id == ideathon_id,
                IdeathonHandoff.idea_id == idea_id,
            )
        )
        return result.scalar_one_or_none() is not None
