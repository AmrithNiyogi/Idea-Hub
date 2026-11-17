"""Idea lifecycle service — validation, draft, submit, withdraw."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.dependencies.auth import CurrentUser
from app.schemas.idea import IdeaWrite
from app.services import idea_service


def _write(**overrides) -> IdeaWrite:
    base = {
        "title": "Ship smarter onboarding",
        "category_id": uuid.uuid4(),
        "problem": "New hires take too long to become productive in our tools.",
        "solution": "Guided tours plus contextual tips inside the workspace.",
        "beneficiaries": "All new hires",
        "effort": "M",
        "success_metrics": "Time-to-first-PR drops by 30%",
        "tags": ["onboarding"],
        "anonymous": False,
        "co_author_ids": [],
    }
    base.update(overrides)
    return IdeaWrite(**base)


def test_validate_submit_requires_fields() -> None:
    errors = idea_service._validate_submit(
        IdeaWrite(title=" ", category_id=None, problem="x", solution="y")
    )
    assert "title" in errors
    assert "category_id" in errors
    assert "problem" in errors
    assert "solution" in errors


def test_validate_submit_ok() -> None:
    assert idea_service._validate_submit(_write()) == {}


def test_as_uuid_list_and_apply_fields() -> None:
    uid = uuid.uuid4()
    assert idea_service._as_uuid_list([str(uid), uid]) == [uid, uid]

    idea = SimpleNamespace(
        title="",
        category_id=None,
        problem="",
        solution="",
        beneficiaries="",
        effort="S",
        success_metrics="",
        tags=[],
        anonymous=False,
        co_author_ids=[],
        updated_at=None,
    )
    data = _write()
    idea_service._apply_fields(idea, data)
    assert idea.title == data.title
    assert idea.effort == "M"
    assert idea.updated_at is not None


@pytest.mark.asyncio
async def test_save_draft_requires_title(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    with pytest.raises(HTTPException) as exc:
        await idea_service.save_draft(
            async_session, current_user, None, IdeaWrite(title="  ")
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_save_draft_creates_new(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    created = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=current_user.id,
        status="draft",
        is_draft=True,
        title="x",
    )

    async def _flush() -> None:
        # Simulate DB assigning PK
        pass

    async_session.flush = AsyncMock(side_effect=_flush)

    with patch.object(idea_service, "Idea", return_value=created):
        with patch.object(
            idea_service, "get_idea", AsyncMock(return_value=created)
        ):
            out = await idea_service.save_draft(
                async_session, current_user, None, _write(title="Draft title")
            )
    assert out is created
    async_session.add.assert_called()
    async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_save_draft_missing_existing(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await idea_service.save_draft(
                async_session, current_user, uuid.uuid4(), _write()
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_idea_validation_error(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    with pytest.raises(HTTPException) as exc:
        await idea_service.submit_idea(
            async_session, current_user, None, IdeaWrite(title="Only title")
        )
    assert exc.value.status_code == 400
    assert "fields" in exc.value.detail


@pytest.mark.asyncio
async def test_submit_idea_happy_path(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea_id = uuid.uuid4()
    idea = SimpleNamespace(
        id=idea_id,
        author_id=current_user.id,
        status="draft",
        is_draft=True,
        title="Ship smarter onboarding",
        category_id=uuid.uuid4(),
        co_author_ids=[],
        submitted_at=None,
        due_at=None,
        pickup_due_at=None,
        stage_entered_at=None,
        updated_at=None,
        problem="",
        solution="",
        beneficiaries="",
        effort="M",
        success_metrics="",
        tags=[],
        anonymous=False,
    )

    follow_result = MagicMock()
    follow_result.scalar_one_or_none.return_value = None
    panel_result = MagicMock()
    panel_result.scalar_one_or_none.return_value = None
    async_session.execute = AsyncMock(side_effect=[follow_result, panel_result])
    async_session.get = AsyncMock(return_value=None)

    with patch.object(idea_service, "Idea", return_value=idea):
        with patch.object(
            idea_service, "get_idea", AsyncMock(return_value=idea)
        ):
            with patch.object(
                idea_service, "notify_users", AsyncMock()
            ):
                out = await idea_service.submit_idea(
                    async_session, current_user, None, _write(category_id=idea.category_id)
                )
    assert out is idea
    assert idea.status == "under_review"
    async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_withdraw_idea_guards(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await idea_service.withdraw_idea(
                async_session, current_user, uuid.uuid4(), "done"
            )
    assert exc.value.status_code == 404

    foreign = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        status="submitted",
        title="x",
        withdraw_reason="",
    )
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=foreign)):
        with pytest.raises(HTTPException) as exc2:
            await idea_service.withdraw_idea(
                async_session, current_user, foreign.id, "done"
            )
    assert exc2.value.status_code == 403

    frozen = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=current_user.id,
        status="accepted",
        title="x",
        withdraw_reason="",
    )
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=frozen)):
        with pytest.raises(HTTPException) as exc3:
            await idea_service.withdraw_idea(
                async_session, current_user, frozen.id, "done"
            )
    assert exc3.value.status_code == 400


@pytest.mark.asyncio
async def test_withdraw_idea_success(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=current_user.id,
        status="under_review",
        title="Ship it",
        withdraw_reason="",
        is_draft=False,
        stage_entered_at=None,
        updated_at=None,
    )
    with patch.object(
        idea_service, "get_idea", AsyncMock(return_value=idea)
    ):
        with patch.object(idea_service, "notify_idea", AsyncMock()):
            out = await idea_service.withdraw_idea(
                async_session, current_user, idea.id, "No longer relevant"
            )
    assert out is idea
    assert idea.status == "withdrawn"


@pytest.mark.asyncio
async def test_answer_needs_info_guards(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=current_user.id,
        co_author_ids=[],
        status="under_review",
        title="x",
        needs_info_question="q",
        is_draft=False,
        stage_entered_at=None,
        updated_at=None,
    )
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=idea)):
        with pytest.raises(HTTPException) as exc:
            await idea_service.answer_needs_info(
                async_session, current_user, idea.id, "long enough answer here"
            )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_idea_passthrough(async_session: AsyncMock) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    async_session.execute.return_value = result
    assert await idea_service.get_idea(async_session, uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_answer_needs_info_success(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    paused = datetime.now(UTC) - timedelta(days=1)
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=current_user.id,
        co_author_ids=[],
        status="needs_info",
        title="Ship it",
        needs_info_question="Clarify metrics",
        is_draft=False,
        stage_entered_at=None,
        updated_at=None,
        paused_at=paused,
        due_at=datetime.now(UTC),
        pickup_due_at=datetime.now(UTC),
        reviewer_id=uuid.uuid4(),
    )
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=idea)):
        with patch.object(idea_service, "notify_users", AsyncMock()):
            out = await idea_service.answer_needs_info(
                async_session,
                current_user,
                idea.id,
                "Here is a detailed answer with enough length.",
            )
    assert out is idea
    assert idea.status == "under_review"
    assert idea.paused_at is None


@pytest.mark.asyncio
async def test_list_ideas_and_engagement(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea_id = uuid.uuid4()
    count_result = 2
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [
        SimpleNamespace(id=idea_id, status="submitted")
    ]
    async_session.scalar = AsyncMock(return_value=count_result)
    async_session.execute = AsyncMock(return_value=list_result)

    ideas, total = await idea_service.list_ideas(
        async_session,
        viewer=current_user,
        q="onboard",
        status_filter=["submitted"],
        tag="x",
        limit=10,
        offset=0,
    )
    assert total == 2
    assert len(ideas) == 1

    empty = await idea_service.engagement_counts(async_session, [], None)
    assert empty == {}

    vote_rows = MagicMock()
    vote_rows.all.return_value = [(idea_id, 3)]
    follow_rows = MagicMock()
    follow_rows.all.return_value = [(idea_id, 1)]
    comment_rows = MagicMock()
    comment_rows.all.return_value = [(idea_id, 2)]
    viewer_votes = MagicMock()
    viewer_votes.all.return_value = [(idea_id,)]
    viewer_follows = MagicMock()
    viewer_follows.all.return_value = []
    async_session.execute = AsyncMock(
        side_effect=[vote_rows, follow_rows, comment_rows, viewer_votes, viewer_follows]
    )
    counts = await idea_service.engagement_counts(
        async_session, [idea_id], current_user.id
    )
    assert counts[idea_id]["vote_count"] == 3
    assert counts[idea_id]["voted"] is True
    assert counts[idea_id]["following"] is False


@pytest.mark.asyncio
async def test_toggle_vote_follow_comment(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    other = uuid.uuid4()
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=other,
        co_author_ids=[],
        status="under_review",
        title="Live idea",
        updated_at=None,
    )
    miss = MagicMock()
    miss.scalar_one_or_none.return_value = None
    async_session.execute.return_value = miss
    async_session.delete = AsyncMock()

    with patch.object(idea_service, "get_idea", AsyncMock(return_value=idea)):
        assert await idea_service.toggle_vote(async_session, current_user, idea.id) is True
        assert await idea_service.toggle_follow(async_session, current_user, idea.id) is True
        with patch.object(idea_service, "notify_idea", AsyncMock()):
            comment = await idea_service.add_comment(
                async_session,
                current_user,
                idea.id,
                "x" * 45,
            )
    assert comment.body == "x" * 45

    # Unfollow / unvote when row exists
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = SimpleNamespace()
    async_session.execute.return_value = existing
    with patch.object(idea_service, "get_idea", AsyncMock(return_value=idea)):
        assert await idea_service.toggle_vote(async_session, current_user, idea.id) is False
        assert await idea_service.toggle_follow(async_session, current_user, idea.id) is False


@pytest.mark.asyncio
async def test_list_comments_and_home_aggregates(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    comments = MagicMock()
    comments.scalars.return_value.all.return_value = [SimpleNamespace(id=1)]
    async_session.execute.return_value = comments
    rows = await idea_service.list_comments(async_session, uuid.uuid4())
    assert len(rows) == 1

    status_rows = MagicMock()
    status_rows.all.return_value = [("under_review", 2), ("accepted", 1)]
    mine = MagicMock()
    mine.scalars.return_value.all.return_value = [
        SimpleNamespace(id=uuid.uuid4(), title="Needs you")
    ]
    async_session.execute = AsyncMock(side_effect=[status_rows, mine])
    agg = await idea_service.home_aggregates(async_session, current_user)
    assert agg["total_live"] >= 2
    assert agg["needs_attention"]
