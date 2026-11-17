"""Problem radar schemas (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProblemIdeaOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    tags: list[str] = Field(default_factory=list)
    submitted_at: Optional[datetime] = None
    anonymous: bool = False


class ProblemOut(BaseModel):
    cluster_key: str
    label: str
    terms: list[str]
    state: str  # solved | in_progress | unsolved
    idea_count: int
    me_too_count: int
    me_too_mine: bool = False
    team_count: int = 0
    ideas: list[ProblemIdeaOut] = Field(default_factory=list)
    sponsor_id: Optional[uuid.UUID] = None
    acknowledged_at: Optional[datetime] = None
    custom_label: str = ""
    note: str = ""


class ProblemHeadlineOut(BaseModel):
    recurring: int
    unsolved: int
    again_30: int = 0


class ProblemMetaIn(BaseModel):
    custom_label: Optional[str] = None
    sponsor_id: Optional[uuid.UUID] = None
    acknowledge: Optional[bool] = None
    note: Optional[str] = None


class MeTooOut(BaseModel):
    cluster_key: str
    me_too_count: int
    me_too_mine: bool
