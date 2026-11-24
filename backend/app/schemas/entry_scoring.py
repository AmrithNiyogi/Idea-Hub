"""Schemas for entry documents and saved AI rubric scores."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class EntryDocumentOut(BaseModel):
    """Document metadata. ``text_chars`` is how much readable text the AI can use."""

    id: uuid.UUID
    idea_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    text_chars: int
    created_at: datetime


class CriterionScore(BaseModel):
    """One rubric criterion: a 0-10 score (null when not scorable) and why."""

    score: Optional[float] = None
    rationale: str = ""


class EntryScoreOut(BaseModel):
    """Latest saved AI rubric score for one entry."""

    idea_id: uuid.UUID
    rank: int
    overall: Optional[float] = None
    criteria: dict[str, CriterionScore]
    rationale: str = ""
    engine: str
    simulated: bool
    evidence: dict[str, Any] = Field(default_factory=dict)
    scored_at: datetime


class EntryScoresOut(BaseModel):
    """All saved scores for an event, best first."""

    ideathon_id: uuid.UUID
    rubric_version: str
    items: list[EntryScoreOut] = Field(default_factory=list)
