"""One-time login tickets for post-OTP role selection (Redis).

After password + OTP succeed for a multi-role account, cookies are not set
yet. A short-lived ticket is stored so ``POST /auth/complete-login`` can
issue the session with the chosen ``active_role``.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import HTTPException, status
from redis.exceptions import RedisError

from app.config.settings import settings
from app.db.session import get_redis

logger = logging.getLogger("idea_hub.login_ticket")


def _key(ticket: str) -> str:
    return f"login_ticket:{ticket}"


def _unavailable(exc: RedisError) -> HTTPException:
    logger.error("Redis error in login ticket: %s", exc, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Login is temporarily unavailable",
    )


def issue_ticket(user_id: str) -> str:
    """Store a one-time ticket bound to ``user_id``; return the opaque token."""
    try:
        client = get_redis()
        ticket = secrets.token_urlsafe(32)
        client.set(
            _key(ticket),
            user_id,
            ex=settings.LOGIN_TICKET_TTL_SECONDS,
        )
        return ticket
    except RedisError as exc:
        raise _unavailable(exc) from exc


def consume_ticket(ticket: str) -> str:
    """Validate and delete the ticket; return the bound user id.

    Raises:
        HTTPException: 401 expired/unknown, 503 Redis down.
    """
    if not ticket or not ticket.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login session expired. Sign in again.",
        )
    try:
        client = get_redis()
        key = _key(ticket.strip())
        user_id = client.get(key)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login session expired. Sign in again.",
            )
        client.delete(key)
        return user_id if isinstance(user_id, str) else user_id.decode("utf-8")
    except HTTPException:
        raise
    except RedisError as exc:
        raise _unavailable(exc) from exc
