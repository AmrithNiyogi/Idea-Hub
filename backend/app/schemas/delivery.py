"""Pydantic schemas for Delivery APIs (Phase 2)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class HoursRequestCreate(BaseModel):
    hours: int = Field(..., ge=1, le=400, description="Whole hours requested (1–400).")
    justification: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Why these hours are needed.",
        examples=["Need 40h to prototype the embedding cache."],
    )


class HoursDecideRequest(BaseModel):
    approve: bool = Field(..., description="True to grant hours and start prototype.")
    hours: Optional[int] = Field(
        None, ge=1, le=400, description="Granted hours (defaults to requested)."
    )
    reason: str = Field("", max_length=2000, description="Decision reason (required if decline).")
    override: bool = Field(
        False, description="Allow grant when pool remaining is insufficient."
    )


class HoursLogCreate(BaseModel):
    hours: float = Field(..., gt=0, le=80, description="Hours in 0.25 steps.")
    work_date: date = Field(..., description="Date the work was done (YYYY-MM-DD).")
    note: str = Field(..., min_length=3, max_length=200)

    @field_validator("hours")
    @classmethod
    def quarter_steps(cls, v: float) -> float:
        if round(v * 4) != v * 4:
            raise ValueError("Hours must be in steps of 0.25")
        return v


class ContributorAdd(BaseModel):
    user_id: uuid.UUID
    role: str = Field("Builder", examples=["Builder"])


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=2000)
    assignee_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    status: str = Field("not_started")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    status: Optional[str] = None
    blocker: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="not_started | in_progress | blocked | done")
    blocker: str = Field("", max_length=1000)


class DeliveryUpdateCreate(BaseModel):
    body: str = Field(..., min_length=3, max_length=4000)
    task_id: Optional[uuid.UUID] = None


class ImpactEntryIn(BaseModel):
    impact_type: str = Field(..., description="hours_saved | revenue | cost_avoided | other")
    value: float = Field(..., gt=0)
    baseline: float = Field(..., ge=0)
    unit: str = Field("", max_length=40)
    evidence: str = Field(..., min_length=10, max_length=400)
    confidence: str = Field(..., pattern="^(low|medium|high)$")


class CreditShareIn(BaseModel):
    user_id: uuid.UUID
    roles: list[str] = Field(default_factory=list)
    pct: float = Field(..., gt=0, le=100)


class MarkImplementedRequest(BaseModel):
    outcome: str = Field(..., min_length=20, max_length=2000)
    impact: list[ImpactEntryIn] = Field(..., min_length=1)
    shares: list[CreditShareIn] = Field(..., min_length=1)

    @field_validator("shares")
    @classmethod
    def shares_total_100(cls, v: list[CreditShareIn]) -> list[CreditShareIn]:
        total = round(sum(s.pct for s in v), 2)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Shares must total 100% (got {total})")
        return v


class VerifyImpactRequest(BaseModel):
    note: str = Field(..., min_length=10, max_length=300)


# ---- responses ----


class TimeLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    work_date: date
    hours: float
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    title: str
    description: str
    assignee_id: Optional[uuid.UUID]
    due_at: Optional[datetime]
    status: str
    blocker: str
    sort_order: int
    done_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryUpdateOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    body: str
    task_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContributorOut(BaseModel):
    user_id: uuid.UUID
    role: str
    added_at: datetime
    added_by: uuid.UUID

    model_config = {"from_attributes": True}


class ImpactEntryOut(BaseModel):
    id: uuid.UUID
    impact_type: str
    value: float
    unit: str
    baseline: float
    evidence: str
    confidence: str
    created_by: uuid.UUID
    created_at: datetime
    verified_by: Optional[uuid.UUID]
    verified_at: Optional[datetime]
    verify_note: str

    model_config = {"from_attributes": True}


class ShareOut(BaseModel):
    user_id: uuid.UUID
    roles: list[str]
    pct: float

    model_config = {"from_attributes": True}


class HoursRequestOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    requested_by: uuid.UUID
    hours: int
    justification: str
    state: str
    decided_by: Optional[uuid.UUID]
    decided_at: Optional[datetime]
    granted_hours: Optional[int]
    reason: str
    override: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PoolOut(BaseModel):
    period_key: str
    budget_hours: int
    granted_hours: int
    remaining: int


class DeliveryDetailOut(BaseModel):
    idea_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    hours_granted: Optional[int] = None
    hours_logged: float = 0
    started_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None
    outcome: str = ""
    pending_request: Optional[HoursRequestOut] = None
    hour_logs: list[TimeLogOut] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list)
    updates: list[DeliveryUpdateOut] = Field(default_factory=list)
    contributors: list[ContributorOut] = Field(default_factory=list)
    impact: list[ImpactEntryOut] = Field(default_factory=list)
    shares: list[ShareOut] = Field(default_factory=list)
    pool: Optional[PoolOut] = None
