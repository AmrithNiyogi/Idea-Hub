"""Pydantic schemas for Recognition APIs (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class LedgerEntryOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    rule_id: str
    points: int
    idea_id: Optional[uuid.UUID]
    ref_id: Optional[str]
    note: str
    escrow: bool
    claimed_at: Optional[datetime]
    created_at: datetime
    rule_label: Optional[str] = None
    dimension: Optional[str] = None

    model_config = {"from_attributes": True}


class BadgeOut(BaseModel):
    id: str
    name: str
    icon: str
    rule_text: str

    model_config = {"from_attributes": True}


class BadgeAwardOut(BaseModel):
    badge_id: str
    name: str
    icon: str
    awarded_at: datetime
    note: str
    idea_id: Optional[uuid.UUID] = None


class LevelOut(BaseModel):
    id: str
    name: str
    min: int
    points: int
    next_min: Optional[int] = None


class LeaderboardRowOut(BaseModel):
    user_id: uuid.UUID
    points: int
    level_id: str
    level_name: str
    dims: dict[str, int] = Field(default_factory=dict)


class RulesOut(BaseModel):
    rules: dict[str, dict[str, Any]]
    levels: list[dict[str, Any]]
    badges: list[dict[str, str]]
    dims: dict[str, str]


class ConfirmIoqRequest(BaseModel):
    period: str = Field(..., description="e.g. 2026-Q4")
    idea_id: uuid.UUID
    reason: str = Field(..., min_length=20, max_length=2000)


class ConfirmAnnualRequest(BaseModel):
    year: str = Field(..., description="e.g. 2026")
    user_id: uuid.UUID
    reason: str = Field(..., min_length=20, max_length=2000)


class AwardOut(BaseModel):
    id: uuid.UUID
    kind: str
    period: str
    idea_id: Optional[uuid.UUID]
    user_ids: list[uuid.UUID]
    reason: str
    points: int
    confirmed_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class IoqCandidateOut(BaseModel):
    idea_id: uuid.UUID
    title: str
    score: float
    reason: str
