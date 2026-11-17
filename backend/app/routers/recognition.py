"""Recognition HTTP API — Phase 3.

TODO: wire into main via ``include_phase23_routers(app)``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.recognition import (
    AwardOut,
    BadgeOut,
    ConfirmAnnualRequest,
    ConfirmIoqRequest,
    LeaderboardRowOut,
    LedgerEntryOut,
    LevelOut,
    RulesOut,
)
from app.services.recognition_service import RecognitionService

router = APIRouter(prefix="/recognition", tags=["recognition"])


@router.get(
    "/rules",
    response_model=RulesOut,
    summary="Points rules, levels, and badge catalog",
)
async def get_rules(session: DbSession, actor: RequireActor) -> RulesOut:
    return await RecognitionService(session).rules()


@router.get(
    "/leaderboard",
    response_model=list[LeaderboardRowOut],
    summary="Public points leaderboard",
)
async def leaderboard(
    session: DbSession,
    actor: RequireActor,
    limit: int = Query(50, ge=1, le=200),
) -> list[LeaderboardRowOut]:
    return await RecognitionService(session).leaderboard(limit=limit)


@router.get(
    "/badges",
    response_model=list[BadgeOut],
    summary="Badge catalog",
)
async def badges(session: DbSession, actor: RequireActor) -> list[BadgeOut]:
    return await RecognitionService(session).badges_catalog()


@router.get(
    "/awards",
    response_model=list[AwardOut],
    summary="Confirmed IoQ and Annual awards",
)
async def awards(session: DbSession, actor: RequireActor) -> list[AwardOut]:
    return await RecognitionService(session).list_awards()


@router.post(
    "/awards/ioq",
    response_model=AwardOut,
    status_code=201,
    summary="Confirm Idea of the Quarter",
)
async def confirm_ioq(
    body: ConfirmIoqRequest, session: DbSession, actor: RequireActor
) -> AwardOut:
    return await RecognitionService(session).confirm_ioq(body, actor)


@router.post(
    "/awards/annual",
    response_model=AwardOut,
    status_code=201,
    summary="Confirm Annual Innovation Award",
)
async def confirm_annual(
    body: ConfirmAnnualRequest, session: DbSession, actor: RequireActor
) -> AwardOut:
    return await RecognitionService(session).confirm_annual(body, actor)


@router.get(
    "/users/{user_id}/ledger",
    response_model=list[LedgerEntryOut],
    summary="Points ledger for a user",
)
async def user_ledger(
    user_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[LedgerEntryOut]:
    return await RecognitionService(session).ledger(user_id, actor)


@router.get(
    "/users/{user_id}/level",
    response_model=LevelOut,
    summary="Level for a user",
)
async def user_level(
    user_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> LevelOut:
    return await RecognitionService(session).level(user_id)
