"""Review context for agents: thread and panel decisions, with no identities and no drafts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.admin import ReviewPanel
from app.routers import agent_internal as router
from app.services import agent_review_context as svc

NOW = datetime.now(timezone.utc)
AUTHOR = uuid.UUID("99999999-8888-7777-6666-555555555555")
REVIEWER = uuid.UUID("12345678-1234-1234-1234-123456789abc")


def _session(rows_by_call: list[list] | None = None, get_result=None) -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=get_result)
    results = []
    for rows in rows_by_call or []:
        result = MagicMock()
        result.all = MagicMock(return_value=rows)
        results.append(result)
    session.execute = AsyncMock(side_effect=results or None)
    return session


@pytest.mark.asyncio
async def test_thread_returns_discussion_without_identities() -> None:
    idea = SimpleNamespace(id=uuid.uuid4(), status="under_review")
    session = _session(
        [
            [("Clarify the metric", "comment", NOW)],
            [(4, 3, 5, "Strong fit", NOW)],
            [("accept", "Matches the theme", "reviewer", NOW)],
            [(None, "under_review", NOW)],
        ]
    )
    out = await svc.idea_thread(session, idea)
    dumped = out.model_dump_json()
    assert out.comments[0].body == "Clarify the metric"
    assert out.reviews[0].impact == 4
    assert out.decisions[0].outcome == "accept"
    assert out.status_history[0].to_status == "under_review"
    assert str(AUTHOR) not in dumped and str(REVIEWER) not in dumped
    assert "author" not in dumped and "reviewer_id" not in dumped and "decider" not in dumped


@pytest.mark.asyncio
async def test_panel_decisions_carry_idea_and_outcome_only() -> None:
    panel = SimpleNamespace(id=uuid.uuid4(), name="Tech panel", category_id=uuid.uuid4())
    idea_id = uuid.uuid4()
    session = _session(
        [
            [SimpleNamespace(slug="tech")],
        ]
    )
    session.get = AsyncMock(return_value=SimpleNamespace(slug="tech"))
    session.execute = AsyncMock(
        return_value=MagicMock(
            all=MagicMock(return_value=[(idea_id, "Auto-triage", "accept", "Good fit", "reviewer", NOW)])
        )
    )
    out = await svc.panel_decisions(session, panel)
    assert out.category_slug == "tech"
    assert out.decisions[0].idea_id == idea_id
    assert out.decisions[0].outcome == "accept"
    assert str(REVIEWER) not in out.model_dump_json()


@pytest.mark.asyncio
async def test_thread_route_hides_drafts_and_missing_ideas() -> None:
    draft = SimpleNamespace(id=uuid.uuid4(), status="draft")
    with pytest.raises(HTTPException) as exc:
        await router.agent_idea_thread(draft.id, _session(get_result=draft), MagicMock())
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        await router.agent_idea_thread(uuid.uuid4(), _session(get_result=None), MagicMock())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_panel_route_404_for_unknown_panel() -> None:
    with pytest.raises(HTTPException) as exc:
        await router.agent_panel_decisions(uuid.uuid4(), _session(get_result=None), MagicMock())
    assert exc.value.status_code == 404
