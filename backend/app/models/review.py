"""Review score and decision ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Review(Base):
    """Per-reviewer impact/effort/alignment scores on an idea."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "idea_id", "reviewer_id", name="uq_reviews_idea_reviewer"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    impact: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    effort: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alignment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Decision(Base):
    """Recorded review outcome with mandatory reason and optional extras."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    as_role: Mapped[str] = mapped_column(String(32), nullable=False, default="reviewer")
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    awaiting_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    revisit_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    merged_into_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ideas.id"), nullable=True
    )
    change_mind: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")
    impact: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    effort: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alignment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
