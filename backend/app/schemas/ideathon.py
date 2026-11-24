"""Pydantic schemas for Ideathon APIs (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


EventKind = Literal["ideathon", "hackathon"]


class IdeathonCreate(BaseModel):
    title: str = Field(..., min_length=4, max_length=80)
    theme: str = Field(..., min_length=3, max_length=60)
    kind: EventKind = "ideathon"
    challenges: list[str] = Field(..., min_length=1, max_length=3)
    sponsor_id: uuid.UUID
    start_at: datetime
    end_at: datetime

    @field_validator("challenges")
    @classmethod
    def challenge_lengths(cls, v: list[str]) -> list[str]:
        cleaned = [c.strip() for c in v if c and c.strip()]
        if not cleaned:
            raise ValueError("Write at least one challenge statement")
        for c in cleaned:
            if len(c) < 20 or len(c) > 300:
                raise ValueError("Each challenge needs 20–300 characters")
        return cleaned


class IdeathonUpdate(BaseModel):
    """Partial edit of an ideathon. Omitted (or null) fields are left unchanged."""

    title: Optional[str] = Field(default=None, min_length=4, max_length=80)
    theme: Optional[str] = Field(default=None, min_length=3, max_length=60)
    kind: Optional[EventKind] = None
    challenges: Optional[list[str]] = Field(default=None, min_length=1, max_length=3)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    @field_validator("challenges")
    @classmethod
    def challenge_lengths(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        cleaned = [c.strip() for c in v if c and c.strip()]
        if not cleaned:
            raise ValueError("Write at least one challenge statement")
        for c in cleaned:
            if len(c) < 20 or len(c) > 300:
                raise ValueError("Each challenge needs 20–300 characters")
        return cleaned


class LinkIdeaRequest(BaseModel):
    idea_id: uuid.UUID


class ShortlistApprove(BaseModel):
    idea_ids: list[uuid.UUID] = Field(..., min_length=2, max_length=6)


class MovePitchRequest(BaseModel):
    idea_id: uuid.UUID
    direction: str = Field(..., pattern="^(up|down)$")


class PitchScoreRequest(BaseModel):
    idea_id: uuid.UUID
    score: int = Field(..., ge=1, le=10)


class AudienceVoteRequest(BaseModel):
    idea_id: uuid.UUID


class ConfirmWinnersRequest(BaseModel):
    idea_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=2)


class HandoffRequest(BaseModel):
    idea_id: uuid.UUID
    statement: str = Field(..., min_length=80, max_length=3000)
    edited: bool = False


class IdeathonSummaryOut(BaseModel):
    id: uuid.UUID
    title: str
    theme: str
    kind: str = "ideathon"
    phase: str
    start_at: datetime
    end_at: datetime
    sponsor_id: uuid.UUID
    organiser_id: uuid.UUID
    entry_count: int = 0
    shortlist_count: int = 0
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IdeathonDetailOut(BaseModel):
    id: uuid.UUID
    title: str
    theme: str
    kind: str = "ideathon"
    challenges: list[str]
    phase: str
    phase_log: list[dict[str, Any]]
    start_at: datetime
    end_at: datetime
    sponsor_id: uuid.UUID
    organiser_id: uuid.UUID
    shortlist: list[uuid.UUID]
    shortlisted_at: Optional[datetime]
    shortlist_edited: bool
    voting_closed_at: Optional[datetime]
    winners: list[uuid.UUID]
    results_at: Optional[datetime]
    tally: Optional[list[dict[str, Any]]]
    completed_at: Optional[datetime]
    entry_idea_ids: list[uuid.UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PitchScoreOut(BaseModel):
    idea_id: uuid.UUID
    user_id: uuid.UUID
    score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AudienceVoteOut(BaseModel):
    idea_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class HandoffOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    statement: str
    sent_by: uuid.UUID
    edited: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TallyRowOut(BaseModel):
    idea_id: uuid.UUID
    panel_avg: float
    panel_n: int
    panel_pct: float
    audience_votes: int
    aud_pct: float
    combined: float
