"""Review context for agents: an idea's discussion and a panel's past decisions.

Responsibilities:
- Idea thread: comments, reviews (scores and notes), decisions and status changes, in time order.
- Panel decisions: the most recent decisions on ideas in the panel's category.

Privacy:
- No author, reviewer, decider or actor ids leave this module. Agents see what was said, not who said it.
- Drafts are excluded. Anonymous ideas keep their anonymity.

Side Effects:
- Read-only.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import ReviewPanel
from app.models.category import Category
from app.models.engagement import Comment
from app.models.idea import Idea, StatusHistory
from app.models.review import Decision, Review
from app.schemas.agent_internal import (
    PanelDecisionItem,
    PanelDecisionsOut,
    ThreadComment,
    ThreadDecision,
    ThreadOut,
    ThreadReview,
    ThreadStatus,
)

THREAD_LIMIT = 100
PANEL_DECISION_LIMIT = 50


async def idea_thread(session: AsyncSession, idea: Idea) -> ThreadOut:
    """The discussion on one idea, oldest first. No author or reviewer identity."""
    comments = (
        await session.execute(
            select(Comment.body, Comment.kind, Comment.created_at)
            .where(Comment.idea_id == idea.id)
            .order_by(Comment.created_at)
            .limit(THREAD_LIMIT)
        )
    ).all()
    reviews = (
        await session.execute(
            select(Review.impact, Review.effort, Review.alignment, Review.comment, Review.created_at)
            .where(Review.idea_id == idea.id)
            .order_by(Review.created_at)
            .limit(THREAD_LIMIT)
        )
    ).all()
    decisions = (
        await session.execute(
            select(Decision.outcome, Decision.reason, Decision.as_role, Decision.created_at)
            .where(Decision.idea_id == idea.id)
            .order_by(Decision.created_at)
            .limit(THREAD_LIMIT)
        )
    ).all()
    history = (
        await session.execute(
            select(StatusHistory.from_status, StatusHistory.to_status, StatusHistory.at)
            .where(StatusHistory.idea_id == idea.id)
            .order_by(StatusHistory.at)
            .limit(THREAD_LIMIT)
        )
    ).all()
    return ThreadOut(
        idea_id=idea.id,
        comments=[ThreadComment(body=b, kind=k, created_at=c) for b, k, c in comments],
        reviews=[
            ThreadReview(impact=i, effort=e, alignment=a, comment=t, created_at=c)
            for i, e, a, t, c in reviews
        ],
        decisions=[
            ThreadDecision(outcome=o, reason=r, as_role=role, created_at=c)
            for o, r, role, c in decisions
        ],
        status_history=[
            ThreadStatus(from_status=f, to_status=t, at=a) for f, t, a in history
        ],
    )


async def panel_decisions(session: AsyncSession, panel: ReviewPanel) -> PanelDecisionsOut:
    """Recent decisions on ideas in this panel's category, newest first. Drafts excluded."""
    category_slug = None
    if panel.category_id:
        category = await session.get(Category, panel.category_id)
        category_slug = category.slug if category else None
    rows = (
        await session.execute(
            select(
                Idea.id,
                Idea.title,
                Decision.outcome,
                Decision.reason,
                Decision.as_role,
                Decision.created_at,
            )
            .join(Idea, Idea.id == Decision.idea_id)
            .where(Idea.category_id == panel.category_id, Idea.status != "draft")
            .order_by(Decision.created_at.desc())
            .limit(PANEL_DECISION_LIMIT)
        )
    ).all()
    return PanelDecisionsOut(
        panel_id=panel.id,
        panel_name=panel.name,
        category_slug=category_slug,
        decisions=[
            PanelDecisionItem(
                idea_id=idea_id,
                idea_title=title,
                outcome=outcome,
                reason=reason,
                as_role=role,
                created_at=created,
            )
            for idea_id, title, outcome, reason, role, created in rows
        ],
    )
