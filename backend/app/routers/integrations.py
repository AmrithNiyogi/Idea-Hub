"""Integrations settings API — personal + organization-default connections.

Mounted at ``/api/v1`` by ``phase23_register.include_phase23_routers``.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.trackers import (
    EffectiveConnectionOut,
    IntegrationProviderOut,
    TrackerConnectionCreate,
    TrackerConnectionOut,
)
from app.services.tracker_service import TrackerService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get(
    "/providers",
    response_model=list[IntegrationProviderOut],
    summary="List integration providers (trackers + coming-soon stubs)",
)
async def list_providers(
    session: DbSession,
    actor: RequireActor,
    category: Optional[str] = Query(
        default=None,
        description="Optional filter: tracker | docs | chat | sheets",
    ),
) -> list[IntegrationProviderOut]:
    _ = actor
    return TrackerService(session).list_integrations(category=category)


@router.get(
    "/connections/effective",
    response_model=list[EffectiveConnectionOut],
    summary="Effective connection per provider (user → org → none)",
)
async def list_effective(
    session: DbSession,
    actor: RequireActor,
    category: Optional[str] = Query(default=None),
) -> list[EffectiveConnectionOut]:
    return await TrackerService(session).list_effective(
        actor, category=category
    )


@router.get(
    "/connections",
    response_model=list[TrackerConnectionOut],
    summary="List my personal integration connections",
)
async def list_mine(
    session: DbSession, actor: RequireActor
) -> list[TrackerConnectionOut]:
    return await TrackerService(session).list_connections(actor)


@router.post(
    "/connections",
    response_model=TrackerConnectionOut,
    status_code=201,
    summary="Connect a personal integration (overrides org default)",
)
async def connect_mine(
    body: TrackerConnectionCreate,
    session: DbSession,
    actor: RequireActor,
) -> TrackerConnectionOut:
    return await TrackerService(session).connect(body, actor, scope="user")


@router.delete(
    "/connections/{connection_id}",
    status_code=204,
    summary="Disconnect a personal integration",
)
async def disconnect_mine(
    connection_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> None:
    await TrackerService(session).disconnect(
        connection_id, actor, expect_scope="user"
    )


@router.get(
    "/org/connections",
    response_model=list[TrackerConnectionOut],
    summary="List organization-default connections (admin)",
)
async def list_org(
    session: DbSession, actor: RequireActor
) -> list[TrackerConnectionOut]:
    return await TrackerService(session).list_org_connections(actor)


@router.post(
    "/org/connections",
    response_model=TrackerConnectionOut,
    status_code=201,
    summary="Set or update an organization-default connection (admin)",
)
async def connect_org(
    body: TrackerConnectionCreate,
    session: DbSession,
    actor: RequireActor,
) -> TrackerConnectionOut:
    return await TrackerService(session).connect(
        body, actor, scope="organization"
    )


@router.delete(
    "/org/connections/{connection_id}",
    status_code=204,
    summary="Delete an organization-default connection (admin)",
)
async def disconnect_org(
    connection_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> None:
    await TrackerService(session).disconnect(
        connection_id, actor, expect_scope="organization"
    )
