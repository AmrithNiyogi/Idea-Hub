"""Insights response schemas (Phase 4)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ParticipationOut(BaseModel):
    """Participation roll-up over a period."""

    days: int
    active: int
    total: int
    pct: int
    prev_active: int = 0
    by_team: list[dict[str, Any]] = Field(default_factory=list)
    buckets: list[dict[str, Any]] = Field(default_factory=list)


class FunnelOut(BaseModel):
    days: int
    counts: list[int]
    stages: list[str]
    conversions: list[dict[str, Any]]
    accepted: int = 0
    accepted_impl: int = 0


class ReviewSpeedOut(BaseModel):
    days: int
    timeline_days: int
    overdue_total: int
    rows: list[dict[str, Any]]
    bottleneck: Optional[dict[str, Any]] = None


class ThemesOut(BaseModel):
    days: int
    tags: list[dict[str, Any]]
    themes: list[dict[str, Any]]
    cur_n: int
    prev_n: int


class ImpactOut(BaseModel):
    days: int
    period: dict[str, Any]
    all_time: dict[str, Any]


class HoursOut(BaseModel):
    quarterly_hours: int
    remaining: int
    granted: int
    logged: int
    by_idea: list[dict[str, Any]] = Field(default_factory=list)


class RecognitionSummaryOut(BaseModel):
    days: int
    total: int
    rows: int
    dims: dict[str, int]
    by_team: list[dict[str, Any]]


class InsightCardOut(BaseModel):
    id: str
    text: str
    evidence: list[str] = Field(default_factory=list)
    link: Optional[str] = None
    simulated: bool = True


class InsightsDashboardOut(BaseModel):
    """Combined insights payload for the Insights page."""

    days: int
    participation: ParticipationOut
    funnel: FunnelOut
    review: ReviewSpeedOut
    themes: ThemesOut
    impact: ImpactOut
    hours: HoursOut
    recognition: RecognitionSummaryOut
    cards: list[InsightCardOut]
