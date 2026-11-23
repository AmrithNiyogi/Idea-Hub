"""Internal read routes for Kompass agent tools.

Mounted at ``/api/v1/internal/agents``. Every route needs a valid user token, sent as the
``access_token`` cookie or ``X-Authorization``. The ``X-User-Id`` local stub is not accepted here.

Responsibilities:
- Serve idea, taxonomy, similarity and ideathon-entry data in a shape agents can use.
- Never return author identity, including for anonymous ideas.
- Hide drafts from agents.

Side Effects:
- Read-only.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db.session_deps import DbSession
from app.dependencies.auth import RequireAgentCaller
from app.models.category import Category
from app.models.idea import Idea
from app.schemas.agent_internal import (
    PanelDecisionsOut,
    ThreadOut,
    AgentIdeaOut,
    EntriesOut,
    SimilarIn,
    SimilarItem,
    SimilarOut,
    TaxonomyItem,
    TaxonomyOut,
)
from app.models.admin import ReviewPanel
from app.services import agent_entry_service, agent_review_context
from app.services import agent_heuristics as heuristics
from app.utils.debug_log import log_incoming_request
from app.services.ideathon_service import IdeathonService

router = APIRouter(
    prefix="/internal/agents", tags=["agent-internal"], dependencies=[Depends(log_incoming_request)]
)


@router.get("/ideas/{idea_id}", response_model=AgentIdeaOut, summary="Idea content for agents (no author)")
async def agent_get_idea(idea_id: uuid.UUID, session: DbSession, _caller: RequireAgentCaller) -> AgentIdeaOut:
    idea = await session.get(Idea, idea_id)
    if idea is None or idea.status == "draft":
        raise HTTPException(404, "Idea not found.")
    category_slug = None
    if idea.category_id:
        category = await session.get(Category, idea.category_id)
        category_slug = category.slug if category else None
    return AgentIdeaOut(
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
    )


@router.get("/config/taxonomy", response_model=TaxonomyOut, summary="Enabled idea categories")
async def agent_taxonomy(session: DbSession, _caller: RequireAgentCaller) -> TaxonomyOut:
    rows = (
        await session.execute(
            select(Category).where(Category.enabled.is_(True)).order_by(Category.slug)
        )
    ).scalars().all()
    return TaxonomyOut(
        categories=[TaxonomyItem(slug=c.slug, label=c.label, description=c.description) for c in rows]
    )


@router.post("/ideas/similar", response_model=SimilarOut, summary="Ideas similar to a draft")
async def agent_similar(body: SimilarIn, session: DbSession, _caller: RequireAgentCaller) -> SimilarOut:
    excluded = set(body.exclude_idea_ids)
    rows = (await session.execute(select(Idea).where(Idea.status != "draft").limit(200))).scalars().all()
    corpus = [idea for idea in rows if idea.id not in excluded]
    draft = {"title": body.title, "problem": body.problem, "tags": body.tags}
    found = heuristics.similar_ideas(draft, corpus, limit=body.limit)
    return SimilarOut(items=[SimilarItem(**item) for item in found])


@router.get("/ideathons/{ideathon_id}/entries", response_model=EntriesOut, summary="Ideathon entry ids and phase")
async def agent_ideathon_entries(ideathon_id: uuid.UUID, session: DbSession, _caller: RequireAgentCaller) -> EntriesOut:
    it = await IdeathonService(session).get(ideathon_id)
    entries = await agent_entry_service.entry_briefs(session, ideathon_id, it.entry_idea_ids)
    return EntriesOut(
        id=it.id,
        title=it.title,
        theme=it.theme,
        challenges=it.challenges,
        phase=it.phase,
        entry_idea_ids=it.entry_idea_ids,
        shortlist=it.shortlist,
        entries=entries,
    )


@router.get("/ideas/{idea_id}/thread", response_model=ThreadOut, summary="Discussion on an idea (no identities)")
async def agent_idea_thread(idea_id: uuid.UUID, session: DbSession, _caller: RequireAgentCaller) -> ThreadOut:
    idea = await session.get(Idea, idea_id)
    if idea is None or idea.status == "draft":
        raise HTTPException(404, "Idea not found.")
    return await agent_review_context.idea_thread(session, idea)


@router.get(
    "/panels/{panel_id}/decisions",
    response_model=PanelDecisionsOut,
    summary="Recent decisions in a review panel (no identities)",
)
async def agent_panel_decisions(
    panel_id: uuid.UUID, session: DbSession, _caller: RequireAgentCaller
) -> PanelDecisionsOut:
    panel = await session.get(ReviewPanel, panel_id)
    if panel is None:
        raise HTTPException(404, "Panel not found.")
    return await agent_review_context.panel_decisions(session, panel)
