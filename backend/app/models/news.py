"""AI Newsletter stored stories and per-category refresh state."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class NewsItem(Base):
    """One validated story in a newsletter category."""

    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint("category", "url", name="uq_news_item_category_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ai_relevance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class NewsCategoryState(Base):
    """Brief and refresh bookkeeping for a newsletter category."""

    __tablename__ = "news_category_state"

    category: Mapped[str] = mapped_column(String(40), primary_key=True)
    brief: Mapped[str] = mapped_column(Text, nullable=False, default="")
    refreshed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
