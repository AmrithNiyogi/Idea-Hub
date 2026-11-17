"""Review queue, pickup, scores, and decide services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.lifecycle import DECISION_OUTCOME_MAP, can_transition
from app.dependencies.auth import CurrentUser
from app.models.idea import Idea, StatusHistory
from app.models.review import Decision, Review
from app.schemas.review import DecideRequest, ReviewScoresIn
from app.services.idea_service import _as_uuid_list, get_idea
from app.services.notification_service import notify_idea, notify_users


def _now() -> datetime:
    return datetime.now(UTC)


def _require_reviewer(user: CurrentUser) -> None:
    if not (
        user.acting_as("reviewer", "admin")
        or user.has_role("reviewer", "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer or admin role required",
        )


async def review_queue(session: AsyncSession, user: CurrentUser) -> list[Idea]:
    """Return under_review / needs_info ideas sorted by due_at (SLA)."""
    _require_reviewer(user)
    result = await session.execute(
        select(Idea)
        .where(Idea.status.in_(["under_review", "needs_info"]))
        .order_by(Idea.due_at.asc().nullslast(), Idea.submitted_at.asc().nullslast())
    )
    return list(result.scalars().all())


async def pickup(
    session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID
) -> Idea:
    """Claim an under_review idea that has not been picked up yet."""
    _require_reviewer(user)
    idea = await get_idea(session, idea_id)
    if idea is None or idea.status != "under_review":
        raise HTTPException(
            status_code=400, detail="This idea is not waiting for pickup"
        )
    if idea.picked_up_at:
        raise HTTPException(status_code=400, detail="Already picked up")
    now = _now()
    idea.picked_up_at = now
    idea.reviewer_id = user.id
    idea.stage_entered_at = now
    idea.updated_at = now
    due = idea.due_at.strftime("%d %b %Y") if idea.due_at else "soon"
    await notify_idea(
        session,
        idea,
        kind="pickup",
        text=(
            f'A reviewer picked up “{idea.title}”. '
            f"A decision is due by {due}."
        ),
        href=f"/ideas/{idea.id}",
        exclude=user.id,
        include_reviewer=False,
        send_email=False,
    )
    await session.commit()
    return await get_idea(session, idea.id)  # type: ignore[return-value]


async def save_scores(
    session: AsyncSession,
    user: CurrentUser,
    idea_id: uuid.UUID,
    payload: ReviewScoresIn,
) -> Review:
    """Upsert the current reviewer's score card."""
    _require_reviewer(user)
    idea = await get_idea(session, idea_id)
    if idea is None or idea.status not in {"under_review", "needs_info"}:
        raise HTTPException(
            status_code=400,
            detail="Scores can only be saved while an idea is in review",
        )
    result = await session.execute(
        select(Review).where(
            Review.idea_id == idea_id, Review.reviewer_id == user.id
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        review = Review(idea_id=idea_id, reviewer_id=user.id)
        session.add(review)
    review.impact = payload.impact
    review.effort = payload.effort
    review.alignment = payload.alignment
    review.comment = payload.comment or ""
    review.updated_at = _now()
    await session.commit()
    await session.refresh(review)
    return review


async def decide(
    session: AsyncSession,
    user: CurrentUser,
    idea_id: uuid.UUID,
    payload: DecideRequest,
) -> tuple[Decision, Idea]:
    """Record a decision and transition idea status.

    Enforces transitions, mandatory reason (≥20 chars), scores for non-info
    outcomes, and decision-specific fields (owner/hours, revisit, merge target).
    """
    _require_reviewer(user)
    idea = await get_idea(session, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.status != "under_review":
        raise HTTPException(
            status_code=400,
            detail="A decision can only be recorded while the idea is under review",
        )
    if idea.author_id == user.id or user.id in _as_uuid_list(idea.co_author_ids):
        raise HTTPException(
            status_code=403,
            detail="You wrote this idea, so you cannot decide on it",
        )

    to_status = DECISION_OUTCOME_MAP.get(payload.decision)
    if not to_status:
        raise HTTPException(status_code=400, detail="Choose a decision")
    if not can_transition(idea.status, to_status):
        raise HTTPException(status_code=400, detail="Illegal transition")

    field_errors: dict[str, str] = {}
    reason = payload.reason.strip()
    if len(reason) < 20:
        field_errors["reason"] = (
            "Write the question for the author (at least 20 characters)."
            if payload.decision == "info"
            else "A written reason is required (at least 20 characters)."
        )

    scores: dict[str, int] | None = None
    if payload.decision != "info":
        if (
            payload.impact is None
            or payload.effort is None
            or payload.alignment is None
        ):
            field_errors["scores"] = (
                "Score impact, effort and alignment (1 to 5) before deciding"
            )
        else:
            scores = {
                "impact": payload.impact,
                "effort": payload.effort,
                "alignment": payload.alignment,
            }

    owner_id = payload.owner_id
    hours = payload.hours
    revisit_at = payload.revisit_at
    target: Idea | None = None
    change_mind = (payload.change_mind or "").strip()

    if payload.decision == "accept":
        if not owner_id and not payload.awaiting_owner:
            field_errors["owner"] = "Choose an owner, or tick awaiting owner"
        if hours is None or not (1 <= hours <= 400):
            field_errors["hours"] = "Recommend innovation hours between 1 and 400"
    if payload.decision == "park":
        if revisit_at is None or revisit_at <= _now():
            field_errors["revisit_at"] = "Pick a revisit date in the future"
    if payload.decision == "merge":
        if not payload.target_id:
            field_errors["target_id"] = "Choose the idea to merge into"
        else:
            target = await get_idea(session, payload.target_id)
            if target is None:
                field_errors["target_id"] = "Choose the idea to merge into"
            elif target.id == idea.id:
                field_errors["target_id"] = "An idea cannot be merged into itself"
            elif target.status not in {
                "under_review",
                "needs_info",
                "accepted",
                "prototype",
                "parked",
            }:
                field_errors["target_id"] = "Choose an idea that is still active"
    if payload.decision == "decline" and len(change_mind) < 10:
        field_errors["change_mind"] = (
            "Say what would change our mind (at least 10 characters)"
        )

    if field_errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Please fix the highlighted fields", "fields": field_errors},
        )

    now = _now()
    if not idea.picked_up_at:
        idea.picked_up_at = now
        idea.reviewer_id = user.id

    if scores is not None:
        result = await session.execute(
            select(Review).where(
                Review.idea_id == idea.id, Review.reviewer_id == user.id
            )
        )
        review = result.scalar_one_or_none()
        if review is None:
            review = Review(idea_id=idea.id, reviewer_id=user.id)
            session.add(review)
        review.impact = scores["impact"]
        review.effort = scores["effort"]
        review.alignment = scores["alignment"]
        review.comment = payload.comment or ""
        review.updated_at = now

    decision = Decision(
        idea_id=idea.id,
        outcome=to_status,
        reason=reason,
        decider_id=user.id,
        as_role=user.active_role,
        owner_id=owner_id if payload.decision == "accept" else None,
        awaiting_owner=bool(payload.decision == "accept" and not owner_id),
        hours=hours if payload.decision == "accept" else None,
        revisit_at=revisit_at if payload.decision == "park" else None,
        merged_into_id=target.id if target else None,
        change_mind=change_mind if payload.decision == "decline" else "",
        question=reason if payload.decision == "info" else "",
        impact=scores["impact"] if scores else None,
        effort=scores["effort"] if scores else None,
        alignment=scores["alignment"] if scores else None,
        created_at=now,
    )
    session.add(decision)

    session.add(
        StatusHistory(
            idea_id=idea.id,
            from_status=idea.status,
            to_status=to_status,
            actor_id=user.id,
            at=now,
            reason=reason,
        )
    )
    idea.status = to_status
    idea.is_draft = False
    idea.stage_entered_at = now
    idea.updated_at = now

    if payload.decision == "accept":
        idea.owner_id = owner_id
        idea.awaiting_owner = not owner_id
        idea.hours_recommended = hours
    if payload.decision == "park":
        idea.revisit_at = revisit_at
    if payload.decision == "info":
        idea.paused_at = now
        idea.needs_info_question = reason
    if payload.decision == "merge" and target is not None:
        idea.merged_into_id = target.id
        authors = [idea.author_id, *_as_uuid_list(idea.co_author_ids)]
        target_co = _as_uuid_list(target.co_author_ids)
        for uid in authors:
            if uid == target.author_id or uid in target_co:
                continue
            target_co.append(uid)
        target.co_author_ids = [str(u) for u in target_co]
        target.updated_at = now

    # Fan-out: followers ∪ author/coauthors/owner get decision / needs_info
    if payload.decision == "info":
        await notify_idea(
            session,
            idea,
            kind="needs_info",
            text=(
                f'A reviewer asked for more info on “{idea.title}”: '
                f"{reason[:160]}"
            ),
            href=f"/ideas/{idea.id}",
            exclude=user.id,
            meta={"outcome": "needs_info"},
        )
    else:
        labels = {
            "accept": "accepted",
            "park": "parked",
            "merge": "merged",
            "decline": "declined",
        }
        verb = labels.get(payload.decision, payload.decision)
        await notify_idea(
            session,
            idea,
            kind="decision",
            text=f'“{idea.title}” was {verb}. {reason[:160]}',
            href=f"/ideas/{idea.id}",
            exclude=user.id,
            meta={"outcome": to_status, "decision": payload.decision},
        )
        if payload.decision == "accept" and owner_id:
            await notify_users(
                session,
                [owner_id],
                kind="owner",
                text=(
                    f'You are the owner of the accepted idea “{idea.title}”. '
                    f"The panel recommends {hours} innovation hours."
                ),
                href=f"/ideas/{idea.id}?tab=delivery",
                idea_id=idea.id,
                idea_title=idea.title,
                exclude=user.id,
                meta={"event": "ownership_assigned"},
            )
        if payload.decision == "merge" and target is not None:
            await notify_idea(
                session,
                target,
                kind="coauthor",
                text=(
                    f'“{idea.title}” was merged into “{target.title}”. '
                    "Its authors are now credited as co-authors."
                ),
                href=f"/ideas/{target.id}",
                exclude=user.id,
                send_email=False,
            )

    await session.commit()
    refreshed = await get_idea(session, idea.id, with_history=True)
    await session.refresh(decision)
    return decision, refreshed  # type: ignore[return-value]
