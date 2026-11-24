"""Idea and status-history ORM models."""

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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Idea(Base):
    """Core innovation idea row — spine owns the lifecycle.

    Columns ``co_author_ids``, ``anonymous``, and ``ideathon_id`` match the
    contract expected by ``app.services.spine_bridge.SpineBridge``.
    """

    __tablename__ = "ideas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    slug: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True, index=True
    )
    problem: Mapped[str] = mapped_column(Text, nullable=False, default="")
    solution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    beneficiaries: Mapped[str] = mapped_column(Text, nullable=False, default="")
    effort: Mapped[str] = mapped_column(String(8), nullable=False, default="M")
    success_metrics: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    co_author_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    awaiting_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hours_recommended: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    needs_info_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    withdraw_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    merged_into_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ideas.id"), nullable=True
    )
    ideathon_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    team_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    demo_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    ai_review: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pickup_due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revisit_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stage_entered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    status_history: Mapped[list["StatusHistory"]] = relationship(
        "StatusHistory",
        back_populates="idea",
        cascade="all, delete-orphan",
        order_by="StatusHistory.at",
    )


class StatusHistory(Base):
    """Lifecycle transition audit row — source of truth for status changes.

    Column names ``from_status`` / ``to_status`` match ``spine_bridge`` inserts.
    """

    __tablename__ = "status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    idea: Mapped[Idea] = relationship("Idea", back_populates="status_history")
