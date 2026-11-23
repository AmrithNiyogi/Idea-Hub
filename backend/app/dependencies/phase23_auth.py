"""Auth dependency bridge for Phase 2+3 routers.

Prefers the spine JWT cookie dependency (``get_current_user``). Falls back
to ``X-User-Id`` / ``X-Roles`` / ``X-Active-Role`` headers for local calls
when spine auth cannot resolve a session.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


@dataclass
class Actor:
    """Minimal authenticated principal used by Phase 2+3 services."""

    id: uuid.UUID
    roles: list[str] = field(default_factory=list)
    active_role: str = "contributor"
    name: str = ""
    email: str = ""
    raw: Any = None

    def has_role(self, *wanted: str) -> bool:
        role_set = {r.lower() for r in self.roles}
        if self.active_role:
            role_set.add(self.active_role.lower())
        return any(w.lower() in role_set for w in wanted)


def _normalize(user: Any) -> Actor:
    if isinstance(user, Actor):
        return user
    if isinstance(user, dict):
        uid = user.get("id")
        roles = list(user.get("roles") or [])
        active = user.get("active_role") or (roles[0] if roles else "contributor")
        return Actor(
            id=uid if isinstance(uid, uuid.UUID) else uuid.UUID(str(uid)),
            roles=[str(r) for r in roles],
            active_role=str(active),
            name=str(user.get("name") or ""),
            email=str(user.get("email") or ""),
            raw=user,
        )
    uid = getattr(user, "id")
    roles = list(getattr(user, "roles", None) or [])
    active = getattr(user, "active_role", None) or (
        roles[0] if roles else "contributor"
    )
    return Actor(
        id=uid if isinstance(uid, uuid.UUID) else uuid.UUID(str(uid)),
        roles=[str(r) for r in roles],
        active_role=str(active),
        name=str(getattr(user, "name", "") or ""),
        email=str(getattr(user, "email", "") or ""),
        raw=user,
    )


async def get_actor(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_roles: Annotated[str | None, Header(alias="X-Roles")] = None,
    x_active_role: Annotated[str | None, Header(alias="X-Active-Role")] = None,
) -> Actor:
    """Resolve current actor via spine auth if present, else header stub."""
    try:
        from app.dependencies.auth import resolve_user_from_request

        user = await resolve_user_from_request(request, session)
        if user is not None:
            return _normalize(user)
    except Exception:  # noqa: BLE001 — spine not ready
        pass

    if not x_user_id:
        # Say which case it is, so a tool caller can see whether a token arrived at all.
        from app.dependencies.auth import _extract_access_token

        if not _extract_access_token(request):
            detail = "No access token received (cookie or X-Authorization header)."
        else:
            detail = "The access token was received but is invalid or expired. Sign in again."
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    try:
        uid = uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id must be a UUID",
        ) from exc
    roles = [
        r.strip() for r in (x_roles or "contributor").split(",") if r.strip()
    ]
    active = (x_active_role or (roles[0] if roles else "contributor")).strip()
    return Actor(id=uid, roles=roles, active_role=active)


RequireActor = Annotated[Actor, Depends(get_actor)]
