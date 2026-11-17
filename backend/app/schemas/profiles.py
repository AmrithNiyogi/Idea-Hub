"""Pydantic schemas for Profile APIs (Phase 3) — thin views over shared data."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.recognition import BadgeAwardOut, LevelOut, LedgerEntryOut


class ProfileIdeaRef(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    role: str = Field(..., description="author | co_author | owner | contributor")


class ContributionEventOut(BaseModel):
    at: datetime
    role: str
    idea_id: uuid.UUID
    idea_title: str
    extra: str = ""


class ImpactSummaryOut(BaseModel):
    hours_saved: float = 0
    hours_verified: float = 0
    usd_influenced: float = 0
    ideas_credited: int = 0


class ProfileOut(BaseModel):
    user_id: uuid.UUID
    name: Optional[str] = None
    title: Optional[str] = None
    team_id: Optional[uuid.UUID] = None
    roles: list[str] = Field(default_factory=list)
    points: int = 0
    level: LevelOut
    badges: list[BadgeAwardOut] = Field(default_factory=list)
    submitted: list[ProfileIdeaRef] = Field(default_factory=list)
    co_authored: list[ProfileIdeaRef] = Field(default_factory=list)
    implemented: list[ProfileIdeaRef] = Field(default_factory=list)
    impact: ImpactSummaryOut = Field(default_factory=ImpactSummaryOut)
    ledger: list[LedgerEntryOut] = Field(default_factory=list)
    history: list[ContributionEventOut] = Field(default_factory=list)
    dims: dict[str, int] = Field(default_factory=dict)
    is_self: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)
