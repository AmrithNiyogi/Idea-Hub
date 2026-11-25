"""Idea CRUD, explore, engagement, and author lifecycle routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import inspect as sa_inspect

from app.dependencies.auth import DbSession, OptionalUser, RequireUser
from app.schemas.agent_context import AgentContextOut
from app.schemas.idea import (
    AnswerInfoRequest,
    CommentCreate,
    CommentOut,
    HomeAggregates,
    IdeaDraftSave,
    IdeaListResponse,
    IdeaOut,
    IdeaSubmitRequest,
    StatusHistoryOut,
    ToggleResponse,
    WithdrawRequest,
)
from app.services import agent_context_service, idea_ai_review_service, idea_service

router = APIRouter(prefix="/ideas", tags=["ideas"])


def _idea_out(idea: Any, counts: dict[str, Any] | None = None) -> IdeaOut:
    c = counts or {}
    co = []
    for item in idea.co_author_ids or []:
        co.append(item if isinstance(item, UUID) else UUID(str(item)))
    # Avoid async lazy-load of status_history on list endpoints.
    history: list[StatusHistoryOut] = []
    insp = sa_inspect(idea)
    if "status_history" not in insp.unloaded:
        history = [
            StatusHistoryOut.model_validate(h)
            for h in (idea.status_history or [])
        ]
    return IdeaOut(
        id=idea.id,
        slug=idea.slug,
        title=idea.title,
        category_id=idea.category_id,
        problem=idea.problem,
        solution=idea.solution,
        beneficiaries=idea.beneficiaries,
        effort=idea.effort,
        success_metrics=idea.success_metrics,
        tags=list(idea.tags or []),
        author_id=idea.author_id,
        anonymous=idea.anonymous,
        co_author_ids=co,
        team_name=idea.team_name,
        github_url=idea.github_url,
        demo_url=idea.demo_url,
        ai_review=idea.ai_review,
        owner_id=idea.owner_id,
        status=idea.status,
        is_draft=idea.is_draft,
        reviewer_id=idea.reviewer_id,
        awaiting_owner=idea.awaiting_owner,
        hours_recommended=idea.hours_recommended,
        needs_info_question=idea.needs_info_question,
        withdraw_reason=idea.withdraw_reason or "",
        merged_into_id=idea.merged_into_id,
        submitted_at=idea.submitted_at,
        picked_up_at=idea.picked_up_at,
        due_at=idea.due_at,
        pickup_due_at=idea.pickup_due_at,
        revisit_at=idea.revisit_at,
        stage_entered_at=idea.stage_entered_at,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
        vote_count=c.get("vote_count", 0),
        follow_count=c.get("follow_count", 0),
        comment_count=c.get("comment_count", 0),
        voted=c.get("voted", False),
        following=c.get("following", False),
        status_history=history,
    )


@router.get("", response_model=IdeaListResponse, summary="Explore / list ideas")
async def list_ideas(
    session: DbSession,
    viewer: OptionalUser,
    q: str | None = None,
    status: list[str] | None = Query(default=None),
    category_id: UUID | None = None,
    tag: str | None = None,
    author_id: UUID | None = None,
    following: bool = False,
    include_drafts: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> IdeaListResponse:
    """Filter ideas by search, status, category, tag, author, or following."""
    items, total = await idea_service.list_ideas(
        session,
        viewer=viewer,
        q=q,
        status_filter=status,
        category_id=category_id,
        tag=tag,
        author_id=author_id,
        following_only=following,
        include_drafts=include_drafts,
        limit=limit,
        offset=offset,
    )
    counts = await idea_service.engagement_counts(
        session, [i.id for i in items], viewer.id if viewer else None
    )
    return IdeaListResponse(
        items=[_idea_out(i, counts.get(i.id)) for i in items],
        total=total,
    )


@router.get("/home", response_model=HomeAggregates, summary="Home aggregates")
async def home(session: DbSession, current: RequireUser) -> HomeAggregates:
    """Stage counts and needs-attention items for the signed-in user."""
    data = await idea_service.home_aggregates(session, current)
    return HomeAggregates(**data)


@router.get("/{idea_id}", response_model=IdeaOut, summary="Get idea detail")
async def get_idea(
    idea_id: UUID, session: DbSession, viewer: OptionalUser
) -> IdeaOut:
    """Return an idea with status history and engagement counts."""
    from fastapi import HTTPException

    idea = await idea_service.get_idea(session, idea_id, with_history=True)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.status == "draft" and (viewer is None or viewer.id != idea.author_id):
        raise HTTPException(status_code=404, detail="Idea not found")
    counts = await idea_service.engagement_counts(
        session, [idea.id], viewer.id if viewer else None
    )
    return _idea_out(idea, counts.get(idea.id))


@router.get(
    "/{idea_id}/agent-context",
    response_model=AgentContextOut,
    summary="Agent handoff context pack",
    description=(
        "Authenticated endpoint that returns structured idea context plus "
        "rendered markdown and Cursor/Claude Code prompt wrappers. "
        "Anonymous authorship is redacted. Never includes secrets or emails."
    ),
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Idea not found or still a private draft"},
    },
)
async def get_agent_context(
    idea_id: UUID, session: DbSession, current: RequireUser
) -> AgentContextOut:
    """Return a paste-ready agent context pack for implementing this idea."""
    _ = current  # auth gate; payload is not personalized beyond redaction rules
    return await agent_context_service.build_agent_context(session, idea_id)


@router.post("/drafts", response_model=IdeaOut, summary="Save draft")
async def save_draft(
    body: IdeaDraftSave, session: DbSession, current: RequireUser
) -> IdeaOut:
    """Create or update a draft owned by the current user."""
    idea = await idea_service.save_draft(
        session, current, body.draft_id, body.data
    )
    return _idea_out(idea)


@router.post("/submit", response_model=IdeaOut, summary="Submit idea")
async def submit(
    body: IdeaSubmitRequest,
    session: DbSession,
    current: RequireUser,
    background: BackgroundTasks,
) -> IdeaOut:
    """Validate and submit; auto-routes into under_review, then builds the AI review in the background."""
    idea = await idea_service.submit_idea(
        session, current, body.draft_id, body.data
    )
    background.add_task(idea_ai_review_service.generate_and_store, idea.id)
    return _idea_out(idea)


@router.post(
    "/{idea_id}/withdraw", response_model=IdeaOut, summary="Withdraw idea"
)
async def withdraw(
    idea_id: UUID,
    body: WithdrawRequest,
    session: DbSession,
    current: RequireUser,
) -> IdeaOut:
    """Author withdraws before a decision is recorded."""
    idea = await idea_service.withdraw_idea(
        session, current, idea_id, body.reason
    )
    return _idea_out(idea)


@router.post(
    "/{idea_id}/restore", response_model=IdeaOut, summary="Restore a withdrawn idea to draft"
)
async def restore(idea_id: UUID, session: DbSession, current: RequireUser) -> IdeaOut:
    """Author moves a withdrawn idea back to draft (only when no decision was recorded)."""
    idea = await idea_service.restore_idea(session, current, idea_id)
    return _idea_out(idea)


@router.post(
    "/{idea_id}/answer-info",
    response_model=IdeaOut,
    summary="Answer needs_info",
)
async def answer_info(
    idea_id: UUID,
    body: AnswerInfoRequest,
    session: DbSession,
    current: RequireUser,
) -> IdeaOut:
    """Author answers a reviewer question and resumes review."""
    idea = await idea_service.answer_needs_info(
        session, current, idea_id, body.text
    )
    return _idea_out(idea)


@router.post(
    "/{idea_id}/vote", response_model=ToggleResponse, summary="Toggle vote"
)
async def vote(
    idea_id: UUID, session: DbSession, current: RequireUser
) -> ToggleResponse:
    """Toggle upvote on a live idea."""
    active = await idea_service.toggle_vote(session, current, idea_id)
    return ToggleResponse(active=active)


@router.post(
    "/{idea_id}/follow", response_model=ToggleResponse, summary="Toggle follow"
)
async def follow(
    idea_id: UUID, session: DbSession, current: RequireUser
) -> ToggleResponse:
    """Toggle follow on a live idea."""
    active = await idea_service.toggle_follow(session, current, idea_id)
    return ToggleResponse(active=active)


@router.get(
    "/{idea_id}/comments",
    response_model=list[CommentOut],
    summary="List comments",
)
async def comments(idea_id: UUID, session: DbSession) -> list[CommentOut]:
    """Return discussion comments for an idea."""
    rows = await idea_service.list_comments(session, idea_id)
    return [CommentOut.model_validate(c) for c in rows]


@router.post(
    "/{idea_id}/comments",
    response_model=CommentOut,
    summary="Add comment",
)
async def add_comment(
    idea_id: UUID,
    body: CommentCreate,
    session: DbSession,
    current: RequireUser,
) -> CommentOut:
    """Post a discussion comment."""
    comment = await idea_service.add_comment(
        session, current, idea_id, body.body
    )
    return CommentOut.model_validate(comment)
