"""Idea team name, teammate list, and GitHub repo link."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.idea import IdeaWrite
from app.services.idea_service import _clean_co_authors


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/acme/ideas-hub",
        "https://github.com/acme/ideas-hub/",
        "https://github.com/acme.team/repo_1-2",
    ],
)
def test_valid_github_repo_urls_are_accepted(url: str) -> None:
    assert IdeaWrite(title="t", github_url=url).github_url == url


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/acme/repo",
        "https://gitlab.com/acme/repo",
        "https://github.com/acme",
        "https://github.com/acme/repo/tree/main",
        "https://github.com.evil.example/acme/repo",
        "javascript:alert(1)",
    ],
)
def test_non_repo_github_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        IdeaWrite(title="t", github_url=url)


def test_blank_github_and_team_are_stored_as_none() -> None:
    data = IdeaWrite(title="t", github_url="   ", team_name="  ")
    assert data.github_url is None
    assert data.team_name is None


def test_team_name_is_trimmed() -> None:
    assert IdeaWrite(title="t", team_name="  Night Owls ").team_name == "Night Owls"


def test_team_name_length_is_limited() -> None:
    with pytest.raises(ValidationError):
        IdeaWrite(title="t", team_name="x" * 121)


def test_co_authors_are_deduped_and_exclude_author() -> None:
    author = uuid.uuid4()
    mate = uuid.uuid4()
    idea = SimpleNamespace(author_id=author)
    out = _clean_co_authors(idea, [author, mate, mate])  # type: ignore[arg-type]
    assert out == [str(mate)]
