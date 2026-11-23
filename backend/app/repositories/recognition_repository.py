"""Persistence helpers for points ledger, badges, awards."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recognition import (
    Badge,
    BadgeAward,
    PointsLedgerEntry,
    RecognitionAward,
    RecognitionThanks,
)


class RecognitionRepository:
    """Repository for recognition ledger and awards."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_dedupe(
        self, dedupe_key: str
    ) -> Optional[PointsLedgerEntry]:
        result = await self.session.execute(
            select(PointsLedgerEntry).where(
                PointsLedgerEntry.dedupe_key == dedupe_key
            )
        )
        return result.scalar_one_or_none()

    async def add_ledger(
        self, row: PointsLedgerEntry
    ) -> PointsLedgerEntry:
        self.session.add(row)
        await self.session.flush()
        return row

    async def ledger_for_user(
        self,
        user_id: uuid.UUID,
        *,
        include_escrow: bool = False,
        limit: int = 200,
    ) -> Sequence[PointsLedgerEntry]:
        stmt = select(PointsLedgerEntry).where(
            PointsLedgerEntry.user_id == user_id
        )
        if not include_escrow:
            stmt = stmt.where(PointsLedgerEntry.escrow.is_(False))
        stmt = stmt.order_by(PointsLedgerEntry.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def public_points(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(PointsLedgerEntry.points), 0)
            ).where(
                PointsLedgerEntry.user_id == user_id,
                PointsLedgerEntry.escrow.is_(False),
            )
        )
        return int(result.scalar_one())

    async def monthly_rule_count(
        self, user_id: uuid.UUID, rule_id: str, year: int, month: int
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(PointsLedgerEntry)
            .where(
                PointsLedgerEntry.user_id == user_id,
                PointsLedgerEntry.rule_id == rule_id,
                func.extract("year", PointsLedgerEntry.created_at) == year,
                func.extract("month", PointsLedgerEntry.created_at) == month,
            )
        )
        return int(result.scalar_one())

    async def leaderboard(
        self, *, limit: int = 50
    ) -> Sequence[tuple[uuid.UUID, int]]:
        result = await self.session.execute(
            select(
                PointsLedgerEntry.user_id,
                func.sum(PointsLedgerEntry.points).label("pts"),
            )
            .where(PointsLedgerEntry.escrow.is_(False))
            .group_by(PointsLedgerEntry.user_id)
            .order_by(func.sum(PointsLedgerEntry.points).desc())
            .limit(limit)
        )
        return [(row[0], int(row[1])) for row in result.all()]

    async def totals(
        self,
        *,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> dict[uuid.UUID, dict[str, int]]:
        """Non-escrow points per user per rule, optionally within a time window."""
        stmt = (
            select(
                PointsLedgerEntry.user_id,
                PointsLedgerEntry.rule_id,
                func.sum(PointsLedgerEntry.points),
            )
            .where(PointsLedgerEntry.escrow.is_(False))
            .group_by(PointsLedgerEntry.user_id, PointsLedgerEntry.rule_id)
        )
        if since is not None:
            stmt = stmt.where(PointsLedgerEntry.created_at >= since)
        if until is not None:
            stmt = stmt.where(PointsLedgerEntry.created_at < until)
        result = await self.session.execute(stmt)
        out: dict[uuid.UUID, dict[str, int]] = {}
        for user_id, rule_id, pts in result.all():
            out.setdefault(user_id, {})[rule_id] = int(pts)
        return out

    async def thanks_sent_in_month(
        self, from_user_id: uuid.UUID, year: int, month: int
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(RecognitionThanks)
            .where(
                RecognitionThanks.from_user_id == from_user_id,
                func.extract("year", RecognitionThanks.created_at) == year,
                func.extract("month", RecognitionThanks.created_at) == month,
            )
        )
        return int(result.scalar_one())

    async def thanks_between_in_month(
        self, from_user_id: uuid.UUID, to_user_id: uuid.UUID, year: int, month: int
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(RecognitionThanks)
            .where(
                RecognitionThanks.from_user_id == from_user_id,
                RecognitionThanks.to_user_id == to_user_id,
                func.extract("year", RecognitionThanks.created_at) == year,
                func.extract("month", RecognitionThanks.created_at) == month,
            )
        )
        return int(result.scalar_one())

    async def add_thanks(self, row: RecognitionThanks) -> RecognitionThanks:
        self.session.add(row)
        await self.session.flush()
        return row

    async def recent_thanks(self, limit: int) -> Sequence[RecognitionThanks]:
        result = await self.session.execute(
            select(RecognitionThanks)
            .order_by(RecognitionThanks.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def ensure_badges(self, defs: Sequence[dict]) -> None:
        for d in defs:
            existing = await self.session.get(Badge, d["id"])
            if existing:
                continue
            self.session.add(
                Badge(
                    id=d["id"],
                    name=d["name"],
                    icon=d.get("icon", ""),
                    rule_text=d.get("rule", ""),
                )
            )
        await self.session.flush()

    async def awards_for_user(
        self, user_id: uuid.UUID
    ) -> Sequence[BadgeAward]:
        result = await self.session.execute(
            select(BadgeAward)
            .where(BadgeAward.user_id == user_id)
            .order_by(BadgeAward.awarded_at.desc())
        )
        return result.scalars().all()

    async def award_badge(
        self, award: BadgeAward
    ) -> Optional[BadgeAward]:
        existing = await self.session.execute(
            select(BadgeAward).where(
                BadgeAward.user_id == award.user_id,
                BadgeAward.badge_id == award.badge_id,
            )
        )
        if existing.scalar_one_or_none():
            return None
        self.session.add(award)
        await self.session.flush()
        return award

    async def get_award_by_period(
        self, kind: str, period: str
    ) -> Optional[RecognitionAward]:
        result = await self.session.execute(
            select(RecognitionAward).where(
                RecognitionAward.kind == kind,
                RecognitionAward.period == period,
            )
        )
        return result.scalar_one_or_none()

    async def add_award(self, award: RecognitionAward) -> RecognitionAward:
        self.session.add(award)
        await self.session.flush()
        return award

    async def list_awards(self) -> Sequence[RecognitionAward]:
        result = await self.session.execute(
            select(RecognitionAward).order_by(RecognitionAward.created_at.desc())
        )
        return result.scalars().all()

    async def list_badges(self) -> Sequence[Badge]:
        result = await self.session.execute(select(Badge).order_by(Badge.name))
        return result.scalars().all()

    async def release_escrow_for_idea(
        self, idea_id: uuid.UUID, user_id: uuid.UUID, claimed_at
    ) -> tuple[int, int]:
        result = await self.session.execute(
            select(PointsLedgerEntry).where(
                PointsLedgerEntry.idea_id == idea_id,
                PointsLedgerEntry.user_id == user_id,
                PointsLedgerEntry.escrow.is_(True),
            )
        )
        rows = result.scalars().all()
        pts = 0
        for row in rows:
            row.escrow = False
            row.claimed_at = claimed_at
            pts += row.points
        await self.session.flush()
        return pts, len(rows)
