"""Review queue and decision routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter

from app.dependencies.auth import DbSession, RequireUser
from app.schemas.idea import IdeaOut
from app.schemas.review import (
    DecideRequest,
    DecisionOut,
    ReviewQueueItem,
    ReviewScoresIn,
)
from app.services import review_service
from app.routers.ideas import _idea_out

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[ReviewQueueItem], summary="Review queue")
async def queue(
    session: DbSession, current: RequireUser
) -> list[ReviewQueueItem]:
    """SLA-sorted queue of ideas awaiting review decisions."""
    ideas = await review_service.review_queue(session, current)
    now = datetime.now(UTC)
    items: list[ReviewQueueItem] = []
    for idea in ideas:
        days = None
        if idea.due_at:
            days = (idea.due_at - now).total_seconds() / 86400.0
        items.append(
            ReviewQueueItem(
                idea_id=idea.id,
                title=idea.title,
                status=idea.status,
                category_id=idea.category_id,
                author_id=idea.author_id,
                submitted_at=idea.submitted_at,
                due_at=idea.due_at,
                pickup_due_at=idea.pickup_due_at,
                picked_up_at=idea.picked_up_at,
                reviewer_id=idea.reviewer_id,
                days_until_due=days,
            )
        )
    return items


@router.post(
    "/{idea_id}/pickup", response_model=IdeaOut, summary="Pick up idea"
)
async def pickup(
    idea_id: UUID, session: DbSession, current: RequireUser
) -> IdeaOut:
    """Claim an under_review idea."""
    idea = await review_service.pickup(session, current, idea_id)
    return _idea_out(idea)


@router.post(
    "/{idea_id}/scores", summary="Save review scores"
)
async def save_scores(
    idea_id: UUID,
    body: ReviewScoresIn,
    session: DbSession,
    current: RequireUser,
) -> dict:
    """Upsert impact/effort/alignment scores for the current reviewer."""
    review = await review_service.save_scores(session, current, idea_id, body)
    return {
        "id": review.id,
        "idea_id": review.idea_id,
        "impact": review.impact,
        "effort": review.effort,
        "alignment": review.alignment,
        "comment": review.comment,
    }


@router.post(
    "/{idea_id}/decide",
    response_model=DecisionOut,
    summary="Record decision",
)
async def decide(
    idea_id: UUID,
    body: DecideRequest,
    session: DbSession,
    current: RequireUser,
) -> DecisionOut:
    """Record accept/park/merge/decline/needs_info with mandatory reason."""
    decision, _idea = await review_service.decide(
        session, current, idea_id, body
    )
    return DecisionOut.model_validate(decision)
