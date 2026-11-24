"""Read a public GitHub repository so the scorer can judge what a team actually built.

Responsibilities:
- Fetch repo metadata, languages, README text, file tree and recent commit count.
- Summarise it as evidence (no owner name, so scoring stays blind to who built it).

Side Effects:
- Outbound calls to the public GitHub REST API (no token; 60 requests/hour per server IP).
  A failed call marks the repo ``unreachable`` and never raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.constants.entry_scoring import (
    GITHUB_API_BASE,
    GITHUB_CI_MARKERS,
    GITHUB_HTTP_TIMEOUT,
    GITHUB_README_MAX_CHARS,
    GITHUB_STATUS_MISSING,
    GITHUB_STATUS_OK,
    GITHUB_STATUS_UNREACHABLE,
    GITHUB_TEST_MARKERS,
    GITHUB_USER_AGENT,
)


@dataclass
class RepoSnapshot:
    """What the scorer knows about a repo. ``evidence`` is safe to store and show."""

    status: str
    readme: str = ""
    paths: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


def repo_slug(url: str | None) -> str | None:
    """``owner/repo`` from a validated GitHub URL, or None."""
    text = (url or "").strip().rstrip("/")
    prefix = "https://github.com/"
    if not text.startswith(prefix):
        return None
    parts = text[len(prefix):].split("/")
    if len(parts) != 2 or not all(parts):
        return None
    name = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return f"{parts[0]}/{name}"


def summarise(meta: dict[str, Any], languages: dict[str, Any], readme: str,
              paths: list[str], commits: int) -> dict[str, Any]:
    """Evidence dict for storage and display."""
    lowered = [p.lower() for p in paths]
    return {
        "status": GITHUB_STATUS_OK,
        "full_name": str(meta.get("name") or ""),
        "description": str(meta.get("description") or "").strip(),
        "languages": {str(k): int(v) for k, v in languages.items() if isinstance(v, int)},
        "readme_chars": len(readme),
        "file_count": len(paths),
        "has_tests": any(m in p for p in lowered for m in GITHUB_TEST_MARKERS),
        "has_ci": any(m in p for p in lowered for m in GITHUB_CI_MARKERS),
        "recent_commits": commits,
        "pushed_at": str(meta.get("pushed_at") or ""),
    }


def missing_snapshot() -> RepoSnapshot:
    """No GitHub link on the entry."""
    return RepoSnapshot(status=GITHUB_STATUS_MISSING, evidence={"status": GITHUB_STATUS_MISSING})


def unreachable_snapshot(reason: str) -> RepoSnapshot:
    """Link given but the repo could not be read (private, deleted, rate-limited)."""
    return RepoSnapshot(
        status=GITHUB_STATUS_UNREACHABLE,
        evidence={"status": GITHUB_STATUS_UNREACHABLE, "reason": reason},
    )


async def _get_json(client: httpx.AsyncClient, url: str, **params: Any) -> Any:
    resp = await client.get(url, params=params or None)
    resp.raise_for_status()
    return resp.json()


async def fetch_snapshot(url: str | None) -> RepoSnapshot:
    """Read a public repo. Never raises; failures become an ``unreachable`` snapshot."""
    slug = repo_slug(url)
    if slug is None:
        return missing_snapshot()
    base = f"{GITHUB_API_BASE}/{slug}"
    headers = {
        "User-Agent": GITHUB_USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=GITHUB_HTTP_TIMEOUT, headers=headers) as client:
            meta = await _get_json(client, base)
            languages = await _get_json(client, f"{base}/languages")
            branch = str(meta.get("default_branch") or "main")
            tree = await _get_json(client, f"{base}/git/trees/{branch}", recursive="1")
            commits = await _get_json(client, f"{base}/commits", per_page="30")
            readme_resp = await client.get(
                f"{base}/readme", headers={"Accept": "application/vnd.github.raw+json"}
            )
            readme = readme_resp.text[:GITHUB_README_MAX_CHARS] if readme_resp.status_code == 200 else ""
    except httpx.HTTPStatusError as exc:
        return unreachable_snapshot(f"GitHub returned {exc.response.status_code}")
    except (httpx.HTTPError, ValueError) as exc:
        return unreachable_snapshot(type(exc).__name__)
    paths = [
        str(item.get("path") or "")
        for item in (tree.get("tree") or [])
        if isinstance(item, dict) and item.get("type") == "blob"
    ]
    commit_count = len(commits) if isinstance(commits, list) else 0
    meta_named = {**meta, "name": meta.get("name") or slug.split("/")[1]}
    return RepoSnapshot(
        status=GITHUB_STATUS_OK,
        readme=readme,
        paths=paths,
        evidence=summarise(meta_named, languages if isinstance(languages, dict) else {}, readme,
                           paths, commit_count),
    )
