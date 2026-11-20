"""Agents / Kompass seam HTTP API — Phase 5."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.agents import (
    AgentInfoOut,
    AgentRunOut,
    AgentRunRequest,
    HelpTurnIn,
    HelpTurnOut,
    IdeaOptimizeTurnIn,
    IdeaOptimizeTurnOut,
    KompassAnswerIn,
    KompassMapOut,
    PendingProposalOut,
    ProposalDecideIn,
    ProposalDecisionOut,
    SubmitAssistTurnIn,
    SubmitAssistTurnOut,
)
from app.services.agent_gateway import AgentGateway
from app.services import agent_live_turns as live_turns

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "/roster",
    response_model=list[AgentInfoOut],
    summary="Agent roster (KOMPASS-aligned; simulated or live)",
)
async def roster(session: DbSession, actor: RequireActor) -> list[AgentInfoOut]:
    return AgentGateway(session).roster()


@router.post(
    "/run",
    response_model=AgentRunOut,
    summary="Run an agent (simulate or live AI Studio execute)",
    description=(
        "Local heuristics when SIMULATE_AGENTS=true or AI Studio env is incomplete. "
        "When live, idea-optimizer / review-intelligence / coding-agent-build call "
        "POST /api/v2/runs/execute when configured. Approval-gated runs still "
        "require a human decide."
    ),
)
async def run_agent(
    body: AgentRunRequest, session: DbSession, actor: RequireActor
) -> AgentRunOut:
    return await AgentGateway(session).run(body, actor)


@router.post(
    "/builds/{idea_id}",
    response_model=AgentRunOut,
    summary="Launch Idea → Agent Build Loop",
    description=(
        "For an Accepted idea: generate agent-context / skill pack, execute "
        "(or simulate) a Kompass-shaped coding build, and open a human gate "
        "before Prototype. Persists a real AgentRun timeline. Never auto-flips "
        "status to Prototype."
    ),
    responses={
        400: {"description": "Idea is not Accepted"},
        403: {"description": "Caller cannot launch builds for this idea"},
        404: {"description": "Idea not found"},
    },
)
async def launch_agent_build(
    idea_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> AgentRunOut:
    """Start a coding-agent build run for an Accepted idea."""
    return await AgentGateway(session).launch_agent_build(idea_id, actor)


@router.get(
    "/runs",
    response_model=list[AgentRunOut],
    summary="Agent run log",
)
async def list_runs(
    session: DbSession,
    actor: RequireActor,
    limit: int = Query(50, ge=1, le=200),
    agent_id: Optional[str] = None,
    idea_id: Optional[uuid.UUID] = None,
    pending_only: bool = False,
) -> list[AgentRunOut]:
    return await AgentGateway(session).list_runs(
        limit=limit,
        agent_id=agent_id,
        idea_id=idea_id,
        pending_only=pending_only,
    )


@router.get(
    "/proposals",
    response_model=list[PendingProposalOut],
    summary="Pending human-approval proposals",
)
async def pending(
    session: DbSession, actor: RequireActor
) -> list[PendingProposalOut]:
    return await AgentGateway(session).pending_proposals()


@router.post(
    "/proposals/decide",
    response_model=ProposalDecisionOut,
    summary="Approve or reject an agent proposal",
)
async def decide(
    body: ProposalDecideIn, session: DbSession, actor: RequireActor
) -> ProposalDecisionOut:
    return await AgentGateway(session).decide_proposal(body, actor)


@router.get(
    "/kompass",
    response_model=KompassMapOut,
    summary="Kompass integration map (always disconnected in MVP)",
)
async def kompass_map(session: DbSession, actor: RequireActor) -> KompassMapOut:
    return await AgentGateway(session).kompass_map()


@router.put(
    "/kompass/questions/{question_id}",
    response_model=KompassMapOut,
    summary="Mark a Kompass open question answered",
)
async def answer_question(
    question_id: str,
    body: KompassAnswerIn,
    session: DbSession,
    actor: RequireActor,
) -> KompassMapOut:
    return await AgentGateway(session).answer_kompass(
        question_id, body.answered, body.note, actor
    )


@router.post(
    "/simulate/submit-assist",
    response_model=SubmitAssistTurnOut,
    summary="Submit ideation co-pilot turn (simulate or live)",
    description=(
        "Freeform brainstorm / refine chat that returns optional form patches "
        "(title, problem, solution, tags, category_slug, effort, …). "
        "Local heuristic while SIMULATE_AGENTS=true; otherwise "
        "POST /api/v2/runs/execute with AISTUDIO_AGENT_SUBMIT_ASSIST. "
        "Echo conversation_id for multi-turn. Never persists the draft."
    ),
    responses={401: {"description": "Not authenticated"}},
)
async def submit_assist_turn(
    body: SubmitAssistTurnIn,
    actor: RequireActor,
) -> SubmitAssistTurnOut:
    """Run one Submit assist turn for the authenticated author."""
    _ = actor
    out = await live_turns.submit_assist_turn(
        draft=body.draft,
        message=body.message,
        awaiting_field=body.awaiting_field,
        conversation_id=body.conversation_id,
    )
    return SubmitAssistTurnOut.model_validate(out)


@router.post(
    "/simulate/help",
    response_model=HelpTurnOut,
    summary="In-app help chatbot turn (simulate or live)",
    description=(
        "FAQ / intent map locally when simulating; live Help agent via "
        "runs/execute when configured. Does not accept or store secrets. "
        "Echo conversation_id for Help FAB multi-turn."
    ),
    responses={401: {"description": "Not authenticated"}},
)
async def help_turn(body: HelpTurnIn, actor: RequireActor) -> HelpTurnOut:
    """Answer a product FAQ question (stub map or live Kompass agent)."""
    _ = actor
    out = await live_turns.help_turn(
        message=body.message,
        conversation_id=body.conversation_id,
    )
    return HelpTurnOut.model_validate(out)


@router.post(
    "/simulate/idea-optimize",
    response_model=IdeaOptimizeTurnOut,
    summary="Author Idea Optimizer turn (simulate or live)",
    description=(
        "Post-submit author co-pilot: clarity, metrics, tags, problem framing. "
        "Returns reply + field_patches for the human to apply. Distinct from "
        "Review Intelligence (scores / decision lean). Never persists changes. "
        "Echo conversation_id for multi-turn optimizer sessions."
    ),
    responses={401: {"description": "Not authenticated"}},
)
async def idea_optimize_turn(
    body: IdeaOptimizeTurnIn,
    actor: RequireActor,
) -> IdeaOptimizeTurnOut:
    """Run one author-optimizer turn for the authenticated user."""
    _ = actor
    idea = dict(body.idea or {})
    if body.idea_id and "id" not in idea:
        idea["id"] = str(body.idea_id)
    out = await live_turns.idea_optimize_turn(
        idea=idea,
        message=body.message,
        messages=body.messages,
        conversation_id=body.conversation_id,
    )
    return IdeaOptimizeTurnOut.model_validate(out)
