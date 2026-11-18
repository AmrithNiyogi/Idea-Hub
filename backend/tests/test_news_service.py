"""AI Newsletter: story validation, staleness and refresh behaviour."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.constants.news_constants import NEWS_CATEGORIES, NEWS_MAX_ITEMS
from app.dependencies.phase23_auth import Actor
from app.services import news_digest_provider
from app.services.news_service import NewsService, validate_items

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def _raw(url: str = "https://x.test/a", hours_ago: float = 1, **kw: Any) -> dict[str, Any]:
    base = {
        "title": "A story",
        "summary": "s",
        "why_it_matters": "w",
        "source_name": "Src",
        "url": url,
        "published_at": (NOW - timedelta(hours=hours_ago)).isoformat(),
        "ai_relevance": 0.9,
    }
    base.update(kw)
    return base


class FakeRepo:
    """In-memory stand-in for NewsRepository."""

    def __init__(self) -> None:
        self.state: Any = None
        self.items: list[Any] = []

    async def get_state(self, category: str) -> Any:
        return self.state

    async def list_items(self, category: str) -> list[Any]:
        return self.items

    async def replace_digest(self, category, brief, items, refreshed_at) -> None:
        self.items = [
            SimpleNamespace(id=uuid.uuid4(), **i) for i in items
        ]
        self.state = SimpleNamespace(brief=brief, refreshed_at=refreshed_at, last_error=None)

    async def record_error(self, category: str, message: str) -> None:
        if self.state is None:
            self.state = SimpleNamespace(brief="", refreshed_at=None, last_error=None)
        self.state.last_error = message


def _service(repo: FakeRepo) -> NewsService:
    svc = NewsService(AsyncMock())
    svc.repo = repo  # type: ignore[assignment]
    return svc


def _digest(n: int = 2) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "brief": "b",
        "items": [
            {**_raw(url=f"https://x.test/{i}"), "published_at": (now - timedelta(hours=i + 1)).isoformat()}
            for i in range(n)
        ],
    }


def test_validate_drops_unusable_items() -> None:
    items = [
        _raw(url="https://x.test/ok"),
        _raw(url=""),
        _raw(url="ftp://x.test/f"),
        _raw(url="https://x.test/old", hours_ago=24 * 8),
        _raw(url="https://x.test/future", hours_ago=-2),
        _raw(url="https://x.test/low", ai_relevance=0.2),
        _raw(url="https://x.test/notitle", title=" "),
        _raw(url="https://x.test/badtime", published_at="nope"),
        _raw(url="https://x.test/badrel", ai_relevance="x"),
        "not-a-dict",
    ]
    kept = validate_items(items, NOW)
    assert [k["url"] for k in kept] == ["https://x.test/ok"]


def test_validate_dedupes_sorts_and_caps() -> None:
    items = [_raw(url=f"https://x.test/{i}", hours_ago=i) for i in range(NEWS_MAX_ITEMS + 4)]
    items.append(_raw(url="https://x.test/0", hours_ago=0))
    kept = validate_items(items, NOW)
    assert len(kept) == NEWS_MAX_ITEMS
    assert len({k["url"] for k in kept}) == NEWS_MAX_ITEMS
    times = [k["published_at"] for k in kept]
    assert times == sorted(times, reverse=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "slug", [s for s, _ in NEWS_CATEGORIES if news_digest_provider.source_for(s) == "sample"]
)
async def test_sample_provider_output_passes_validation(slug: str) -> None:
    digest = await news_digest_provider.fetch_digest(slug)
    assert digest["brief"]
    kept = validate_items(digest["items"], datetime.now(timezone.utc))
    assert len(kept) == len(digest["items"]) > 0


@pytest.mark.asyncio
async def test_first_open_fetches_and_stores() -> None:
    repo = FakeRepo()
    feed = await _service(repo).get_feed("ai")
    assert feed.label == "Artificial Intelligence"
    assert feed.items and not feed.stale and feed.error is None


@pytest.mark.asyncio
async def test_fresh_category_is_not_refetched() -> None:
    repo = FakeRepo()
    svc = _service(repo)
    await svc.get_feed("ai")
    with patch.object(news_digest_provider, "fetch_digest", AsyncMock()) as fetch:
        feed = await svc.refresh("ai")
        await svc.get_feed("ai")
    fetch.assert_not_awaited()
    assert not feed.stale


@pytest.mark.asyncio
async def test_stale_category_is_served_then_refreshed() -> None:
    repo = FakeRepo()
    svc = _service(repo)
    await svc.get_feed("ai")
    repo.state.refreshed_at = datetime.now(timezone.utc) - timedelta(hours=7)
    assert (await svc.get_feed("ai")).stale is True
    with patch.object(news_digest_provider, "fetch_digest", AsyncMock(return_value=_digest(3))) as fetch:
        feed = await svc.refresh("ai")
    fetch.assert_awaited_once()
    assert len(feed.items) == 3 and not feed.stale


@pytest.mark.asyncio
async def test_provider_failure_keeps_last_good_stories() -> None:
    repo = FakeRepo()
    svc = _service(repo)
    await svc.get_feed("ai")
    before = len(repo.items)
    repo.state.refreshed_at = datetime.now(timezone.utc) - timedelta(hours=7)
    with patch.object(news_digest_provider, "fetch_digest", AsyncMock(side_effect=RuntimeError("boom"))):
        feed = await svc.refresh("ai")
    assert len(feed.items) == before
    assert feed.stale and feed.error


@pytest.mark.asyncio
async def test_all_items_invalid_keeps_old_and_reports_error() -> None:
    repo = FakeRepo()
    svc = _service(repo)
    await svc.get_feed("ai")
    before = len(repo.items)
    bad = {"brief": "b", "items": [_raw(ai_relevance=0.0)]}
    with patch.object(news_digest_provider, "fetch_digest", AsyncMock(return_value=bad)):
        feed = await svc.refresh("ai", force=True, actor=Actor(id=uuid.uuid4(), roles=["admin"]))
    assert len(feed.items) == before
    assert feed.error


@pytest.mark.asyncio
async def test_force_requires_admin() -> None:
    svc = _service(FakeRepo())
    member = Actor(id=uuid.uuid4(), roles=["contributor"], active_role="contributor")
    with pytest.raises(HTTPException) as exc:
        await svc.refresh("ai", force=True, actor=member)
    assert exc.value.status_code == 403
    admin = Actor(id=uuid.uuid4(), roles=["admin"], active_role="admin")
    feed = await svc.refresh("ai", force=True, actor=admin)
    assert feed.items


@pytest.mark.asyncio
async def test_unknown_category_is_404() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service(FakeRepo()).get_feed("sports")
    assert exc.value.status_code == 404
