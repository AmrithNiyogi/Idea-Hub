"""Ideathon campaign models (Phase 3).

Responsibilities:
- Persist campaigns, challenge statements, phase log.
- Persist shortlist order, pitch scores, audience votes.
- Persist winners, handoff problem statements.

Ideathon linkage to ideas is stored as ``ideas.ideathon_id`` on the spine
ideas table when present; Phase 3 also keeps ``ideathon_entries`` so the
module works if spine has not yet added that column (dual-write / read).
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Ideathon(Base):
    """Timed innovation campaign with challenge statements and phases."""

    __tablename__ = "ideathons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    theme: Mapped[str] = mapped_column(String(60), nullable=False)
    challenges: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    sponsor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    organiser_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    phase: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )
    phase_log: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    shortlist: Mapped[list[Any]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    shortlisted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shortlist_edited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    voting_closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    winners: Mapped[list[Any]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    results_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    winner_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    tally: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    entries: Mapped[list["IdeathonEntry"]] = relationship(
        back_populates="ideathon", cascade="all, delete-orphan"
    )
    pitch_scores: Mapped[list["PitchScore"]] = relationship(
        back_populates="ideathon", cascade="all, delete-orphan"
    )
    audience_votes: Mapped[list["AudienceVote"]] = relationship(
        back_populates="ideathon", cascade="all, delete-orphan"
    )
    handoffs: Mapped[list["IdeathonHandoff"]] = relationship(
        back_populates="ideathon", cascade="all, delete-orphan"
    )


class IdeathonEntry(Base):
    """Idea linked into an ideathon during the open phase."""

    __tablename__ = "ideathon_entries"
    __table_args__ = (
        UniqueConstraint("idea_id", name="uq_ideathon_entry_idea"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    ideathon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideathons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ideathon: Mapped["Ideathon"] = relationship(back_populates="entries")


class PitchScore(Base):
    """Panel pitch-day score (1–10) for a shortlisted idea."""

    __tablename__ = "pitch_scores"
    __table_args__ = (
        UniqueConstraint(
            "ideathon_id",
            "idea_id",
            "user_id",
            name="uq_pitch_score",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    ideathon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideathons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ideathon: Mapped["Ideathon"] = relationship(back_populates="pitch_scores")


class AudienceVote(Base):
    """One audience vote per user per ideathon (toggleable)."""

    __tablename__ = "audience_votes"
    __table_args__ = (
        UniqueConstraint("ideathon_id", "user_id", name="uq_audience_vote"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    ideathon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideathons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ideathon: Mapped["Ideathon"] = relationship(back_populates="audience_votes")


class IdeathonHandoff(Base):
    """Hackathon backlog handoff statement for a winning idea."""

    __tablename__ = "ideathon_handoffs"
    __table_args__ = (
        UniqueConstraint(
            "ideathon_id",
            "idea_id",
            name="uq_ideathon_handoff",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    ideathon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideathons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    sent_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(60), nullable=False, default="Backlog (simulated)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ideathon: Mapped["Ideathon"] = relationship(back_populates="handoffs")
