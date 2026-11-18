"""AI Newsletter live sources (arXiv, GitHub) and insights; no network access."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.constants.news_constants import NEWS_CATEGORIES
from app.services import news_arxiv, news_digest_provider, news_github, news_insights
from app.services.news_service import NewsService, validate_items

ATOM = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults>42</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2611.00001v2</id>
    <title>A  Study of
      Tool Use</title>
    <summary>First line.
      Second line with   spaces.</summary>
    <published>{published}</published>
    <arxiv:primary_category term="cs.LG"/>
    <author><name>Ada Example</name></author>
    <author><name>Bo Sample</name></author>
  </entry>
</feed>"""

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def _atom(published: datetime) -> str:
    return ATOM.format(published=published.strftime("%Y-%m-%dT%H:%M:%SZ"))


def test_parse_feed_cleans_fields() -> None:
    total, papers = news_arxiv.parse_feed(_atom(NOW))
    assert total == 42
    paper = papers[0]
    assert paper["title"] == "A Study of Tool Use"
    assert paper["abstract"] == "First line. Second line with spaces."
    assert paper["url"] == "https://arxiv.org/abs/2611.00001"
    assert paper["authors"] == ["Ada Example", "Bo Sample"]
    assert paper["primary_category"] == "cs.LG"


def test_parse_feed_rejects_invalid_xml() -> None:
    with pytest.raises(ValueError):
        news_arxiv.parse_feed("<not-xml")


@pytest.mark.asyncio
async def test_arxiv_digest_passes_validation() -> None:
    published = datetime.now(timezone.utc) - timedelta(hours=3)
    with patch.object(news_arxiv, "_query", AsyncMock(return_value=_atom(published))):
        digest = await news_arxiv.fetch_papers_digest()
    item = digest["items"][0]
    assert item["summary"].startswith("Ada Example et al. — First line.")
    assert item["source_name"] == "arXiv · cs.LG"
    assert len(validate_items(digest["items"], datetime.now(timezone.utc))) == 1


@pytest.mark.asyncio
async def test_arxiv_digest_skips_non_ai_primary_category() -> None:
    xml = _atom(NOW).replace('term="cs.LG"', 'term="hep-th"')
    with patch.object(news_arxiv, "_query", AsyncMock(return_value=xml)):
        digest = await news_arxiv.fetch_papers_digest()
    assert digest["items"] == []


@pytest.mark.asyncio
async def test_github_copies_under_other_owners_keep_most_starred() -> None:
    async def fake_search(topic: str, since: str) -> list[dict[str, Any]]:
        return [
            _raw_repo(1, 50, full_name="a/Config-Checker"),
            _raw_repo(2, 400, full_name="b/config-checker"),
            _raw_repo(3, 100, full_name="c/other"),
        ]

    with patch.object(news_github, "_search", fake_search):
        repos = await news_github.fetch_recent_repos(datetime.now(timezone.utc))
    assert [r["name"] for r in repos] == ["b/config-checker", "c/other"]


@pytest.mark.asyncio
async def test_arxiv_topic_counts_one_row_per_topic() -> None:
    with (
        patch.object(news_arxiv, "_query", AsyncMock(return_value=_atom(NOW))),
        patch.object(news_arxiv, "ARXIV_REQUEST_GAP_SECONDS", 0),
    ):
        rows = await news_arxiv.fetch_topic_counts(NOW)
    assert len(rows) == len(news_arxiv.ARXIV_TOPICS)
    assert rows[0]["count"] == 42
    assert rows[0]["latest_url"] == "https://arxiv.org/abs/2611.00001"


def _raw_repo(rid: int, stars: int, **kw: Any) -> dict[str, Any]:
    base = {
        "id": rid,
        "full_name": f"org/repo-{rid}",
        "html_url": f"https://github.com/org/repo-{rid}",
        "description": "An agent toolkit",
        "stargazers_count": stars,
        "language": "Python",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    }
    base.update(kw)
    return base


@pytest.mark.asyncio
async def test_github_repos_deduped_sorted_and_mapped() -> None:
    async def fake_search(topic: str, since: str) -> list[dict[str, Any]]:
        return [_raw_repo(1, 50), _raw_repo(2, 900)]

    with patch.object(news_github, "_search", fake_search):
        digest = await news_github.fetch_repos_digest(datetime.now(timezone.utc))
    assert [i["title"] for i in digest["items"]] == ["org/repo-2", "org/repo-1"]
    assert "★ 900 · Python" in digest["items"][0]["summary"]
    assert "org/repo-2" in digest["brief"]
    assert len(validate_items(digest["items"], datetime.now(timezone.utc))) == 2


@pytest.mark.asyncio
async def test_github_no_repos_gives_empty_brief_not_error() -> None:
    with patch.object(news_github, "_search", AsyncMock(return_value=[])):
        digest = await news_github.fetch_repos_digest(NOW)
    assert digest["items"] == []
    assert "No new AI repositories" in digest["brief"]


def test_provider_sources() -> None:
    assert news_digest_provider.source_for("ai-research") == "arxiv"
    assert news_digest_provider.source_for("ai-tools") == "github"
    assert {s for s, _ in NEWS_CATEGORIES if news_digest_provider.source_for(s) == "sample"}


@pytest.mark.asyncio
async def test_provider_routes_live_categories() -> None:
    with (
        patch.object(news_arxiv, "fetch_papers_digest", AsyncMock(return_value={"x": 1})),
        patch.object(news_github, "fetch_repos_digest", AsyncMock(return_value={"y": 2})),
    ):
        assert await news_digest_provider.fetch_digest("ai-research") == {"x": 1}
        assert await news_digest_provider.fetch_digest("ai-tools") == {"y": 2}


def test_top_topics_counts_each_story_once_and_skips_stopwords() -> None:
    texts = [
        "Agents agents agents fail on long tasks",
        "New agents framework for the enterprise",
        "Regulation of the framework",
        "A one-off unique story",
    ]
    topics = {t.topic: t.count for t in news_insights.top_topics(texts)}
    assert topics["agents"] == 2
    assert topics["framework"] == 2
    assert "the" not in topics and "new" not in topics
    assert "unique" not in topics


@pytest.fixture(autouse=True)
def _clear_insight_cache() -> None:
    news_insights._cache.clear()


@pytest.mark.asyncio
async def test_insights_report_failed_section_without_failing() -> None:
    rows = [{"label": "Robotics", "count": 5, "latest_title": "t", "latest_url": "u"}]
    with (
        patch.object(
            news_github, "fetch_recent_repos", AsyncMock(side_effect=httpx.ConnectError("down"))
        ),
        patch.object(news_arxiv, "fetch_topic_counts", AsyncMock(return_value=rows)),
    ):
        out = await news_insights.build_insights(["agents agents", "agents"])
    assert out.unavailable == ["trending_repos"]
    assert out.trending_repos == []
    assert out.paper_topics[0].label == "Robotics"
    assert out.top_topics[0].topic == "agents"


@pytest.mark.asyncio
async def test_insights_are_cached_between_calls() -> None:
    repos = [news_github.to_repo(_raw_repo(1, 10))]
    github = AsyncMock(return_value=repos)
    arxiv = AsyncMock(return_value=[])
    with (
        patch.object(news_github, "fetch_recent_repos", github),
        patch.object(news_arxiv, "fetch_topic_counts", arxiv),
    ):
        first = await news_insights.build_insights([])
        await news_insights.build_insights([])
    assert github.await_count == 1 and arxiv.await_count == 1
    assert first.trending_repos[0].name == "org/repo-1"


@pytest.mark.asyncio
async def test_service_keeps_old_stories_when_source_http_fails() -> None:
    from tests.test_news_service import FakeRepo

    repo = FakeRepo()
    svc = NewsService(AsyncMock())
    svc.repo = repo  # type: ignore[assignment]
    repo.state = SimpleNamespace(
        brief="old", refreshed_at=datetime.now(timezone.utc) - timedelta(hours=9), last_error=None
    )
    repo.items = [
        SimpleNamespace(
            id=uuid.uuid4(), title="kept", summary="", why_it_matters="", source_name="",
            url="https://x.test/k", published_at=NOW,
        )
    ]
    with patch.object(
        news_digest_provider, "fetch_digest", AsyncMock(side_effect=httpx.ConnectError("down"))
    ):
        feed = await svc.refresh("ai-tools")
    assert [i.title for i in feed.items] == ["kept"]
    assert feed.error and feed.source == "github"
