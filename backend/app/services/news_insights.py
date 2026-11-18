"""AI Newsletter insights: trending repos, weekly paper counts and recurring themes."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional, Sequence

import httpx

from app.constants.news_constants import (
    NEWS_STALE_AFTER,
    NEWS_TOP_TOPICS,
    NEWS_TOPIC_MIN_STORIES,
    NEWS_TOPIC_STOPWORDS,
    NEWS_TRENDING_REPOS,
)
from app.schemas.news import (
    NewsInsightsOut,
    NewsPaperTopicOut,
    NewsRepoOut,
    NewsTopicOut,
)
from app.services import news_arxiv, news_github

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z][a-z0-9\-]{2,}")
_cache: dict[str, tuple[datetime, Any]] = {}
_cache_lock = asyncio.Lock()


def top_topics(texts: Sequence[str]) -> list[NewsTopicOut]:
    """Words that recur across stories, most widespread first.

    Each story counts a word once, so one long story cannot dominate.

    Args:
        texts: One string (title and summary) per story.

    Returns:
        Up to ``NEWS_TOP_TOPICS`` words that appear in at least
        ``NEWS_TOPIC_MIN_STORIES`` stories.
    """
    counts: Counter[str] = Counter()
    for text in texts:
        words = {
            w for w in _WORD.findall(text.lower()) if w not in NEWS_TOPIC_STOPWORDS
        }
        counts.update(words)
    ranked = sorted(
        ((w, n) for w, n in counts.items() if n >= NEWS_TOPIC_MIN_STORIES),
        key=lambda pair: (-pair[1], pair[0]),
    )
    return [NewsTopicOut(topic=w, count=n) for w, n in ranked[:NEWS_TOP_TOPICS]]


async def _cached(
    name: str, now: datetime, loader: Callable[[], Awaitable[Any]]
) -> Optional[Any]:
    """Return a section from cache or load it; ``None`` when the source fails."""
    async with _cache_lock:
        hit = _cache.get(name)
        if hit and now - hit[0] < NEWS_STALE_AFTER:
            return hit[1]
        try:
            value = await loader()
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("News insight %s failed: %s", name, exc)
            return None
        _cache[name] = (now, value)
        return value


async def build_insights(texts: Sequence[str]) -> NewsInsightsOut:
    """Assemble insights; a failing source is reported, not fatal.

    Args:
        texts: Title and summary of every stored story, for the themes list.

    Returns:
        Insights with ``unavailable`` naming any section that could not load.
    """
    now = datetime.now(timezone.utc)
    unavailable: list[str] = []

    repos = await _cached(
        "trending_repos", now, lambda: news_github.fetch_recent_repos(now)
    )
    topics = await _cached(
        "paper_topics", now, lambda: news_arxiv.fetch_topic_counts(now)
    )
    if repos is None:
        unavailable.append("trending_repos")
    if topics is None:
        unavailable.append("paper_topics")

    return NewsInsightsOut(
        trending_repos=[
            NewsRepoOut.model_validate(r)
            for r in (repos or [])[:NEWS_TRENDING_REPOS]
        ],
        paper_topics=[NewsPaperTopicOut(**row) for row in (topics or [])],
        top_topics=top_topics(texts),
        generated_at=now,
        unavailable=unavailable,
    )
