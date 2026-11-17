"""External tracker HTTP API — Phase 2+3 delivery adjacent.

Mounted at ``/api/v1`` by ``phase23_register.include_phase23_routers``.

Connection CRUD for personal + org defaults also lives under
``/integrations/*`` (see ``routers.integrations``). This module keeps the
tracker-specific catalog and idea link endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.trackers import (
    EffectiveConnectionOut,
    IdeaTrackerLinkCreate,
    IdeaTrackerLinkOut,
    IdeaTrackerRemoteUpdate,
    LiveTrackerTaskOut,
    TrackerConnectionCreate,
    TrackerConnectionOut,
    TrackerProviderOut,
)
from app.services.tracker_service import TrackerService

router = APIRouter(tags=["trackers"])


@router.get(
    "/trackers/providers",
    response_model=list[TrackerProviderOut],
    summary="List registered tracker providers",
    description=(
        "Returns every tracker in the registry (ClickUp, Jira, custom webhook, "
        "and any later-registered TrackerProvider). For the broader catalog "
        "including coming-soon Sheets/Notion/Teams, use GET /integrations/providers."
    ),
)
async def list_providers(
    session: DbSession, actor: RequireActor
) -> list[TrackerProviderOut]:
    _ = actor
    return TrackerService(session).list_providers()


@router.get(
    "/trackers/connections",
    response_model=list[TrackerConnectionOut],
    summary="List my personal tracker connections",
)
async def list_connections(
    session: DbSession, actor: RequireActor
) -> list[TrackerConnectionOut]:
    return await TrackerService(session).list_connections(actor)


@router.get(
    "/trackers/connections/effective",
    response_model=list[EffectiveConnectionOut],
    summary="Effective tracker connection per provider (user → org → none)",
)
async def list_effective(
    session: DbSession, actor: RequireActor
) -> list[EffectiveConnectionOut]:
    return await TrackerService(session).list_effective(
        actor, category="tracker"
    )


@router.post(
    "/trackers/connections",
    response_model=TrackerConnectionOut,
    status_code=201,
    summary="Connect a tracker provider (personal)",
    description=(
        "Validates credentials via the provider, then stores them encrypted "
        "as a personal (user-scope) connection. Prefer Integrations settings "
        "for day-to-day connect/disconnect."
    ),
)
async def connect(
    body: TrackerConnectionCreate,
    session: DbSession,
    actor: RequireActor,
) -> TrackerConnectionOut:
    return await TrackerService(session).connect(body, actor, scope="user")


@router.delete(
    "/trackers/connections/{connection_id}",
    status_code=204,
    summary="Disconnect a personal tracker connection",
)
async def disconnect(
    connection_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> None:
    await TrackerService(session).disconnect(
        connection_id, actor, expect_scope="user"
    )


@router.get(
    "/ideas/{idea_id}/tracker-links",
    response_model=list[IdeaTrackerLinkOut],
    summary="List external tracker links for an idea",
)
async def list_idea_links(
    idea_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> list[IdeaTrackerLinkOut]:
    return await TrackerService(session).list_idea_links(idea_id, actor)


@router.get(
    "/ideas/{idea_id}/tracker-links/live",
    response_model=list[LiveTrackerTaskOut],
    summary="List linked tasks with live data from the remote tracker",
    description=(
        "For each stored idea_tracker_link, fetches the remote task "
        "(title, status, assignees, status options). Failures for a single "
        "link return stored metadata plus an error field."
    ),
)
async def list_live_tasks(
    idea_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> list[LiveTrackerTaskOut]:
    return await TrackerService(session).list_live_tasks(idea_id, actor)


@router.post(
    "/ideas/{idea_id}/tracker-links",
    response_model=IdeaTrackerLinkOut,
    status_code=201,
    summary="Create or link a remote work item for an accepted idea",
    description=(
        "Uses connection_id (personal or org default) or resolves provider_id "
        "via user → organization default."
    ),
)
async def create_or_link(
    idea_id: uuid.UUID,
    body: IdeaTrackerLinkCreate,
    session: DbSession,
    actor: RequireActor,
) -> IdeaTrackerLinkOut:
    return await TrackerService(session).create_or_link(idea_id, body, actor)


@router.get(
    "/ideas/{idea_id}/tracker-links/{link_id}/live",
    response_model=LiveTrackerTaskOut,
    summary="Refresh one linked task from the remote tracker",
)
async def get_live_task(
    idea_id: uuid.UUID,
    link_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> LiveTrackerTaskOut:
    return await TrackerService(session).get_live_task(idea_id, link_id, actor)


@router.patch(
    "/ideas/{idea_id}/tracker-links/{link_id}/remote",
    response_model=LiveTrackerTaskOut,
    summary="Update a remote tracker task (status write-back)",
    description=(
        "Pushes status (and optional title) to ClickUp/Jira/custom webhook, "
        "then returns a fresh live snapshot. ClickUp expects the status name "
        "from the list (not a UUID)."
    ),
)
async def update_remote_task(
    idea_id: uuid.UUID,
    link_id: uuid.UUID,
    body: IdeaTrackerRemoteUpdate,
    session: DbSession,
    actor: RequireActor,
) -> LiveTrackerTaskOut:
    return await TrackerService(session).update_remote_task(
        idea_id, link_id, body, actor
    )


@router.delete(
    "/ideas/{idea_id}/tracker-links/{link_id}",
    status_code=204,
    summary="Remove an external tracker link (does not delete the remote item)",
)
async def unlink(
    idea_id: uuid.UUID,
    link_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> None:
    await TrackerService(session).unlink(idea_id, link_id, actor)
