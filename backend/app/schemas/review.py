"""Pydantic schemas for the review queue and decisions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewScoresIn(BaseModel):
    """Save draft scores while an idea is in review."""

    impact: int | None = Field(default=None, ge=1, le=5)
    effort: int | None = Field(default=None, ge=1, le=5)
    alignment: int | None = Field(default=None, ge=1, le=5)
    comment: str = ""


class DecideRequest(BaseModel):
    """Record a review decision.

    ``decision`` values: accept | park | merge | decline | info
    """

    decision: str = Field(..., pattern=r"^(accept|park|merge|decline|info)$")
    reason: str = Field(..., min_length=20, max_length=4000)
    impact: int | None = Field(default=None, ge=1, le=5)
    effort: int | None = Field(default=None, ge=1, le=5)
    alignment: int | None = Field(default=None, ge=1, le=5)
    comment: str = ""
    owner_id: UUID | None = None
    awaiting_owner: bool = False
    hours: int | None = Field(default=None, ge=1, le=400)
    revisit_at: datetime | None = None
    target_id: UUID | None = None
    change_mind: str = ""


class DecisionOut(BaseModel):
    """Persisted decision."""

    id: UUID
    idea_id: UUID
    outcome: str
    reason: str
    decider_id: UUID
    as_role: str
    owner_id: UUID | None = None
    awaiting_owner: bool = False
    hours: int | None = None
    revisit_at: datetime | None = None
    merged_into_id: UUID | None = None
    change_mind: str = ""
    question: str = ""
    impact: int | None = None
    effort: int | None = None
    alignment: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewQueueItem(BaseModel):
    """Queue row sorted by SLA urgency."""

    idea_id: UUID
    title: str
    status: str
    category_id: UUID | None
    author_id: UUID
    submitted_at: datetime | None
    due_at: datetime | None
    pickup_due_at: datetime | None
    picked_up_at: datetime | None
    reviewer_id: UUID | None
    days_until_due: float | None = None
