"""Reopen conditions HTTP API — Phase 6."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.reopen import (
    MarkManualIn,
    ReopenDecideIn,
    ReopenProposalOut,
    ReopenSetIn,
    ReopenStateOut,
)
from app.services.reopen_service import ReopenService

router = APIRouter(prefix="/reopen", tags=["reopen"])


@router.post(
    "",
    response_model=ReopenStateOut,
    summary="Create or replace reopen conditions on a parked/declined idea",
)
async def upsert(
    body: ReopenSetIn, session: DbSession, actor: RequireActor
) -> ReopenStateOut:
    return await ReopenService(session).upsert_set(body, actor)


@router.get(
    "/proposals",
    response_model=list[ReopenProposalOut],
    summary="Ideas whose reopen conditions are satisfied",
)
async def proposals(
    session: DbSession, actor: RequireActor
) -> list[ReopenProposalOut]:
    return await ReopenService(session).proposals()


@router.get(
    "/{idea_id}",
    response_model=ReopenStateOut,
    summary="Evaluate reopen conditions for an idea",
)
async def state(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> ReopenStateOut:
    return await ReopenService(session).state_for(idea_id)


@router.post(
    "/{idea_id}/mark-manual",
    response_model=ReopenStateOut,
    summary="Confirm a manual reopen condition",
)
async def mark_manual(
    idea_id: uuid.UUID,
    body: MarkManualIn,
    session: DbSession,
    actor: RequireActor,
) -> ReopenStateOut:
    return await ReopenService(session).mark_manual(idea_id, body, actor)


@router.post(
    "/{idea_id}/approve",
    response_model=dict,
    summary="Approve reopen — move idea to under_review",
)
async def approve(
    idea_id: uuid.UUID,
    body: ReopenDecideIn,
    session: DbSession,
    actor: RequireActor,
) -> dict[str, Any]:
    return await ReopenService(session).approve(idea_id, body, actor)


@router.post(
    "/{idea_id}/dismiss",
    response_model=dict,
    summary="Dismiss reopen proposal (snooze)",
)
async def dismiss(
    idea_id: uuid.UUID,
    body: ReopenDecideIn,
    session: DbSession,
    actor: RequireActor,
) -> dict[str, Any]:
    return await ReopenService(session).dismiss(idea_id, body, actor)
