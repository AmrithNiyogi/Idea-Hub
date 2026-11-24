"""Idea team name, teammate list, and GitHub repo link."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.routers.ideas import _idea_out
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


def test_idea_response_carries_team_github_and_demo_links() -> None:
    now = datetime.now(timezone.utc)
    idea = SimpleNamespace(
        id=uuid.uuid4(), slug=None, title="t", category_id=None, problem="", solution="",
        beneficiaries="", effort="M", success_metrics="", tags=[], author_id=uuid.uuid4(),
        anonymous=False, co_author_ids=[], team_name="Team A",
        github_url="https://github.com/acme/repo", demo_url="https://demo.example.com", ai_review=None,
        owner_id=None, status="submitted", is_draft=False, reviewer_id=None,
        awaiting_owner=False, hours_recommended=None, needs_info_question=None,
        withdraw_reason="", merged_into_id=None, submitted_at=None, picked_up_at=None,
        due_at=None, pickup_due_at=None, revisit_at=None, stage_entered_at=None,
        created_at=now, updated_at=now, status_history=[],
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.routers.ideas.sa_inspect", lambda _i: SimpleNamespace(unloaded=set()))
        out = _idea_out(idea)
    assert out.team_name == "Team A"
    assert out.github_url == "https://github.com/acme/repo"
    assert out.demo_url == "https://demo.example.com"
