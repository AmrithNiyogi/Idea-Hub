"""Agent run log and proposal approval gates (Phase 5).

Responsibilities:
- Persist every simulated (or future Kompass) agent run.
- Persist human approve/reject decisions on proposals.

Must never:
- Record accept/park/merge/decline idea decisions.
- Call live Kompass (adapter boundary only).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AgentRun(Base):
    """One agent execution record. Always ``simulated=True`` in MVP."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    engine: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mock-heuristic-v1"
    )
    approval_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    approval_role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    approval_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none"
    )
    # none | pending | approved | rejected
    proposal_key: Mapped[Optional[str]] = mapped_column(
        String(160), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ProposalDecision(Base):
    """Human gate outcome for an agent proposal (keyed by proposal_key)."""

    __tablename__ = "proposal_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    proposal_key: Mapped[str] = mapped_column(
        String(160), nullable=False, unique=True, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    # approved | rejected
    decided_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    snooze_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KompassAnswer(Base):
    """Admin mark that a Kompass open question was answered (local only)."""

    __tablename__ = "kompass_answers"

    question_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    answered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
