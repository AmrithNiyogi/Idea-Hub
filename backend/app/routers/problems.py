"""Problem radar HTTP API — Phase 6."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.problems import (
    MeTooOut,
    ProblemHeadlineOut,
    ProblemMetaIn,
    ProblemOut,
)
from app.services.problem_service import ProblemService

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get(
    "",
    response_model=list[ProblemOut],
    summary="List recurring problem clusters",
)
async def list_problems(
    session: DbSession,
    actor: RequireActor,
    state: Optional[str] = None,
    sort: str = Query("raised"),
) -> list[ProblemOut]:
    return await ProblemService(session).list_problems(
        actor, state=state, sort=sort
    )


@router.get(
    "/headline",
    response_model=ProblemHeadlineOut,
    summary="Problem radar headline counts",
)
async def headline(
    session: DbSession, actor: RequireActor
) -> ProblemHeadlineOut:
    return await ProblemService(session).headline(actor)


@router.get(
    "/by-idea/{idea_id}",
    response_model=Optional[ProblemOut],
    summary="Problem cluster containing an idea",
)
async def by_idea(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> Optional[ProblemOut]:
    return await ProblemService(session).of_idea(idea_id, actor)


@router.get(
    "/{cluster_key}",
    response_model=ProblemOut,
    summary="Get one problem cluster",
)
async def get_problem(
    cluster_key: str, session: DbSession, actor: RequireActor
) -> ProblemOut:
    return await ProblemService(session).get_problem(cluster_key, actor)


@router.post(
    "/{cluster_key}/me-too",
    response_model=MeTooOut,
    summary="Mark I have this problem too",
)
async def me_too(
    cluster_key: str, session: DbSession, actor: RequireActor
) -> MeTooOut:
    return await ProblemService(session).me_too(cluster_key, actor)


@router.delete(
    "/{cluster_key}/me-too",
    response_model=MeTooOut,
    summary="Remove metoo mark",
)
async def un_me_too(
    cluster_key: str, session: DbSession, actor: RequireActor
) -> MeTooOut:
    return await ProblemService(session).un_me_too(cluster_key, actor)


@router.patch(
    "/{cluster_key}/meta",
    response_model=ProblemOut,
    summary="Leadership rename / sponsor / acknowledge",
)
async def update_meta(
    cluster_key: str,
    body: ProblemMetaIn,
    session: DbSession,
    actor: RequireActor,
) -> ProblemOut:
    return await ProblemService(session).update_meta(cluster_key, body, actor)
