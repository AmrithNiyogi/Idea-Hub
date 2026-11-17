"""Collaboration requests + tracker HTTP API — Phase 6."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.collab import (
    CheckinCreateIn,
    CheckinOut,
    CollabCreateIn,
    CollabDecideIn,
    CollabRequestOut,
    MilestoneCreateIn,
    MilestoneOut,
    MilestoneUpdateIn,
    TrackerOut,
)
from app.services.collab_service import CollabService

router = APIRouter(tags=["collab"])


@router.get(
    "/collab/mine",
    response_model=list[CollabRequestOut],
    summary="My collaboration requests",
)
async def mine(session: DbSession, actor: RequireActor) -> list[CollabRequestOut]:
    return await CollabService(session).list_mine(actor)


@router.get(
    "/collab/incoming",
    response_model=list[CollabRequestOut],
    summary="Pending requests on my ideas",
)
async def incoming(
    session: DbSession, actor: RequireActor
) -> list[CollabRequestOut]:
    return await CollabService(session).list_incoming(actor)


@router.get(
    "/ideas/{idea_id}/collab",
    response_model=list[CollabRequestOut],
    summary="Collab requests for an idea",
)
async def for_idea(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[CollabRequestOut]:
    return await CollabService(session).list_for_idea(idea_id)


@router.post(
    "/collab",
    response_model=CollabRequestOut,
    status_code=201,
    summary="Request to co-author or help build",
)
async def create(
    body: CollabCreateIn, session: DbSession, actor: RequireActor
) -> CollabRequestOut:
    return await CollabService(session).create(body, actor)


@router.post(
    "/collab/{request_id}/withdraw",
    response_model=CollabRequestOut,
    summary="Withdraw my pending request",
)
async def withdraw(
    request_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> CollabRequestOut:
    return await CollabService(session).withdraw(request_id, actor)


@router.post(
    "/collab/{request_id}/decide",
    response_model=CollabRequestOut,
    summary="Accept or decline a collab request",
)
async def decide(
    request_id: uuid.UUID,
    body: CollabDecideIn,
    session: DbSession,
    actor: RequireActor,
) -> CollabRequestOut:
    return await CollabService(session).decide(request_id, body, actor)


@router.get(
    "/ideas/{idea_id}/tracker",
    response_model=TrackerOut,
    summary="Team progress tracker for an idea",
)
async def tracker(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> TrackerOut:
    return await CollabService(session).tracker(idea_id)


@router.post(
    "/ideas/{idea_id}/tracker/milestones",
    response_model=MilestoneOut,
    status_code=201,
    summary="Add a tracker milestone",
)
async def add_milestone(
    idea_id: uuid.UUID,
    body: MilestoneCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> MilestoneOut:
    return await CollabService(session).add_milestone(idea_id, body, actor)


@router.patch(
    "/tracker/milestones/{milestone_id}",
    response_model=MilestoneOut,
    summary="Update a tracker milestone",
)
async def update_milestone(
    milestone_id: uuid.UUID,
    body: MilestoneUpdateIn,
    session: DbSession,
    actor: RequireActor,
) -> MilestoneOut:
    return await CollabService(session).update_milestone(
        milestone_id, body, actor
    )


@router.post(
    "/ideas/{idea_id}/tracker/checkins",
    response_model=CheckinOut,
    status_code=201,
    summary="Post a progress check-in",
)
async def add_checkin(
    idea_id: uuid.UUID,
    body: CheckinCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> CheckinOut:
    return await CollabService(session).add_checkin(idea_id, body, actor)
