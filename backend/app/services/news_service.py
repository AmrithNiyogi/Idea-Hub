"""AI Newsletter — stored digests per category, refreshed when stale."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.news_constants import (
    NEWS_CATEGORIES,
    NEWS_CATEGORY_LABELS,
    NEWS_CATEGORY_SOURCES,
    NEWS_DEFAULT_CATEGORY,
    NEWS_MAX_AGE,
    NEWS_MAX_ITEMS,
    NEWS_MIN_AI_RELEVANCE,
    NEWS_STALE_AFTER,
)
from app.dependencies.phase23_auth import Actor
from app.repositories.news_repository import NewsRepository
from app.schemas.news import (
    NewsCategoryOut,
    NewsFeedOut,
    NewsInsightsOut,
    NewsItemOut,
)
from app.services import news_digest_provider, news_insights

logger = logging.getLogger(__name__)

_refresh_locks: dict[str, asyncio.Lock] = {}


def _parse_time(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp into an aware UTC datetime, or None."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def validate_items(raw_items: list[Any], now: datetime) -> list[dict[str, Any]]:
    """Keep only usable stories: URL, recent, AI-relevant, unique; newest first.

    Args:
        raw_items: Items as returned by the digest provider.
        now: Reference time for the age check.

    Returns:
        Cleaned item dicts ready to store, capped at ``NEWS_MAX_ITEMS``.
    """
    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        title = str(raw.get("title") or "").strip()
        published = _parse_time(raw.get("published_at"))
        try:
            relevance = float(raw.get("ai_relevance", 0))
        except (TypeError, ValueError):
            continue
        if not title or not url.lower().startswith(("http://", "https://")):
            continue
        if url in seen or published is None:
            continue
        if published > now or now - published > NEWS_MAX_AGE:
            continue
        if relevance < NEWS_MIN_AI_RELEVANCE:
            continue
        seen.add(url)
        kept.append(
            {
                "title": title[:300],
                "summary": str(raw.get("summary") or "").strip(),
                "why_it_matters": str(raw.get("why_it_matters") or "").strip(),
                "source_name": str(raw.get("source_name") or "").strip()[:120],
                "url": url[:1000],
                "published_at": published,
                "ai_relevance": relevance,
            }
        )
    kept.sort(key=lambda item: item["published_at"], reverse=True)
    return kept[:NEWS_MAX_ITEMS]


class NewsService:
    """Read stored newsletter digests and refresh them from the provider."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = NewsRepository(session)

    @staticmethod
    def list_categories() -> list[NewsCategoryOut]:
        return [NewsCategoryOut(slug=s, label=l) for s, l in NEWS_CATEGORIES]

    @staticmethod
    def _check_category(category: str) -> str:
        if category not in NEWS_CATEGORY_LABELS:
            raise HTTPException(status_code=404, detail="Unknown news category")
        return category

    async def get_insights(self) -> NewsInsightsOut:
        """Trending repos, weekly paper counts and themes across stored stories."""
        items = await self.repo.list_all_items()
        # Titles only, and not repos: descriptions and abstracts are too wordy
        # to find themes in.
        return await news_insights.build_insights(
            [
                i.title
                for i in items
                if NEWS_CATEGORY_SOURCES.get(i.category) != "github"
            ]
        )

    async def get_feed(
        self, category: str = NEWS_DEFAULT_CATEGORY
    ) -> NewsFeedOut:
        """Return stored stories for a category; a never-filled category is fetched first."""
        self._check_category(category)
        state = await self.repo.get_state(category)
        if state is None or state.refreshed_at is None:
            return await self.refresh(category)
        return await self._feed(category)

    async def refresh(
        self, category: str, *, force: bool = False, actor: Optional[Actor] = None
    ) -> NewsFeedOut:
        """Refresh a category if stale (or always when an admin forces it)."""
        self._check_category(category)
        if force and not (actor and actor.has_role("admin")):
            raise HTTPException(status_code=403, detail="Only admins can force a refresh")
        lock = _refresh_locks.setdefault(category, asyncio.Lock())
        async with lock:
            state = await self.repo.get_state(category)
            now = datetime.now(timezone.utc)
            fresh = (
                state is not None
                and state.refreshed_at is not None
                and now - state.refreshed_at < NEWS_STALE_AFTER
            )
            if fresh and not force:
                return await self._feed(category)
            await self._fetch_and_store(category, now)
        return await self._feed(category)

    async def _fetch_and_store(self, category: str, now: datetime) -> None:
        try:
            digest = await news_digest_provider.fetch_digest(category)
            items = validate_items(list(digest["items"]), now)
            brief = str(digest.get("brief") or "")
        except (httpx.HTTPError, KeyError, ValueError, TypeError, RuntimeError) as exc:
            logger.warning("News refresh failed for %s: %s", category, exc)
            await self.repo.record_error(category, "Couldn't refresh this category.")
            return
        if not items:
            await self.repo.record_error(category, "No recent AI stories were returned.")
            return
        await self.repo.replace_digest(category, brief, items, now)

    async def _feed(self, category: str) -> NewsFeedOut:
        state = await self.repo.get_state(category)
        items = await self.repo.list_items(category)
        refreshed_at = state.refreshed_at if state else None
        stale = refreshed_at is None or (
            datetime.now(timezone.utc) - refreshed_at >= NEWS_STALE_AFTER
        )
        return NewsFeedOut(
            category=category,
            label=NEWS_CATEGORY_LABELS[category],
            source=news_digest_provider.source_for(category),
            brief=state.brief if state else "",
            items=[NewsItemOut.model_validate(i) for i in items],
            refreshed_at=refreshed_at,
            stale=stale,
            error=state.last_error if state else None,
        )
