"""AI Newsletter schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsCategoryOut(BaseModel):
    slug: str = Field(description="Category slug used in API calls")
    label: str = Field(description="Display name")


class NewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: str
    why_it_matters: str
    source_name: str
    url: str
    published_at: datetime


class NewsRepoOut(BaseModel):
    name: str
    url: str
    description: str
    stars: int
    language: str


class NewsPaperTopicOut(BaseModel):
    label: str
    count: int = Field(description="Papers submitted in the last 7 days")
    latest_title: str
    latest_url: str


class NewsTopicOut(BaseModel):
    topic: str
    count: int = Field(description="Stories that mention the topic")


class NewsInsightsOut(BaseModel):
    trending_repos: list[NewsRepoOut] = Field(default_factory=list)
    paper_topics: list[NewsPaperTopicOut] = Field(default_factory=list)
    top_topics: list[NewsTopicOut] = Field(default_factory=list)
    generated_at: datetime
    unavailable: list[str] = Field(
        default_factory=list, description="Sections whose source could not be reached"
    )


class NewsFeedOut(BaseModel):
    category: str
    label: str
    source: str = Field(description="sample, arxiv or github")
    brief: str = ""
    items: list[NewsItemOut] = Field(default_factory=list)
    refreshed_at: Optional[datetime] = None
    stale: bool = Field(description="True when stored results are older than the refresh window")
    error: Optional[str] = Field(default=None, description="Last refresh failure, if any")
