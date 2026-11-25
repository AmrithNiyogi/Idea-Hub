"""Review decide / pickup / scores — critical decision path."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.dependencies.auth import CurrentUser
from app.schemas.review import DecideRequest, ReviewScoresIn
from app.services import review_service


def _idea(**overrides) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "author_id": uuid.uuid4(),
        "co_author_ids": [],
        "status": "under_review",
        "title": "Review me",
        "picked_up_at": None,
        "reviewer_id": None,
        "stage_entered_at": None,
        "updated_at": None,
        "awaiting_owner": False,
        "owner_id": None,
        "hours_recommended": None,
        "revisit_at": None,
        "merged_into_id": None,
        "needs_info_question": None,
        "due_at": None,
        "paused_at": None,
        "is_draft": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_review_queue_requires_role(
    current_user: CurrentUser, async_session: AsyncMock
) -> None:
    with pytest.raises(HTTPException) as exc:
        await review_service.review_queue(async_session, current_user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_review_queue_ok(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = [_idea()]
    async_session.execute.return_value = result
    rows = await review_service.review_queue(async_session, reviewer_user)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_pickup_guards(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    with patch.object(review_service, "get_idea", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await review_service.pickup(async_session, reviewer_user, uuid.uuid4())
    assert exc.value.status_code == 400

    already = _idea(picked_up_at=datetime.now(UTC))
    with patch.object(review_service, "get_idea", AsyncMock(return_value=already)):
        with pytest.raises(HTTPException) as exc2:
            await review_service.pickup(async_session, reviewer_user, already.id)
    assert exc2.value.status_code == 400


@pytest.mark.asyncio
async def test_pickup_success(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with patch.object(review_service, "notify_idea", AsyncMock()), patch.object(
            review_service, "_reviewer_ids", AsyncMock(return_value=[])
        ), patch.object(review_service, "notify_users", AsyncMock()):
            out = await review_service.pickup(async_session, reviewer_user, idea.id)
    assert out is idea
    assert idea.reviewer_id == reviewer_user.id
    assert idea.picked_up_at is not None


@pytest.mark.asyncio
async def test_save_scores_upsert(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    async_session.execute.return_value = result

    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        review = await review_service.save_scores(
            async_session,
            reviewer_user,
            idea.id,
            ReviewScoresIn(impact=4, effort=3, alignment=5, comment="solid"),
        )
    assert review.impact == 4
    async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_decide_rejects_author(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea(author_id=reviewer_user.id)
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with pytest.raises(HTTPException) as exc:
            await review_service.decide(
                async_session,
                reviewer_user,
                idea.id,
                DecideRequest(
                    decision="decline",
                    reason="Not aligned with strategy this quarter.",
                    impact=2,
                    effort=2,
                    alignment=1,
                    change_mind="Need clearer ROI story.",
                ),
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_decide_requires_scores_and_reason(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    # Bypass Pydantic min_length so the service-level field_errors path runs.
    payload = DecideRequest.model_construct(
        decision="accept",
        reason="too short",
        impact=None,
        effort=None,
        alignment=None,
        comment="",
        owner_id=None,
        awaiting_owner=True,
        hours=20,
        revisit_at=None,
        target_id=None,
        change_mind="",
    )
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with pytest.raises(HTTPException) as exc:
            await review_service.decide(
                async_session, reviewer_user, idea.id, payload
            )
    assert exc.value.status_code == 400
    assert "fields" in exc.value.detail


@pytest.mark.asyncio
async def test_decide_accept_happy_path(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    owner = uuid.uuid4()
    score_result = MagicMock()
    score_result.scalar_one_or_none.return_value = None
    async_session.execute.return_value = score_result

    payload = DecideRequest(
        decision="accept",
        reason="Strong alignment and feasible delivery this quarter.",
        impact=5,
        effort=3,
        alignment=5,
        owner_id=owner,
        hours=40,
    )

    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with patch.object(review_service, "notify_idea", AsyncMock()):
            with patch.object(review_service, "notify_users", AsyncMock()):
                decision, out_idea = await review_service.decide(
                    async_session, reviewer_user, idea.id, payload
                )
    assert out_idea.status == "accepted"
    assert decision.outcome == "accepted"
    assert idea.owner_id == owner
    async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_decide_info_and_decline(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    info = DecideRequest(
        decision="info",
        reason="Please clarify the success metrics and measurement plan.",
    )
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with patch.object(review_service, "notify_idea", AsyncMock()):
            with patch.object(review_service, "notify_users", AsyncMock()):
                decision, out = await review_service.decide(
                    async_session, reviewer_user, idea.id, info
                )
    assert out.status == "needs_info"
    assert decision.outcome == "needs_info"

    idea2 = _idea()
    decline = DecideRequest(
        decision="decline",
        reason="Duplicates an existing initiative already in delivery.",
        impact=2,
        effort=2,
        alignment=1,
        change_mind="Bring a differentiated wedge and clearer ROI.",
    )
    score_result = MagicMock()
    score_result.scalar_one_or_none.return_value = None
    async_session.execute.return_value = score_result
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea2)):
        with patch.object(review_service, "notify_idea", AsyncMock()):
            with patch.object(review_service, "notify_users", AsyncMock()):
                decision2, out2 = await review_service.decide(
                    async_session, reviewer_user, idea2.id, decline
                )
    assert out2.status == "declined"
    assert decision2.outcome == "declined"


@pytest.mark.asyncio
async def test_decide_park_requires_future_date(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    payload = DecideRequest(
        decision="park",
        reason="Good idea but not a priority for this quarter cycle.",
        impact=3,
        effort=3,
        alignment=3,
        revisit_at=datetime.now(UTC) - timedelta(days=1),
    )
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with pytest.raises(HTTPException) as exc:
            await review_service.decide(
                async_session, reviewer_user, idea.id, payload
            )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_decide_park_and_merge_success(
    reviewer_user: CurrentUser, async_session: AsyncMock
) -> None:
    idea = _idea()
    revisit = datetime.now(UTC) + timedelta(days=30)
    score_result = MagicMock()
    score_result.scalar_one_or_none.return_value = None
    async_session.execute.return_value = score_result
    park = DecideRequest(
        decision="park",
        reason="Park until next planning cycle for capacity reasons.",
        impact=3,
        effort=3,
        alignment=4,
        revisit_at=revisit,
    )
    with patch.object(review_service, "get_idea", AsyncMock(return_value=idea)):
        with patch.object(review_service, "notify_idea", AsyncMock()):
            with patch.object(review_service, "notify_users", AsyncMock()):
                decision, out = await review_service.decide(
                    async_session, reviewer_user, idea.id, park
                )
    assert out.status == "parked"
    assert decision.outcome == "parked"
    assert idea.revisit_at == revisit

    source = _idea()
    target = _idea(status="accepted", co_author_ids=[], author_id=uuid.uuid4())
    merge = DecideRequest(
        decision="merge",
        reason="Duplicates the target initiative already in acceptance.",
        impact=3,
        effort=2,
        alignment=4,
        target_id=target.id,
    )

    async def _get(session, idea_id, **kwargs):  # noqa: ANN001
        if idea_id == source.id:
            return source
        if idea_id == target.id:
            return target
        return None

    async_session.execute.return_value = score_result
    with patch.object(review_service, "get_idea", side_effect=_get):
        with patch.object(review_service, "notify_idea", AsyncMock()):
            with patch.object(review_service, "notify_users", AsyncMock()):
                decision2, out2 = await review_service.decide(
                    async_session, reviewer_user, source.id, merge
                )
    assert out2.status == "merged"
    assert decision2.outcome == "merged"
    assert source.merged_into_id == target.id


@pytest.mark.asyncio
async def test_pickup_email_goes_to_all_other_reviewers() -> None:
    picker, rev, admin, plain = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = MagicMock()
    result.all.return_value = [(picker, ["reviewer"]), (rev, ["reviewer"]), (admin, ["admin"]), (plain, ["contributor"])]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    assert await review_service._reviewer_ids(session, picker) == [rev, admin]


@pytest.mark.asyncio
async def test_reviewer_names_show_name_or_email_prefix_never_ids() -> None:
    named, blank = uuid.uuid4(), uuid.uuid4()
    result = MagicMock()
    result.all.return_value = [(named, "Nayasa Mundhra", "nayasa@x.com"), (blank, "", "fd02ebf2@x.com")]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    names = await review_service.reviewer_names(session, {named, blank})
    assert names == {named: "Nayasa Mundhra", blank: "fd02ebf2"}
    assert await review_service.reviewer_names(session, set()) == {}
