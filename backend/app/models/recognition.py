"""Recognition ledger, badges, and awards (Phase 3).

Responsibilities:
- Append-only points ledger rows citing a named rule.
- Badge definitions + per-user awards.
- Idea of the Quarter / Annual award confirmations.

Escrow: anonymous-idea points set ``escrow=True`` and are excluded from
public totals until the author reveals/claims (spine idea.anonymous).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PointsLedgerEntry(Base):
    """One immutable points award citing a recognition rule."""

    __tablename__ = "points_ledger"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_points_ledger_dedupe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ref_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    escrow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Badge(Base):
    """Catalog of earnable badges (seeded from BADGE_DEFS)."""

    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    icon: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    rule_text: Mapped[str] = mapped_column(Text, nullable=False, default="")


class BadgeAward(Base):
    """User earned a badge at a point in time."""

    __tablename__ = "badge_awards"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_badge_award"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
    )
    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecognitionAward(Base):
    """Confirmed Idea of the Quarter or Annual Innovation Award."""

    __tablename__ = "recognition_awards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True
    )
    user_ids: Mapped[list[Any]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    nominee_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
