"""Pydantic schemas for ideas, engagement, and explore."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import re

from pydantic import BaseModel, Field, field_validator

GITHUB_REPO_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")


class IdeaWrite(BaseModel):
    """Fields accepted when saving a draft or submitting an idea."""

    title: str = Field(..., min_length=1, max_length=300)
    category_id: UUID | None = None
    problem: str = ""
    solution: str = ""
    beneficiaries: str = ""
    effort: str = Field(default="M", pattern=r"^(S|M|L|XL)$")
    success_metrics: str = ""
    tags: list[str] = Field(default_factory=list)
    anonymous: bool = False
    co_author_ids: list[UUID] = Field(default_factory=list)
    team_name: str | None = Field(default=None, max_length=120)
    github_url: str | None = Field(default=None, max_length=300)

    @field_validator("team_name")
    @classmethod
    def clean_team_name(cls, v: str | None) -> str | None:
        """Blank team names are stored as no team name."""
        cleaned = (v or "").strip()
        return cleaned or None

    @field_validator("github_url")
    @classmethod
    def check_github_url(cls, v: str | None) -> str | None:
        """Accept an empty value or one GitHub repository URL (one per idea)."""
        cleaned = (v or "").strip()
        if not cleaned:
            return None
        if not GITHUB_REPO_URL.match(cleaned):
            raise ValueError("GitHub link must look like https://github.com/owner/repo")
        return cleaned


class IdeaDraftSave(BaseModel):
    """Save or update a draft (title required)."""

    draft_id: UUID | None = None
    data: IdeaWrite


class IdeaSubmitRequest(BaseModel):
    """Submit a new idea or promote an existing draft."""

    draft_id: UUID | None = None
    data: IdeaWrite


class WithdrawRequest(BaseModel):
    """Author withdraw reason."""

    reason: str = Field(default="", max_length=2000)


class AnswerInfoRequest(BaseModel):
    """Author response to a needs_info question."""

    text: str = Field(..., min_length=10, max_length=2000)


class CommentCreate(BaseModel):
    """Post a discussion comment."""

    body: str = Field(..., min_length=1, max_length=2000)


class CommentOut(BaseModel):
    """Comment response."""

    id: UUID
    idea_id: UUID
    author_id: UUID
    body: str
    kind: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusHistoryOut(BaseModel):
    """Status transition row."""

    id: UUID
    from_status: str | None
    to_status: str
    actor_id: UUID | None
    at: datetime
    reason: str

    model_config = {"from_attributes": True}


class IdeaOut(BaseModel):
    """Idea detail / list item."""

    id: UUID
    slug: str | None = None
    title: str
    category_id: UUID | None = None
    problem: str = ""
    solution: str = ""
    beneficiaries: str = ""
    effort: str = "M"
    success_metrics: str = ""
    tags: list[str] = Field(default_factory=list)
    author_id: UUID
    anonymous: bool = False
    co_author_ids: list[UUID] = Field(default_factory=list)
    team_name: str | None = None
    github_url: str | None = None
    owner_id: UUID | None = None
    status: str
    is_draft: bool = False
    reviewer_id: UUID | None = None
    awaiting_owner: bool = False
    hours_recommended: int | None = None
    needs_info_question: str | None = None
    withdraw_reason: str = ""
    merged_into_id: UUID | None = None
    submitted_at: datetime | None = None
    picked_up_at: datetime | None = None
    due_at: datetime | None = None
    pickup_due_at: datetime | None = None
    revisit_at: datetime | None = None
    stage_entered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    vote_count: int = 0
    follow_count: int = 0
    comment_count: int = 0
    voted: bool = False
    following: bool = False
    status_history: list[StatusHistoryOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class IdeaListResponse(BaseModel):
    """Paginated idea list."""

    items: list[IdeaOut]
    total: int


class ToggleResponse(BaseModel):
    """Vote / follow toggle result."""

    active: bool


class HomeAggregates(BaseModel):
    """Home dashboard stage counts and needs-attention hints."""

    status_counts: dict[str, int]
    needs_attention: list[dict]
    total_live: int
