"""Notifications inbox HTTP API.

Endpoints:
- ``GET /notifications`` — newest inbox rows + unread count
- ``GET /notifications/unread-count`` — badge only
- ``POST /notifications/{id}/read`` — mark one read
- ``POST /notifications/read-all`` — mark all read
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.auth import RequireUser
from app.schemas.notifications import (
    MarkReadOut,
    NotificationListOut,
    UnreadCountOut,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationListOut,
    summary="List my notifications",
    description=(
        "Returns newest-first inbox rows for the authenticated user plus the "
        "total unread count for the topbar badge. Read state is persisted in Postgres."
    ),
    responses={401: {"description": "Not authenticated"}},
)
async def list_notifications(
    session: DbSession,
    user: RequireUser,
    limit: int = Query(40, ge=1, le=100, description="Max rows to return."),
    unread_only: bool = Query(
        False, description="When true, return only unread rows."
    ),
) -> NotificationListOut:
    """Fetch the caller's persisted notification inbox."""
    return await NotificationService(session).list_inbox(
        user.id, limit=limit, unread_only=unread_only
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountOut,
    summary="Unread notification count",
    description="Lightweight badge payload without loading the full inbox.",
    responses={401: {"description": "Not authenticated"}},
)
async def unread_count(session: DbSession, user: RequireUser) -> UnreadCountOut:
    """Return unread count for the bell badge."""
    return await NotificationService(session).unread(user.id)


@router.post(
    "/{notif_id}/read",
    response_model=MarkReadOut,
    summary="Mark one notification read",
    description="Marks a single owned notification as read. Idempotent.",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def mark_one_read(
    notif_id: uuid.UUID,
    session: DbSession,
    user: RequireUser,
) -> MarkReadOut:
    """Mark one notification read for the caller."""
    return await NotificationService(session).mark_read(user.id, notif_id)


@router.post(
    "/read-all",
    response_model=MarkReadOut,
    summary="Mark all notifications read",
    description="Flips every unread notification for the caller to read.",
    responses={401: {"description": "Not authenticated"}},
)
async def mark_all_read(session: DbSession, user: RequireUser) -> MarkReadOut:
    """Mark the entire inbox read for the caller."""
    return await NotificationService(session).mark_all_read(user.id)
