"""Profiles HTTP API — Phase 3.

TODO: wire into main via ``include_phase23_routers(app)``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.profiles import ProfileOut
from app.services.profile_service import ProfileService

router = APIRouter(tags=["profiles"])


@router.get(
    "/people/{user_id}",
    response_model=ProfileOut,
    summary="Person profile",
    description=(
        "Thin view: submitted / co-authored / implemented ideas, points, "
        "badges, impact summary, ledger excerpt, contribution history."
    ),
)
async def get_profile(
    user_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> ProfileOut:
    return await ProfileService(session).get_profile(user_id, actor)
