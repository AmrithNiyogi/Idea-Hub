"""arXiv Atom API client for the AI Newsletter (public API, no key)."""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

from app.constants.news_constants import (
    ARXIV_API_URL,
    ARXIV_REQUEST_GAP_SECONDS,
    ARXIV_STORY_FETCH,
    ARXIV_SUMMARY_MAX_CHARS,
    ARXIV_TOPICS,
    NEWS_HTTP_TIMEOUT,
    NEWS_MAX_AGE,
    NEWS_USER_AGENT,
)

_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "o": "http://a9.com/-/spec/opensearch/1.1/",
    "x": "http://arxiv.org/schemas/atom",
}
_VERSION_SUFFIX = re.compile(r"v\d+$")
_SPACES = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    return _SPACES.sub(" ", text or "").strip()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _authors_line(authors: list[str]) -> str:
    if not authors:
        return ""
    return authors[0] if len(authors) == 1 else f"{authors[0]} et al."


def parse_feed(xml_text: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse an arXiv Atom response into ``(total_results, papers)``.

    Args:
        xml_text: Raw Atom XML from the arXiv API.

    Returns:
        Total match count and one dict per entry (title, abstract, url,
        published, authors, primary_category).

    Raises:
        ValueError: If the response is not valid XML.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"arXiv response was not valid XML: {exc}") from exc
    total = int(root.findtext("o:totalResults", default="0", namespaces=_NS))
    papers: list[dict[str, Any]] = []
    for entry in root.findall("a:entry", _NS):
        raw_url = _clean(entry.findtext("a:id", namespaces=_NS))
        primary = entry.find("x:primary_category", _NS)
        papers.append(
            {
                "title": _clean(entry.findtext("a:title", namespaces=_NS)),
                "abstract": _clean(entry.findtext("a:summary", namespaces=_NS)),
                "url": _VERSION_SUFFIX.sub(
                    "", raw_url.replace("http://", "https://", 1)
                ),
                "published": _clean(entry.findtext("a:published", namespaces=_NS)),
                "authors": [
                    _clean(a.findtext("a:name", namespaces=_NS))
                    for a in entry.findall("a:author", _NS)
                ],
                "primary_category": (
                    primary.get("term", "") if primary is not None else ""
                ),
            }
        )
    return total, papers


async def _query(search_query: str, max_results: int) -> str:
    async with httpx.AsyncClient(
        timeout=NEWS_HTTP_TIMEOUT, headers={"User-Agent": NEWS_USER_AGENT}
    ) as client:
        resp = await client.get(
            ARXIV_API_URL,
            params={
                "search_query": search_query,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
        )
        resp.raise_for_status()
        return resp.text


async def fetch_papers_digest() -> dict[str, Any]:
    """Return the newest AI papers in the newsletter digest shape."""
    query = " OR ".join(f"cat:{cat}" for cat, _ in ARXIV_TOPICS)
    _, papers = parse_feed(await _query(query, ARXIV_STORY_FETCH))
    ai_categories = {cat for cat, _ in ARXIV_TOPICS}
    items = []
    for paper in papers:
        # Cross-listed physics or maths papers are not AI news.
        if paper["primary_category"] not in ai_categories:
            continue
        byline = _authors_line(paper["authors"])
        abstract = _truncate(paper["abstract"], ARXIV_SUMMARY_MAX_CHARS)
        items.append(
            {
                "title": paper["title"],
                "summary": f"{byline} — {abstract}" if byline else abstract,
                "why_it_matters": "",
                "source_name": f"arXiv · {paper['primary_category']}".strip(" ·"),
                "url": paper["url"],
                "published_at": paper["published"],
                "ai_relevance": 1.0,
            }
        )
    cats = ", ".join(cat for cat, _ in ARXIV_TOPICS)
    return {
        "brief": (
            f"The newest AI papers submitted to arXiv across {cats}. "
            "Listed newest first; not ranked by importance."
        ),
        "items": items,
    }


async def fetch_topic_counts(now: datetime) -> list[dict[str, Any]]:
    """Papers submitted in the last 7 days per AI topic, with the newest paper.

    Papers cross-listed in several categories count in each of them.

    Args:
        now: Reference time; the window is the 7 days before it.

    Returns:
        One row per topic: label, count, latest_title, latest_url.
    """
    start = (now - NEWS_MAX_AGE).astimezone(timezone.utc).strftime("%Y%m%d%H%M")
    end = now.astimezone(timezone.utc).strftime("%Y%m%d%H%M")
    rows: list[dict[str, Any]] = []
    for index, (cat, label) in enumerate(ARXIV_TOPICS):
        if index:
            await asyncio.sleep(ARXIV_REQUEST_GAP_SECONDS)
        total, papers = parse_feed(
            await _query(f"cat:{cat} AND submittedDate:[{start} TO {end}]", 1)
        )
        latest = papers[0] if papers else None
        rows.append(
            {
                "label": label,
                "count": total,
                "latest_title": latest["title"] if latest else "",
                "latest_url": latest["url"] if latest else "",
            }
        )
    return rows
