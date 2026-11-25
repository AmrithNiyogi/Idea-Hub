"""Idea lifecycle, explore, and engagement services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.lifecycle import (
    LIVE_STATUSES,
    WITHDRAWABLE_STATUSES,
    can_transition,
)
from app.dependencies.auth import CurrentUser
from app.models.admin import ReviewPanel
from app.models.category import Category
from app.models.engagement import Comment, Follow, Vote
from app.models.idea import Idea, StatusHistory
from app.models.review import Decision
from app.schemas.idea import IdeaWrite
from app.services.notification_service import notify_idea, notify_users


def _now() -> datetime:
    return datetime.now(UTC)


def _as_uuid_list(raw: Any) -> list[uuid.UUID]:
    out: list[uuid.UUID] = []
    for item in raw or []:
        out.append(item if isinstance(item, uuid.UUID) else uuid.UUID(str(item)))
    return out


def _clean_co_authors(idea: Idea, ids: list[uuid.UUID] | None) -> list[str]:
    """Dedupe teammate ids and drop the author, so nobody is listed twice."""
    author = str(idea.author_id) if idea.author_id else None
    out: list[str] = []
    for raw in ids or []:
        value = str(raw)
        if value != author and value not in out:
            out.append(value)
    return out


def _apply_fields(idea: Idea, data: IdeaWrite) -> None:
    idea.title = data.title.strip()
    idea.category_id = data.category_id
    idea.problem = data.problem or ""
    idea.solution = data.solution or ""
    idea.beneficiaries = data.beneficiaries or ""
    idea.effort = data.effort or "M"
    idea.success_metrics = data.success_metrics or ""
    idea.tags = list(data.tags or [])
    idea.anonymous = bool(data.anonymous)
    idea.co_author_ids = _clean_co_authors(idea, data.co_author_ids)
    idea.team_name = data.team_name
    idea.github_url = data.github_url
    idea.demo_url = data.demo_url
    idea.updated_at = _now()


def _validate_submit(data: IdeaWrite) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not data.title.strip():
        errors["title"] = "Title is required"
    if not data.category_id:
        errors["category_id"] = "Choose a category"
    if len((data.problem or "").strip()) < 20:
        errors["problem"] = "Describe the problem (at least 20 characters)"
    if len((data.solution or "").strip()) < 20:
        errors["solution"] = "Describe the solution (at least 20 characters)"
    if len((data.beneficiaries or "").strip()) < 5:
        errors["beneficiaries"] = "Who benefits?"
    if len((data.success_metrics or "").strip()) < 5:
        errors["success_metrics"] = "How will you measure success?"
    return errors


async def _append_history(
    session: AsyncSession,
    idea: Idea,
    *,
    to_status: str,
    actor_id: uuid.UUID | None,
    reason: str = "",
    at: datetime | None = None,
) -> None:
    when = at or _now()
    session.add(
        StatusHistory(
            idea_id=idea.id,
            from_status=idea.status if idea.status != to_status else idea.status,
            to_status=to_status,
            actor_id=actor_id,
            at=when,
            reason=reason,
        )
    )
    idea.status = to_status
    idea.is_draft = to_status == "draft"
    idea.stage_entered_at = when
    idea.updated_at = when


async def save_draft(
    session: AsyncSession, user: CurrentUser, draft_id: uuid.UUID | None, data: IdeaWrite
) -> Idea:
    """Create or update a draft owned by the current user."""
    if not data.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Give the draft a title before saving",
        )
    idea: Idea | None = None
    if draft_id:
        idea = await get_idea(session, draft_id)
        if (
            idea is None
            or idea.status != "draft"
            or idea.author_id != user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That draft is not available",
            )
    if idea is None:
        now = _now()
        idea = Idea(
            author_id=user.id,
            status="draft",
            is_draft=True,
            title=data.title.strip(),
            stage_entered_at=now,
        )
        session.add(idea)
        await session.flush()
        session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status=None,
                to_status="draft",
                actor_id=user.id,
                at=now,
                reason="",
            )
        )
    _apply_fields(idea, data)
    await session.commit()
    await session.refresh(idea)
    return idea


async def submit_idea(
    session: AsyncSession,
    user: CurrentUser,
    draft_id: uuid.UUID | None,
    data: IdeaWrite,
) -> Idea:
    """Validate and submit an idea; auto-route draft → submitted → under_review."""
    field_errors = _validate_submit(data)
    if field_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Please fix the highlighted fields", "fields": field_errors},
        )

    idea: Idea | None = None
    if draft_id:
        idea = await get_idea(session, draft_id)
        if (
            idea is None
            or idea.status != "draft"
            or idea.author_id != user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That draft is not available",
            )
    now = _now()
    if idea is None:
        idea = Idea(author_id=user.id, status="draft", is_draft=True, title=data.title)
        session.add(idea)
        await session.flush()
        session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status=None,
                to_status="draft",
                actor_id=user.id,
                at=now,
                reason="",
            )
        )
    _apply_fields(idea, data)
    idea.submitted_at = now
    idea.due_at = now + timedelta(days=10)
    idea.pickup_due_at = now + timedelta(days=3)
    await _append_history(
        session, idea, to_status="submitted", actor_id=user.id, reason="", at=now
    )
    await _append_history(
        session,
        idea,
        to_status="under_review",
        actor_id=None,
        reason="Routed to category panel",
        at=now + timedelta(milliseconds=1),
    )
    # Author auto-follows (subscription to subsequent idea events)
    existing = await session.execute(
        select(Follow).where(Follow.idea_id == idea.id, Follow.user_id == user.id)
    )
    if existing.scalar_one_or_none() is None:
        session.add(Follow(idea_id=idea.id, user_id=user.id))

    # Route to category panel — mandatory recipients (email: routed)
    panel_ids: list[uuid.UUID] = []
    panel_label = "category"
    if idea.category_id:
        panel_row = (
            await session.execute(
                select(ReviewPanel).where(
                    ReviewPanel.category_id == idea.category_id
                )
            )
        ).scalar_one_or_none()
        if panel_row:
            panel_ids = _as_uuid_list(panel_row.member_ids or [])
            if panel_row.chair_id and panel_row.chair_id not in panel_ids:
                panel_ids.append(panel_row.chair_id)
        cat = await session.get(Category, idea.category_id)
        if cat:
            panel_label = cat.label
    if panel_ids:
        await notify_users(
            session,
            panel_ids,
            kind="routed",
            text=f'New idea routed to the {panel_label} panel: “{idea.title}”.',
            href=f"/review/{idea.id}",
            idea_id=idea.id,
            idea_title=idea.title,
            exclude=user.id,
            meta={"event": "idea_submitted"},
        )
    for co in _as_uuid_list(idea.co_author_ids):
        if co == user.id:
            continue
        await notify_users(
            session,
            [co],
            kind="coauthor",
            text=f'You were added as a co-author on “{idea.title}”.',
            href=f"/ideas/{idea.id}",
            idea_id=idea.id,
            idea_title=idea.title,
            exclude=user.id,
            send_email=False,
        )

    await session.commit()
    return await get_idea(session, idea.id, with_history=True)  # type: ignore[return-value]


async def withdraw_idea(
    session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID, reason: str
) -> Idea:
    """Author withdraws before a decision is recorded."""
    idea = await get_idea(session, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can withdraw")
    if idea.status not in WITHDRAWABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="An idea can only be withdrawn before a decision is recorded",
        )
    if not can_transition(idea.status, "withdrawn"):
        raise HTTPException(status_code=400, detail="Illegal transition")
    idea.withdraw_reason = (reason or "").strip()
    await _append_history(
        session,
        idea,
        to_status="withdrawn",
        actor_id=user.id,
        reason=idea.withdraw_reason,
    )
    await notify_idea(
        session,
        idea,
        kind="status",
        text=f'“{idea.title}” was withdrawn by its author.',
        exclude=user.id,
        send_email=False,
    )
    await session.commit()
    return await get_idea(session, idea.id, with_history=True)  # type: ignore[return-value]


async def _decision_recorded(session: AsyncSession, idea_id: uuid.UUID) -> bool:
    """True when any reviewer decision exists for the idea."""
    found = await session.execute(select(Decision.id).where(Decision.idea_id == idea_id).limit(1))
    return found.first() is not None


async def restore_idea(session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID) -> Idea:
    """Author moves a withdrawn idea back to draft so it can be edited and resubmitted.

    Only when no decision was recorded. Clears the withdrawal and any stale review or
    pause state. No notification: nobody is reviewing a draft.
    """
    idea = await get_idea(session, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can restore")
    if idea.status != "withdrawn":
        raise HTTPException(status_code=400, detail="Only a withdrawn idea can be restored")
    if not can_transition(idea.status, "draft"):
        raise HTTPException(status_code=400, detail="Illegal transition")
    if await _decision_recorded(session, idea.id):
        raise HTTPException(status_code=400, detail="This idea has a decision and cannot be restored")
    idea.withdraw_reason = ""
    idea.reviewer_id = None
    idea.picked_up_at = None
    idea.paused_at = None
    await _append_history(
        session, idea, to_status="draft", actor_id=user.id, reason="Restored to draft by author"
    )
    await session.commit()
    return await get_idea(session, idea.id, with_history=True)  # type: ignore[return-value]


async def answer_needs_info(
    session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID, text: str
) -> Idea:
    """Author/co-author answers needs_info and resumes under_review."""
    idea = await get_idea(session, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    co_ids = _as_uuid_list(idea.co_author_ids)
    if user.id != idea.author_id and user.id not in co_ids:
        raise HTTPException(status_code=403, detail="Only the author can answer")
    if idea.status != "needs_info":
        raise HTTPException(status_code=400, detail="No question is waiting")
    body = text.strip()
    if len(body) < 10:
        raise HTTPException(status_code=400, detail="Answer at least 10 characters")
    session.add(
        Comment(
            idea_id=idea.id,
            author_id=user.id,
            body=body,
            kind="info_answer",
        )
    )
    now = _now()
    if idea.paused_at:
        shift = now - idea.paused_at
        if idea.due_at:
            idea.due_at = idea.due_at + shift
        if idea.pickup_due_at:
            idea.pickup_due_at = idea.pickup_due_at + shift
        idea.paused_at = None
    idea.needs_info_question = None
    await _append_history(
        session,
        idea,
        to_status="under_review",
        actor_id=user.id,
        reason="Author answered the reviewer. Review clock resumed.",
        at=now,
    )
    recipients: list[uuid.UUID] = []
    if idea.reviewer_id:
        recipients.append(idea.reviewer_id)
    await notify_users(
        session,
        recipients,
        kind="answered",
        text=(
            f'{user.name} answered your question on “{idea.title}”. '
            "The review clock is running again."
        ),
        href=f"/review/{idea.id}",
        idea_id=idea.id,
        idea_title=idea.title,
        exclude=user.id,
        send_email=False,
    )
    await session.commit()
    return await get_idea(session, idea.id, with_history=True)  # type: ignore[return-value]


async def get_idea(
    session: AsyncSession,
    idea_id: uuid.UUID,
    *,
    with_history: bool = False,
) -> Idea | None:
    """Load an idea by id, optionally with status history."""
    stmt = select(Idea).where(Idea.id == idea_id)
    if with_history:
        stmt = stmt.options(selectinload(Idea.status_history))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_ideas(
    session: AsyncSession,
    *,
    viewer: CurrentUser | None,
    q: str | None = None,
    status_filter: list[str] | None = None,
    category_id: uuid.UUID | None = None,
    tag: str | None = None,
    author_id: uuid.UUID | None = None,
    following_only: bool = False,
    include_drafts: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Idea], int]:
    """Explore / filter ideas. Drafts are only visible to their author."""
    filters = []
    if include_drafts and viewer:
        filters.append(
            or_(Idea.status != "draft", Idea.author_id == viewer.id)
        )
    else:
        filters.append(Idea.status != "draft")

    if status_filter:
        filters.append(Idea.status.in_(status_filter))
    if category_id:
        filters.append(Idea.category_id == category_id)
    if author_id:
        filters.append(Idea.author_id == author_id)
    if q:
        like = f"%{q.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Idea.title).like(like),
                func.lower(Idea.problem).like(like),
                func.lower(Idea.solution).like(like),
            )
        )
    if tag:
        filters.append(Idea.tags.contains([tag]))
    if following_only and viewer:
        follow_ids = select(Follow.idea_id).where(Follow.user_id == viewer.id)
        filters.append(Idea.id.in_(follow_ids))

    where = and_(*filters) if filters else true()
    total = await session.scalar(select(func.count()).select_from(Idea).where(where))
    result = await session.execute(
        select(Idea)
        .where(where)
        .order_by(Idea.updated_at.desc())
        .limit(min(limit, 100))
        .offset(max(offset, 0))
    )
    return list(result.scalars().all()), int(total or 0)


async def engagement_counts(
    session: AsyncSession, idea_ids: list[uuid.UUID], viewer_id: uuid.UUID | None
) -> dict[uuid.UUID, dict[str, Any]]:
    """Batch vote/follow/comment counts (+ viewer flags)."""
    if not idea_ids:
        return {}
    out: dict[uuid.UUID, dict[str, Any]] = {
        i: {
            "vote_count": 0,
            "follow_count": 0,
            "comment_count": 0,
            "voted": False,
            "following": False,
        }
        for i in idea_ids
    }
    for model, key in ((Vote, "vote_count"), (Follow, "follow_count"), (Comment, "comment_count")):
        rows = await session.execute(
            select(model.idea_id, func.count())
            .where(model.idea_id.in_(idea_ids))
            .group_by(model.idea_id)
        )
        for idea_id, count in rows.all():
            out[idea_id][key] = int(count)

    if viewer_id:
        votes = await session.execute(
            select(Vote.idea_id).where(
                Vote.idea_id.in_(idea_ids), Vote.user_id == viewer_id
            )
        )
        for (idea_id,) in votes.all():
            out[idea_id]["voted"] = True
        follows = await session.execute(
            select(Follow.idea_id).where(
                Follow.idea_id.in_(idea_ids), Follow.user_id == viewer_id
            )
        )
        for (idea_id,) in follows.all():
            out[idea_id]["following"] = True
    return out


async def toggle_vote(
    session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID
) -> bool:
    """Toggle upvote; authors/co-authors cannot vote their own idea."""
    idea = await get_idea(session, idea_id)
    if idea is None or idea.status not in LIVE_STATUSES:
        raise HTTPException(status_code=400, detail="This idea cannot be voted on")
    if idea.author_id == user.id or user.id in _as_uuid_list(idea.co_author_ids):
        raise HTTPException(status_code=400, detail="You cannot upvote an idea you wrote")
    existing = await session.execute(
        select(Vote).where(Vote.idea_id == idea_id, Vote.user_id == user.id)
    )
    row = existing.scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()
        return False
    session.add(Vote(idea_id=idea_id, user_id=user.id))
    await session.commit()
    return True


async def toggle_follow(
    session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID
) -> bool:
    """Toggle follow on a live idea.

    Follow = subscribe to subsequent idea-scoped in-app notifications (and
    important emails). Unfollow stops those unless the user remains a
    mandatory role (author / co-author / owner / assignee).
    """
    idea = await get_idea(session, idea_id)
    if idea is None or idea.status not in LIVE_STATUSES:
        raise HTTPException(status_code=400, detail="This idea cannot be followed")
    existing = await session.execute(
        select(Follow).where(Follow.idea_id == idea_id, Follow.user_id == user.id)
    )
    row = existing.scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()
        return False
    session.add(Follow(idea_id=idea_id, user_id=user.id))
    await session.commit()
    return True


async def add_comment(
    session: AsyncSession, user: CurrentUser, idea_id: uuid.UUID, body: str
) -> Comment:
    """Post a discussion comment on a live idea."""
    idea = await get_idea(session, idea_id)
    if idea is None or idea.status not in LIVE_STATUSES:
        raise HTTPException(status_code=400, detail="This idea is not open for discussion")
    text = body.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Write something before posting")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Comments are limited to 2,000 characters")
    comment = Comment(idea_id=idea_id, author_id=user.id, body=text, kind="comment")
    session.add(comment)
    idea.updated_at = _now()
    # Major discussion comments notify author/owner/followers (in-app only).
    if len(text) >= 40:
        await notify_idea(
            session,
            idea,
            kind="comment",
            text=f'{user.name} commented on “{idea.title}”.',
            href=f"/ideas/{idea.id}",
            exclude=user.id,
            send_email=False,
        )
    await session.commit()
    await session.refresh(comment)
    return comment


async def list_comments(
    session: AsyncSession, idea_id: uuid.UUID
) -> list[Comment]:
    """Return comments for an idea oldest-first."""
    result = await session.execute(
        select(Comment)
        .where(Comment.idea_id == idea_id)
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def home_aggregates(session: AsyncSession, user: CurrentUser) -> dict[str, Any]:
    """Stage counts across live ideas plus simple needs-attention items."""
    rows = await session.execute(
        select(Idea.status, func.count())
        .where(Idea.status != "draft")
        .group_by(Idea.status)
    )
    status_counts = {st: int(n) for st, n in rows.all()}
    total_live = sum(status_counts.get(s, 0) for s in LIVE_STATUSES)

    attention: list[dict[str, Any]] = []
    # Author: needs_info on my ideas
    mine = await session.execute(
        select(Idea).where(
            Idea.author_id == user.id, Idea.status == "needs_info"
        )
    )
    for idea in mine.scalars().all():
        attention.append(
            {
                "kind": "needs_info",
                "idea_id": str(idea.id),
                "text": f"Answer the reviewer on “{idea.title}”",
                "href": f"/ideas/{idea.id}",
            }
        )
    # Only the role the viewer is working as: a reviewer working as contributor sees no review items.
    if user.acting_as("reviewer", "admin"):
        queue = await session.execute(
            select(Idea)
            .where(Idea.status == "under_review")
            .order_by(Idea.due_at.asc().nullslast())
            .limit(5)
        )
        for idea in queue.scalars().all():
            attention.append(
                {
                    "kind": "review",
                    "idea_id": str(idea.id),
                    "text": f"Review “{idea.title}”",
                    "href": f"/review/{idea.id}",
                }
            )
    return {
        "status_counts": status_counts,
        "needs_attention": attention[:12],
        "total_live": total_live,
    }
