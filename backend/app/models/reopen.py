"""Reopen conditions for parked/declined ideas (Phase 6).

Agents may propose reopen when conditions are satisfied; only a reviewer
or admin may approve and move the idea back to under_review.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ReopenConditionSet(Base):
    """Condition set attached to a park/decline decision.

    ``conds`` is a JSON list of condition objects::

        {id, type, ...type-specific fields, met_at?, met_by?, note?}

    Types: date | raised | dependency | capacity | demand | manual
    """

    __tablename__ = "reopen_conditions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    rule: Mapped[str] = mapped_column(String(8), nullable=False, default="any")
    # any | all
    conds: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    close_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
