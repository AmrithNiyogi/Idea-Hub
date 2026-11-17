"""Simulated agents / Kompass seam HTTP API — Phase 5."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.agents import (
    AgentInfoOut,
    AgentRunOut,
    AgentRunRequest,
    KompassAnswerIn,
    KompassMapOut,
    PendingProposalOut,
    ProposalDecideIn,
    ProposalDecisionOut,
)
from app.services.agent_gateway import AgentGateway

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "/roster",
    response_model=list[AgentInfoOut],
    summary="Simulated agent roster (KOMPASS-aligned)",
)
async def roster(session: DbSession, actor: RequireActor) -> list[AgentInfoOut]:
    return AgentGateway(session).roster()


@router.post(
    "/run",
    response_model=AgentRunOut,
    summary="Run a simulated agent (always labelled Simulated)",
    description=(
        "Deterministic heuristics only. No live Kompass call. "
        "Approval-gated runs appear in pending proposals until a human decides."
    ),
)
async def run_agent(
    body: AgentRunRequest, session: DbSession, actor: RequireActor
) -> AgentRunOut:
    return await AgentGateway(session).run(body, actor)


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
    pending_only: bool = False,
) -> list[AgentRunOut]:
    return await AgentGateway(session).list_runs(
        limit=limit, agent_id=agent_id, pending_only=pending_only
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
