"""Response and request schemas for the internal agent routes used by Kompass tools.

These shapes never carry author identity. Anonymous ideas expose only ``is_anonymous``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentIdeaOut(BaseModel):
    id: uuid.UUID
    title: str
    problem: str
    solution: str
    beneficiaries: str
    success_metrics: str
    tags: list[str]
    effort: str
    status: str
    category_slug: Optional[str]
    is_anonymous: bool


class TaxonomyItem(BaseModel):
    slug: str
    label: str
    description: str


class TaxonomyOut(BaseModel):
    categories: list[TaxonomyItem]


class SimilarIn(BaseModel):
    title: str = ""
    problem: str = ""
    tags: list[str] = Field(default_factory=list)
    exclude_idea_ids: list[uuid.UUID] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class SimilarItem(BaseModel):
    idea_id: str
    title: str
    status: str
    similarity: float
    shared_terms: list[str]
    can_join: bool


class SimilarOut(BaseModel):
    items: list[SimilarItem]


class AgentEntryOut(AgentIdeaOut):
    """An ideathon entry as an agent scores it: the idea content plus the human signals."""

    panel_avg: Optional[float]
    panel_n: int
    audience_votes: int


class EntriesOut(BaseModel):
    id: uuid.UUID
    title: str
    theme: str
    challenges: list[str]
    phase: str
    entry_idea_ids: list[uuid.UUID]
    shortlist: list[uuid.UUID]
    entries: list[AgentEntryOut] = Field(default_factory=list)


class ThreadComment(BaseModel):
    body: str
    kind: str
    created_at: datetime


class ThreadReview(BaseModel):
    impact: Optional[int]
    effort: Optional[int]
    alignment: Optional[int]
    comment: str
    created_at: datetime


class ThreadDecision(BaseModel):
    outcome: str
    reason: str
    as_role: str
    created_at: datetime


class ThreadStatus(BaseModel):
    from_status: Optional[str]
    to_status: str
    at: datetime


class ThreadOut(BaseModel):
    """An idea's discussion. Authors, reviewers and deciders are not included."""

    idea_id: uuid.UUID
    comments: list[ThreadComment]
    reviews: list[ThreadReview]
    decisions: list[ThreadDecision]
    status_history: list[ThreadStatus]


class PanelDecisionItem(BaseModel):
    idea_id: uuid.UUID
    idea_title: str
    outcome: str
    reason: str
    as_role: str
    created_at: datetime


class PanelDecisionsOut(BaseModel):
    """A panel's recent decisions. The panel is its category; deciders are not included."""

    panel_id: uuid.UUID
    panel_name: str
    category_slug: Optional[str]
    decisions: list[PanelDecisionItem]
