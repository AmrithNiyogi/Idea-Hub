"""Ideathon entries as agents read them: idea content plus panel and audience signals.

Responsibilities:
- Load each entry's idea content (no author identity, drafts left out).
- Attach the human panel average and the audience vote count for the ideathon.

Collaborators:
- ``app.models.idea`` / ``app.models.category`` for content.
- ``app.models.ideathon`` for pitch scores and audience votes.

Side Effects:
- Read-only.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.idea import Idea
from app.models.ideathon import AudienceVote, PitchScore
from app.schemas.agent_internal import AgentEntryOut


def build_entry_out(
    idea: Idea,
    category_slug: Optional[str],
    panel_avg: Optional[float],
    panel_n: int,
    audience_votes: int,
) -> AgentEntryOut:
    """Shape one entry for agents. Takes the idea row's fields, never its author."""
    return AgentEntryOut(
        id=idea.id,
        title=idea.title,
        problem=idea.problem,
        solution=idea.solution,
        beneficiaries=idea.beneficiaries,
        success_metrics=idea.success_metrics,
        tags=[str(t) for t in (idea.tags or [])],
        effort=idea.effort,
        status=idea.status,
        category_slug=category_slug,
        is_anonymous=bool(idea.anonymous),
        panel_avg=panel_avg,
        panel_n=panel_n,
        audience_votes=audience_votes,
    )


async def entry_briefs(
    session: AsyncSession, ideathon_id: uuid.UUID, idea_ids: list[uuid.UUID]
) -> list[AgentEntryOut]:
    """Content and signals for each entry, in the order the ideathon lists them. Drafts are skipped."""
    if not idea_ids:
        return []
    ideas = {
        i.id: i
        for i in (await session.execute(select(Idea).where(Idea.id.in_(idea_ids)))).scalars().all()
    }
    panel_rows = (
        await session.execute(
            select(PitchScore.idea_id, func.avg(PitchScore.score), func.count())
            .where(PitchScore.ideathon_id == ideathon_id)
            .group_by(PitchScore.idea_id)
        )
    ).all()
    panel = {row[0]: (round(float(row[1]), 2), int(row[2])) for row in panel_rows}
    vote_rows = (
        await session.execute(
            select(AudienceVote.idea_id, func.count())
            .where(AudienceVote.ideathon_id == ideathon_id)
            .group_by(AudienceVote.idea_id)
        )
    ).all()
    votes = {row[0]: int(row[1]) for row in vote_rows}
    out: list[AgentEntryOut] = []
    for idea_id in idea_ids:
        idea = ideas.get(idea_id)
        if idea is None or idea.status == "draft":
            continue
        category_slug = None
        if idea.category_id:
            category = await session.get(Category, idea.category_id)
            category_slug = category.slug if category else None
        avg, n = panel.get(idea_id, (None, 0))
        out.append(build_entry_out(idea, category_slug, avg, n, votes.get(idea_id, 0)))
    return out
