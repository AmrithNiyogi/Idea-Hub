"""Collaboration request + tracker schemas (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CollabCreateIn(BaseModel):
    idea_id: uuid.UUID
    type: str = Field(..., pattern="^(coauthor|build)$")
    message: str = Field("", max_length=1000)
    role: str = Field("", max_length=80)
    hours: Optional[int] = Field(None, ge=1, le=200)
    source: str = ""


class CollabDecideIn(BaseModel):
    accept: bool
    note: str = ""


class CollabRequestOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    from_user_id: uuid.UUID
    type: str
    message: str
    role: str
    hours: Optional[int] = None
    status: str
    source: str
    decided_by: Optional[uuid.UUID] = None
    decided_at: Optional[datetime] = None
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MilestoneCreateIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    owner_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    sort_order: int = 0


class MilestoneUpdateIn(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    blocker: Optional[str] = None
    sort_order: Optional[int] = None


class MilestoneOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    title: str
    status: str
    owner_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    blocker: str
    sort_order: int
    done_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckinCreateIn(BaseModel):
    body: str = Field(..., min_length=2, max_length=2000)
    percent_complete: Optional[float] = Field(None, ge=0, le=100)


class CheckinOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    percent_complete: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrackerOut(BaseModel):
    idea_id: uuid.UUID
    milestones: list[MilestoneOut]
    checkins: list[CheckinOut]
    blocked_count: int = 0
    overdue_count: int = 0
