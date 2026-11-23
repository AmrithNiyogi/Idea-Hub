"""Internal agent routes: drafts hidden, no author identity, similarity and taxonomy shape."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.routers import agent_internal as router
from app.schemas.agent_internal import AgentIdeaOut, SimilarIn

IDEA_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
OTHER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
AUTHOR = uuid.UUID("99999999-8888-7777-6666-555555555555")


def _idea(**overrides) -> SimpleNamespace:
    base = dict(
        id=IDEA_ID, title="Auto-triage support escalations", problem="Escalations wait a day.",
        solution="Route by severity.", beneficiaries="Support leads", success_metrics="First look under 2h",
        tags=["support"], effort="M", status="under_review", category_id=None, anonymous=False,
        author_id=AUTHOR, created_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _session_with(get_result=None, rows=None) -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=get_result)
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows or []
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_draft_idea_is_not_found_for_agents() -> None:
    session = _session_with(get_result=_idea(status="draft"))
    with pytest.raises(HTTPException) as exc:
        await router.agent_get_idea(IDEA_ID, session, None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_idea_response_has_no_author_identity_even_when_not_anonymous() -> None:
    session = _session_with(get_result=_idea(anonymous=False))
    out = await router.agent_get_idea(IDEA_ID, session, None)
    assert isinstance(out, AgentIdeaOut)
    assert "author_id" not in AgentIdeaOut.model_fields
    assert "co_author_ids" not in AgentIdeaOut.model_fields
    assert out.is_anonymous is False


@pytest.mark.asyncio
async def test_anonymous_idea_only_says_it_is_anonymous() -> None:
    session = _session_with(get_result=_idea(anonymous=True))
    out = await router.agent_get_idea(IDEA_ID, session, None)
    assert out.is_anonymous is True
    assert "author" not in out.model_dump_json().lower()


@pytest.mark.asyncio
async def test_similar_excludes_given_ideas_and_reports_join_flags() -> None:
    keep = _idea(id=OTHER_ID, title="Triage support tickets faster", problem="Support escalations wait.", tags=["support"])
    drop = _idea(id=IDEA_ID, title="Triage support tickets faster", problem="Support escalations wait.", tags=["support"])
    session = _session_with(rows=[keep, drop])
    body = SimilarIn(title="Triage support escalations", problem="Escalations wait a day.", tags=["support"], exclude_idea_ids=[IDEA_ID], limit=5)
    out = await router.agent_similar(body, session, None)
    ids = [item.idea_id for item in out.items]
    assert str(IDEA_ID) not in ids
    assert str(OTHER_ID) in ids
    assert all(isinstance(item.can_join, bool) for item in out.items)


@pytest.mark.asyncio
async def test_taxonomy_lists_enabled_categories_only_by_query() -> None:
    cat = SimpleNamespace(slug="tech", label="Tech", description="Engineering")
    session = _session_with(rows=[cat])
    out = await router.agent_taxonomy(session, None)
    assert [c.slug for c in out.categories] == ["tech"]
    # the query filters on enabled, so disabled categories never reach the response
    compiled = str(session.execute.call_args.args[0])
    assert "enabled" in compiled
