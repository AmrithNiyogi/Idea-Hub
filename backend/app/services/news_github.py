"""GitHub repository search client for the AI Newsletter (public REST API)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.constants.news_constants import (
    GITHUB_LOOKBACK,
    GITHUB_PER_TOPIC,
    GITHUB_SEARCH_URL,
    GITHUB_TOPICS,
    NEWS_HTTP_TIMEOUT,
    NEWS_USER_AGENT,
)


def to_repo(raw: dict[str, Any]) -> dict[str, Any]:
    """Reduce a GitHub search result to the fields the newsletter uses."""
    return {
        "id": raw.get("id"),
        "name": str(raw.get("full_name") or ""),
        "url": str(raw.get("html_url") or ""),
        "description": str(raw.get("description") or "").strip(),
        "stars": int(raw.get("stargazers_count") or 0),
        "language": str(raw.get("language") or ""),
        "created_at": str(raw.get("created_at") or ""),
    }


async def _search(topic: str, since: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=NEWS_HTTP_TIMEOUT,
        headers={
            "User-Agent": NEWS_USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    ) as client:
        resp = await client.get(
            GITHUB_SEARCH_URL,
            params={
                "q": f"topic:{topic} created:>{since}",
                "sort": "stars",
                "order": "desc",
                "per_page": GITHUB_PER_TOPIC,
            },
        )
        resp.raise_for_status()
        return list(resp.json().get("items") or [])


async def fetch_recent_repos(now: datetime) -> list[dict[str, Any]]:
    """AI repositories created in the last 7 days, most-starred first.

    Args:
        now: Reference time; the window is the 7 days before it.

    Returns:
        Unique repositories across the configured AI topics.
    """
    since = (now - GITHUB_LOOKBACK).astimezone(timezone.utc).strftime("%Y-%m-%d")
    seen: dict[Any, dict[str, Any]] = {}
    for topic in GITHUB_TOPICS:
        for raw in await _search(topic, since):
            repo = to_repo(raw)
            if repo["url"]:
                seen.setdefault(repo["id"], repo)
    # Copies of one project under different owners (often star-farming) keep
    # only their most-starred repo.
    best: dict[str, dict[str, Any]] = {}
    for repo in seen.values():
        short = repo["name"].rsplit("/", 1)[-1].lower()
        if short not in best or repo["stars"] > best[short]["stars"]:
            best[short] = repo
    return sorted(best.values(), key=lambda r: r["stars"], reverse=True)


async def fetch_repos_digest(now: datetime) -> dict[str, Any]:
    """Return new AI repositories in the newsletter digest shape."""
    repos = await fetch_recent_repos(now)
    items = []
    for repo in repos:
        meta = f"★ {repo['stars']:,}"
        if repo["language"]:
            meta += f" · {repo['language']}"
        desc = repo["description"]
        items.append(
            {
                "title": repo["name"],
                "summary": f"{desc} ({meta})" if desc else meta,
                "why_it_matters": "",
                "source_name": "GitHub",
                "url": repo["url"],
                "published_at": repo["created_at"],
                "ai_relevance": 1.0,
            }
        )
    if repos:
        top = repos[0]
        brief = (
            f"{len(repos)} new open-source AI repositories appeared on GitHub "
            f"this week, ranked by stars. The most-starred is {top['name']} "
            f"(★ {top['stars']:,})."
        )
    else:
        brief = "No new AI repositories were found on GitHub this week."
    return {"brief": brief, "items": items}
