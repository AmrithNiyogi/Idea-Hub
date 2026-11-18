"""Source of newsletter digests: arXiv, GitHub or placeholder data per category."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.constants.news_constants import NEWS_CATEGORY_SOURCES, NEWS_SOURCE_SAMPLE
from app.constants.news_sample_data import NEWS_SAMPLE_STORIES
from app.services import news_arxiv, news_github


def source_for(category: str) -> str:
    """Return ``arxiv``, ``github`` or ``sample`` for a category slug."""
    return NEWS_CATEGORY_SOURCES.get(category, NEWS_SOURCE_SAMPLE)


def _sample_digest(category: str, now: datetime) -> dict[str, Any]:
    brief, stories = NEWS_SAMPLE_STORIES[category]
    items = [
        {
            "title": title,
            "summary": summary,
            "why_it_matters": why,
            "source_name": source,
            "url": f"https://example.com/ai-news/{category}/{index}",
            "published_at": (now - timedelta(hours=hours_ago)).isoformat(),
            "ai_relevance": 1.0,
        }
        for index, (title, summary, why, source, hours_ago) in enumerate(stories, 1)
    ]
    return {"brief": brief, "items": items}


async def fetch_digest(category: str) -> dict[str, Any]:
    """Return ``{"brief": str, "items": [...]}`` for one category.

    Args:
        category: Category slug from ``NEWS_CATEGORIES``.

    Returns:
        Raw digest in the agent output shape (items still need validation).
    """
    now = datetime.now(timezone.utc)
    source = source_for(category)
    if source == "arxiv":
        return await news_arxiv.fetch_papers_digest()
    if source == "github":
        return await news_github.fetch_repos_digest(now)
    return _sample_digest(category, now)
