"""Problem radar metoo + leadership meta (Phase 6).

Clusters are computed on read from idea problem/tags; only engagement
(metoo) and leadership annotations (rename, sponsor, acknowledge) persist.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ProblemMeToo(Base):
    """User mark that they share a recurring problem cluster."""

    __tablename__ = "problem_me_too"
    __table_args__ = (
        UniqueConstraint("cluster_key", "user_id", name="uq_problem_me_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    cluster_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProblemMeta(Base):
    """Leadership annotations on a problem cluster."""

    __tablename__ = "problem_meta"

    cluster_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    custom_label: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    sponsor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
