"""Reopen condition schemas (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReopenCondIn(BaseModel):
    type: str
    due_at: Optional[datetime] = None
    n: Optional[int] = None
    idea_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    hours: Optional[int] = None
    mode: Optional[str] = None  # problem | votes
    text: Optional[str] = None


class ReopenSetIn(BaseModel):
    idea_id: uuid.UUID
    decision_id: Optional[uuid.UUID] = None
    rule: str = "any"
    conds: list[ReopenCondIn] = Field(default_factory=list)
    revisit_at: Optional[datetime] = None


class CondEvalOut(BaseModel):
    cond: dict[str, Any]
    label: str
    met: bool
    frac: float
    progress: str
    evidence: str
    impossible: bool = False


class ReopenStateOut(BaseModel):
    idea_id: uuid.UUID
    rule: str
    satisfied: bool
    met: int
    total: int
    close: float
    derived: bool = False
    items: list[CondEvalOut]
    evidence: list[str] = Field(default_factory=list)
    snoozed_until: Optional[datetime] = None
    closed: bool = False


class ReopenProposalOut(BaseModel):
    type: str = "reopen"
    proposal_key: str
    idea_id: uuid.UUID
    idea_title: str
    evidence: list[str]
    state: ReopenStateOut


class MarkManualIn(BaseModel):
    cond_id: str
    note: str = ""


class ReopenDecideIn(BaseModel):
    reason: str = ""
    snooze_days: int = Field(0, ge=0, le=30)
