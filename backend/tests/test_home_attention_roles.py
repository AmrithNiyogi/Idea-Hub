"""Home "needs your attention" follows the active role, not every role held."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies.auth import CurrentUser
from app.services import idea_service


def _session(review_rows: list) -> MagicMock:
    """Three queries in order: status counts, my needs_info ideas, review queue."""
    empty_all = SimpleNamespace(all=lambda: [], scalars=lambda: SimpleNamespace(all=lambda: []))
    review = SimpleNamespace(all=lambda: [], scalars=lambda: SimpleNamespace(all=lambda: review_rows))
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[empty_all, empty_all, review])
    return session


def _user(active_role: str) -> CurrentUser:
    return CurrentUser(
        id=uuid.uuid4(),
        email="sam@dotkonnekt.example",
        name="Sam Patel",
        roles=["contributor", "reviewer"],
        active_role=active_role,
        primary_role="contributor",
        slug="sam-patel",
    )


def _idea() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), title="One view of renewal signals")


@pytest.mark.asyncio
async def test_reviewer_role_held_but_working_as_contributor_sees_no_review_items() -> None:
    session = _session([_idea()])
    data = await idea_service.home_aggregates(session, _user("contributor"))
    assert [i["kind"] for i in data["needs_attention"]] == []
    assert session.execute.await_count == 2  # review queue is never queried


@pytest.mark.asyncio
async def test_reviewer_working_as_reviewer_sees_review_items() -> None:
    session = _session([_idea()])
    data = await idea_service.home_aggregates(session, _user("reviewer"))
    assert [i["kind"] for i in data["needs_attention"]] == ["review"]
    assert session.execute.await_count == 3
