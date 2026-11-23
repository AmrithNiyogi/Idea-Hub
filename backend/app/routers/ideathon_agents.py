"""Organiser endpoints that run the Ideathon Rank and Pitch agents on Kompass.

Responsibilities:
- Check the caller is an organiser (leadership or admin) and that the ideathon exists.
- Refuse clearly when the agent or gateway is not configured (503).
- Pass the agent's result back. A failed upstream call is 502.

Side Effects:
- Outbound call to the Kompass execute endpoint. Nothing is written to the database.
- Results are proposals. The organiser decides what to keep.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.constants.ideathon_constants import ORG_ROLES
from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import Actor, RequireActor
from app.schemas.ideathon_agents import AgentRunOut, PitchRunIn, RankRunIn
from app.services import aistudio_execute_client as studio
from app.services import ideathon_pitch_service, ideathon_rank_service
from app.services.ideathon_service import IdeathonService

router = APIRouter(prefix="/ideathons", tags=["ideathons"])


def _require_organiser(actor: Actor) -> None:
    if actor.active_role not in ORG_ROLES:
        raise HTTPException(403, "Only organisers can run the Ideathon agents.")


def _caller_access_token(request: Request) -> str:
    """The signed-in user's access token. It is an HttpOnly cookie, so only the server can read it."""
    token = (request.cookies.get("access_token") or "").strip()
    if not token:
        raise HTTPException(401, "Sign in again to run the Ideathon agents.")
    return token


def _require_configured(hub_key: str) -> None:
    if not studio.aistudio_configured():
        raise HTTPException(
            503,
            "The AI Studio gateway is not configured (AISTUDIO_API_BASE_URL, "
            "AISTUDIO_TENANT_ID, AISTUDIO_PROJECT_SLUG).",
        )
    if not studio.resolve_kompass_agent_id(hub_key):
        raise HTTPException(503, f"The agent for '{hub_key}' has no Kompass agent id configured.")


def _to_out(result: studio.ExecuteResult) -> AgentRunOut:
    if not result.success:
        raise HTTPException(502, result.error or "The agent run failed.")
    return AgentRunOut(
        success=True,
        result_text=result.result_text,
        conversation_id=result.conversation_id,
        run_id=result.run_id,
    )


@router.post(
    "/{ideathon_id}/agents/rank",
    response_model=AgentRunOut,
    summary="Run the Ideathon Rank agent (proposal only)",
)
async def run_rank(
    ideathon_id: uuid.UUID,
    body: RankRunIn,
    request: Request,
    session: DbSession,
    actor: RequireActor,
) -> AgentRunOut:
    _require_organiser(actor)
    _require_configured(ideathon_rank_service.HUB_AGENT_KEY)
    token = _caller_access_token(request)
    await IdeathonService(session).get(ideathon_id)
    result = await ideathon_rank_service.propose_rank(
        ideathon_id, body.weights, tool_auth_token=token
    )
    return _to_out(result)


@router.post(
    "/{ideathon_id}/agents/pitch",
    response_model=AgentRunOut,
    summary="Run the Ideathon Pitch agent (draft only)",
)
async def run_pitch(
    ideathon_id: uuid.UUID,
    body: PitchRunIn,
    request: Request,
    session: DbSession,
    actor: RequireActor,
) -> AgentRunOut:
    _require_organiser(actor)
    _require_configured(ideathon_pitch_service.HUB_AGENT_KEY)
    token = _caller_access_token(request)
    await IdeathonService(session).get(ideathon_id)
    result = await ideathon_pitch_service.propose_pitch(
        ideathon_id,
        stage=body.stage,
        clusters=body.clusters,
        shortlist_suggestion=body.shortlist_suggestion,
        tool_auth_token=token,
    )
    return _to_out(result)
