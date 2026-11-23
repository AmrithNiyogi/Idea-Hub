"""Admin API for service tokens: create, list and revoke. Administrator only.

Responsibilities:
- Issue a token (shown once) with a label and optional expiry.
- List issued tokens with status and last use.
- Revoke a token. A revoked token stops working on the next request.

Side Effects:
- Writes ``service_tokens`` rows. Tokens work only on the agent-internal read routes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import Actor, RequireActor
from app.models.service_token import ServiceToken
from app.schemas.service_tokens import ServiceTokenCreatedOut, ServiceTokenCreateIn, ServiceTokenOut
from app.services import service_token_service as tokens

router = APIRouter(prefix="/admin/service-tokens", tags=["admin"])


def _require_admin(actor: Actor) -> None:
    if not actor.has_role("admin"):
        raise HTTPException(403, "Administrator role required.")


def _out(row: ServiceToken) -> ServiceTokenOut:
    return ServiceTokenOut(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        status=tokens.status_of(row),
        created_at=row.created_at,
        expires_at=row.expires_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
    )


@router.get("", response_model=list[ServiceTokenOut], summary="List service tokens")
async def list_tokens(session: DbSession, actor: RequireActor) -> list[ServiceTokenOut]:
    _require_admin(actor)
    return [_out(row) for row in await tokens.list_all(session)]


@router.post(
    "",
    response_model=ServiceTokenCreatedOut,
    status_code=201,
    summary="Issue a service token (shown once)",
)
async def create_token(
    body: ServiceTokenCreateIn, session: DbSession, actor: RequireActor
) -> ServiceTokenCreatedOut:
    _require_admin(actor)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
        if body.expires_in_days
        else None
    )
    row, plaintext = await tokens.create(
        session, name=body.name, created_by=actor.id, expires_at=expires_at
    )
    await session.commit()
    return ServiceTokenCreatedOut(token=plaintext, record=_out(row))


@router.post(
    "/{token_id}/revoke",
    response_model=ServiceTokenOut,
    summary="Revoke a service token",
)
async def revoke_token(
    token_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> ServiceTokenOut:
    _require_admin(actor)
    row = await tokens.revoke(session, token_id, revoked_by=actor.id)
    await session.commit()
    return _out(row)
