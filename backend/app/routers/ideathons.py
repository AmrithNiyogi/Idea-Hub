"""Ideathons HTTP API — Phase 3.

TODO: wire into main via ``include_phase23_routers(app)``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.ideathon import (
    AudienceVoteRequest,
    ConfirmWinnersRequest,
    HandoffOut,
    HandoffRequest,
    IdeathonCreate,
    IdeathonDetailOut,
    IdeathonSummaryOut,
    IdeathonUpdate,
    LinkIdeaRequest,
    MovePitchRequest,
    PitchScoreRequest,
    ShortlistApprove,
    TallyRowOut,
)
from app.services.ideathon_service import IdeathonService

router = APIRouter(prefix="/ideathons", tags=["ideathons"])


@router.get(
    "",
    response_model=list[IdeathonSummaryOut],
    summary="List ideathon campaigns",
)
async def list_ideathons(
    session: DbSession, actor: RequireActor
) -> list[IdeathonSummaryOut]:
    return await IdeathonService(session).list_ideathons()


@router.post(
    "",
    status_code=201,
    summary="Create an ideathon campaign",
)
async def create_ideathon(
    body: IdeathonCreate, session: DbSession, actor: RequireActor
) -> dict:
    return await IdeathonService(session).create(body, actor)


@router.get(
    "/{ideathon_id}",
    response_model=IdeathonDetailOut,
    summary="Get ideathon detail",
)
async def get_ideathon(
    ideathon_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> IdeathonDetailOut:
    return await IdeathonService(session).get(ideathon_id)


@router.patch(
    "/{ideathon_id}",
    summary="Edit ideathon details (organiser)",
)
async def update_ideathon(
    ideathon_id: uuid.UUID,
    body: IdeathonUpdate,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).update(ideathon_id, body, actor)


@router.post("/{ideathon_id}/advance", summary="Advance ideathon to next phase")
async def advance(
    ideathon_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> dict:
    return await IdeathonService(session).advance(ideathon_id, actor)


@router.post("/{ideathon_id}/link", summary="Link an idea as an entry")
async def link_idea(
    ideathon_id: uuid.UUID,
    body: LinkIdeaRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).link_idea(ideathon_id, body, actor)


@router.delete(
    "/{ideathon_id}/entries/{idea_id}",
    summary="Unlink an idea from the ideathon",
)
async def unlink_idea(
    ideathon_id: uuid.UUID,
    idea_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).unlink_idea(
        ideathon_id, idea_id, actor
    )


@router.post(
    "/{ideathon_id}/shortlist",
    summary="Approve shortlist (organiser)",
)
async def approve_shortlist(
    ideathon_id: uuid.UUID,
    body: ShortlistApprove,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).approve_shortlist(
        ideathon_id, body, actor
    )


@router.post("/{ideathon_id}/pitch/move", summary="Reorder pitch list")
async def move_pitch(
    ideathon_id: uuid.UUID,
    body: MovePitchRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).move_pitch(ideathon_id, body, actor)


@router.post("/{ideathon_id}/pitch/score", summary="Panel pitch score (1–10)")
async def score_pitch(
    ideathon_id: uuid.UUID,
    body: PitchScoreRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).score_pitch(ideathon_id, body, actor)


@router.post(
    "/{ideathon_id}/pitch/vote",
    summary="Audience vote (toggle)",
)
async def audience_vote(
    ideathon_id: uuid.UUID,
    body: AudienceVoteRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).audience_vote(
        ideathon_id, body, actor
    )


@router.post("/{ideathon_id}/pitch/close", summary="Close voting")
async def close_voting(
    ideathon_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> dict:
    return await IdeathonService(session).close_voting(ideathon_id, actor)


@router.get(
    "/{ideathon_id}/tally",
    response_model=list[TallyRowOut],
    summary="Computed pitch tally",
)
async def tally(
    ideathon_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[TallyRowOut]:
    return await IdeathonService(session).tally(ideathon_id)


@router.post(
    "/{ideathon_id}/winners",
    summary="Confirm winners (1–2)",
)
async def confirm_winners(
    ideathon_id: uuid.UUID,
    body: ConfirmWinnersRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await IdeathonService(session).confirm_winners(
        ideathon_id, body, actor
    )


@router.get(
    "/{ideathon_id}/handoffs",
    response_model=list[HandoffOut],
    summary="List hackathon handoffs for an ideathon",
)
async def list_handoffs(
    ideathon_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[HandoffOut]:
    return await IdeathonService(session).list_handoffs(ideathon_id)


@router.post(
    "/{ideathon_id}/handoff",
    response_model=HandoffOut,
    summary="Send hackathon handoff for a winner",
)
async def send_handoff(
    ideathon_id: uuid.UUID,
    body: HandoffRequest,
    session: DbSession,
    actor: RequireActor,
) -> HandoffOut:
    return await IdeathonService(session).send_handoff(
        ideathon_id, body, actor
    )


@router.post("/{ideathon_id}/complete", summary="Mark ideathon complete")
async def complete(
    ideathon_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> dict:
    return await IdeathonService(session).complete(ideathon_id, actor)
