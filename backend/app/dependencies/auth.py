"""Auth dependencies — resolve current user from cookie or Bearer token."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services import auth_service

logger = logging.getLogger("idea_hub.deps.auth")


@dataclass
class CurrentUser:
    """Authenticated principal attached to the request."""

    id: uuid.UUID
    email: str
    name: str
    roles: list[str] = field(default_factory=list)
    active_role: str = "contributor"
    primary_role: str = "contributor"
    title: str = ""
    team_id: uuid.UUID | None = None
    avatar: int = 1
    slug: str = ""
    status: str = "active"
    orm: User | None = None

    def has_role(self, *wanted: str) -> bool:
        role_set = {r.lower() for r in self.roles}
        return any(w.lower() in role_set for w in wanted)

    def acting_as(self, *wanted: str) -> bool:
        return self.active_role.lower() in {w.lower() for w in wanted}


def _extract_access_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token:
        return token
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def resolve_user_from_request(
    request: Request, session: AsyncSession
) -> CurrentUser | None:
    """Resolve the caller from cookie/Bearer without raising.

    Returns:
        CurrentUser when a valid access token is present; otherwise None.
    """
    token = _extract_access_token(request)
    if not token:
        return None
    try:
        payload = auth_service.decode_token(token, "access")
    except HTTPException:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None
    user = await auth_service.get_user_by_id(session, user_id)
    if not user or user.status != "active":
        return None
    roles = [str(r) for r in (user.roles or [])]
    active = str(payload.get("active_role") or user.primary_role or "contributor")
    current = CurrentUser(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=roles,
        active_role=active,
        primary_role=user.primary_role,
        title=user.title or "",
        team_id=user.team_id,
        avatar=user.avatar,
        slug=user.slug,
        status=user.status,
        orm=user,
    )
    request.state.current_user = current
    request.state.user = current
    return current


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser:
    """Require a valid access token (cookie or Authorization Bearer)."""
    user = await resolve_user_from_request(request, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def get_optional_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser | None:
    """Return the current user when authenticated, else None."""
    return await resolve_user_from_request(request, session)


RequireUser = Annotated[CurrentUser, Depends(get_current_user)]
OptionalUser = Annotated[CurrentUser | None, Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def to_actor_dict(user: CurrentUser) -> dict[str, Any]:
    """Shape compatible with Phase 2+3 ``_normalize``."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": user.roles,
        "active_role": user.active_role,
    }
