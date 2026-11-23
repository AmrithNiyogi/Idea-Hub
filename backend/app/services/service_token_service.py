"""Issue, verify, list and revoke service tokens.

Responsibilities:
- Generate tokens with the ``ikst_`` prefix and store only their SHA-256 hash.
- Verify a presented token: exists, not revoked, not expired. Records ``last_used_at``.
- Admin list and revoke.

Side Effects:
- Writes ``service_tokens`` rows. ``verify`` commits the ``last_used_at`` update, at most every 5 minutes per token.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_token import ServiceToken

TOKEN_PREFIX = "ikst_"
LAST_USED_WRITE_INTERVAL = timedelta(minutes=5)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_service_token(token: str | None) -> bool:
    """True when the presented credential has the service-token form."""
    return token is not None and token.startswith(TOKEN_PREFIX)


async def create(
    session: AsyncSession,
    *,
    name: str,
    created_by: uuid.UUID,
    expires_at: Optional[datetime] = None,
) -> tuple[ServiceToken, str]:
    """Issue a token. Returns the stored row and the plaintext, which is never stored."""
    plaintext = TOKEN_PREFIX + secrets.token_urlsafe(32)
    row = ServiceToken(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        name=name.strip(),
        token_hash=_hash(plaintext),
        prefix=plaintext[:12],
        created_by=created_by,
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()
    return row, plaintext


async def verify(session: AsyncSession, token: str) -> ServiceToken | None:
    """The live token row for this credential, or None if unknown, revoked or expired."""
    if not is_service_token(token):
        return None
    row = (
        await session.execute(select(ServiceToken).where(ServiceToken.token_hash == _hash(token)))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return None
    now = datetime.now(timezone.utc)
    if row.expires_at is not None and row.expires_at <= now:
        return None
    if row.last_used_at is None or now - row.last_used_at > LAST_USED_WRITE_INTERVAL:
        row.last_used_at = now
        await session.commit()
    return row


async def list_all(session: AsyncSession) -> list[ServiceToken]:
    """Every issued token, newest first, revoked ones included."""
    rows = await session.execute(select(ServiceToken).order_by(ServiceToken.created_at.desc()))
    return list(rows.scalars().all())


async def revoke(session: AsyncSession, token_id: uuid.UUID, *, revoked_by: uuid.UUID) -> ServiceToken:
    """Revoke a token. Revoking twice keeps the first revocation time."""
    row = await session.get(ServiceToken, token_id)
    if row is None:
        raise HTTPException(404, "Service token not found.")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        row.revoked_by = revoked_by
    await session.flush()
    return row


def status_of(row: ServiceToken, now: datetime | None = None) -> str:
    """active, expired or revoked. Revoked wins over expired."""
    current = now or datetime.now(timezone.utc)
    if row.revoked_at is not None:
        return "revoked"
    if row.expires_at is not None and row.expires_at <= current:
        return "expired"
    return "active"
