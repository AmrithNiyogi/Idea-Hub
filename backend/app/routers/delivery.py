"""Delivery HTTP API — Phase 2.

Mounted at ``/api/v1`` by ``phase23_register.include_phase23_routers``.

TODO: wire into main — call ``include_phase23_routers(app)`` from spine
``main.py`` (or include this router directly).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.delivery import (
    ContributorAdd,
    DeliveryDetailOut,
    DeliveryUpdateCreate,
    HoursDecideRequest,
    HoursLogCreate,
    HoursRequestCreate,
    HoursRequestOut,
    MarkImplementedRequest,
    TaskCreate,
    TaskOut,
    TaskStatusUpdate,
    TaskUpdate,
    VerifyImpactRequest,
)
from app.services.delivery_service import DeliveryService

router = APIRouter(tags=["delivery"])


@router.get(
    "/ideas/{idea_id}/delivery",
    response_model=DeliveryDetailOut,
    summary="Get delivery tab for an idea",
    description=(
        "Returns hours request/grant state, tasks, updates, contributors, "
        "impact entries, credit shares, and the quarterly innovation pool."
    ),
)
async def get_delivery(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> DeliveryDetailOut:
    return await DeliveryService(session).get_delivery(idea_id, actor)


@router.post(
    "/ideas/{idea_id}/delivery/hours-requests",
    response_model=HoursRequestOut,
    status_code=201,
    summary="Request innovation hours",
)
async def request_hours(
    idea_id: uuid.UUID,
    body: HoursRequestCreate,
    session: DbSession,
    actor: RequireActor,
) -> HoursRequestOut:
    return await DeliveryService(session).request_hours(idea_id, body, actor)


@router.get(
    "/delivery/hours-requests",
    response_model=list[HoursRequestOut],
    summary="List innovation-hour requests",
    description=(
        "Leadership/admin Approvals inbox. Pass state=pending for waiting "
        "decisions, or omit to return recent requests of any state."
    ),
)
async def list_hours_requests(
    session: DbSession,
    actor: RequireActor,
    state: str | None = None,
    limit: int = 50,
) -> list[HoursRequestOut]:
    return await DeliveryService(session).list_hours_requests(
        actor, state=state, limit=limit
    )


@router.post(
    "/delivery/hours-requests/{request_id}/decide",
    summary="Approve or decline an hours request",
    description="Leadership/admin only. Approval creates a delivery project and moves the idea to prototype.",
)
async def decide_hours(
    request_id: uuid.UUID,
    body: HoursDecideRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).decide_hours(request_id, body, actor)


@router.post(
    "/ideas/{idea_id}/delivery/hours-log",
    summary="Log hours spent on a prototype",
)
async def log_hours(
    idea_id: uuid.UUID,
    body: HoursLogCreate,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).log_hours(idea_id, body, actor)


@router.post(
    "/ideas/{idea_id}/delivery/contributors",
    status_code=201,
    summary="Add a delivery contributor",
)
async def add_contributor(
    idea_id: uuid.UUID,
    body: ContributorAdd,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).add_contributor(idea_id, body, actor)


@router.delete(
    "/ideas/{idea_id}/delivery/contributors/{user_id}",
    summary="Remove a delivery contributor",
)
async def remove_contributor(
    idea_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).remove_contributor(
        idea_id, user_id, actor
    )


@router.post(
    "/ideas/{idea_id}/delivery/tasks",
    response_model=TaskOut,
    status_code=201,
    summary="Add a delivery task",
)
async def add_task(
    idea_id: uuid.UUID,
    body: TaskCreate,
    session: DbSession,
    actor: RequireActor,
) -> TaskOut:
    return await DeliveryService(session).add_task(idea_id, body, actor)


@router.patch(
    "/delivery/tasks/{task_id}",
    response_model=TaskOut,
    summary="Update a delivery task",
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    session: DbSession,
    actor: RequireActor,
) -> TaskOut:
    return await DeliveryService(session).update_task(task_id, body, actor)


@router.post(
    "/delivery/tasks/{task_id}/status",
    response_model=TaskOut,
    summary="Check off / change task status",
)
async def set_task_status(
    task_id: uuid.UUID,
    body: TaskStatusUpdate,
    session: DbSession,
    actor: RequireActor,
) -> TaskOut:
    return await DeliveryService(session).set_task_status(task_id, body, actor)


@router.post(
    "/ideas/{idea_id}/delivery/updates",
    status_code=201,
    summary="Post a delivery progress update",
)
async def post_update(
    idea_id: uuid.UUID,
    body: DeliveryUpdateCreate,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).post_update(idea_id, body, actor)


@router.post(
    "/ideas/{idea_id}/delivery/mark-implemented",
    summary="Mark idea implemented with impact and credit shares",
)
async def mark_implemented(
    idea_id: uuid.UUID,
    body: MarkImplementedRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).mark_implemented(idea_id, body, actor)


@router.post(
    "/ideas/{idea_id}/delivery/impact/{entry_id}/verify",
    summary="Second-person verify an impact entry",
)
async def verify_impact(
    idea_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: VerifyImpactRequest,
    session: DbSession,
    actor: RequireActor,
) -> dict:
    return await DeliveryService(session).verify_impact(
        idea_id, entry_id, body, actor
    )
