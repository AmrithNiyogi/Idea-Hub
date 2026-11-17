"""Authentication service — credentials, JWT issue/verify, role switch."""

from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.constants.lifecycle import VALID_ROLES
from app.models.user import User
from app.schemas.auth import UserPublic

logger = logging.getLogger("idea_hub.auth")


def _slug_from_email(email: str) -> str:
    """Derive a URL-safe slug candidate from the email local-part."""
    local = email.split("@", 1)[0].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", local).strip("-")[:48]
    return slug or "user"


async def _unique_slug(session: AsyncSession, base: str) -> str:
    """Return ``base`` or ``base-<suffix>`` that does not collide in users.slug."""
    candidate = base
    for _ in range(12):
        existing = await session.execute(
            select(User.id).where(User.slug == candidate)
        )
        if existing.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base[:40]}-{secrets.token_hex(3)}"
    return f"{base[:32]}-{uuid.uuid4().hex[:8]}"


async def upsert_microsoft_user(
    session: AsyncSession, *, email: str, name: str
) -> User:
    """Link or create a user for a validated Microsoft SSO identity.

    Existing users (including seed accounts) are matched by normalized email
    and signed in as-is (``has_password`` unchanged — linked password accounts
    keep MFA eligibility). New emails get an active account with the configured
    default role, ``has_password=False``, and a random unusable password hash.

    Args:
        session: Async SQLAlchemy session.
        email: Verified email from the Microsoft id_token.
        name: Display name from OIDC claims.

    Returns:
        User: Active ORM user ready for JWT issuance.

    Raises:
        HTTPException: 401 if the matched account is disabled.

    Side Effects:
        May insert a new ``users`` row and commit the session.
    """
    normalized = email.strip().lower()
    user = await get_user_by_email(session, normalized)
    if user is not None:
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
            )
        # Refresh display name if Microsoft sent a non-empty name and ours is blank.
        if name and (not user.name or user.name == normalized.split("@", 1)[0]):
            user.name = name
            await session.commit()
            await session.refresh(user)
        return user

    role = (settings.MICROSOFT_DEFAULT_ROLE or "contributor").strip()
    if role not in VALID_ROLES:
        role = "contributor"
    slug = await _unique_slug(session, _slug_from_email(normalized))
    user = User(
        id=uuid.uuid4(),
        email=normalized,
        password_hash=hash_password(secrets.token_urlsafe(48)),
        has_password=False,
        name=name or normalized.split("@", 1)[0],
        title="",
        team_id=None,
        roles=[role],
        primary_role=role,
        status="active",
        avatar=(abs(hash(normalized)) % 8) + 1,
        slug=slug,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("Created Microsoft SSO user %s role=%s", normalized, role)
    return user


def hash_password(password: str) -> str:
    """Return a bcrypt hash for storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time password check against a stored bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Load a user by normalized email."""
    result = await session.execute(
        select(User).where(User.email == email.strip().lower())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Load a user by primary key."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_credentials(
    session: AsyncSession, email: str, password: str
) -> User:
    """Validate email/password without issuing tokens.

    Raises:
        HTTPException: 401 invalid credentials or disabled account.
    """
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )
    return user


def create_access_token(
    user: User, *, active_role: str | None = None
) -> str:
    """Issue a short-lived access JWT with roles + active_role claims."""
    roles = list(user.roles or [])
    role = active_role or user.primary_role or (roles[0] if roles else "contributor")
    if role not in roles and roles:
        role = user.primary_role if user.primary_role in roles else roles[0]
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "email": user.email,
        "roles": roles,
        "active_role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Issue a long-lived refresh JWT."""
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT of the expected type.

    Raises:
        HTTPException: 403 expired, 401 invalid/wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != expected_type or not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return payload
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token expired",
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


def user_to_public(user: User, *, active_role: str | None = None) -> UserPublic:
    """Map ORM user to API-safe public shape."""
    roles = [str(r) for r in (user.roles or [])]
    role = active_role or user.primary_role or (roles[0] if roles else "contributor")
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        title=user.title or "",
        team_id=user.team_id,
        roles=roles,
        primary_role=user.primary_role,
        active_role=role,
        status=user.status,
        avatar=user.avatar,
        avatar_url=getattr(user, "avatar_url", None),
        slug=user.slug,
        totp_enabled=bool(getattr(user, "totp_enabled", False)),
        has_password=bool(getattr(user, "has_password", True)),
    )


def issue_login_tokens(
    user: User, *, active_role: str | None = None
) -> dict[str, Any]:
    """Create access + refresh tokens and sanitized user payload."""
    role = active_role or user.primary_role
    return {
        "access_token": create_access_token(user, active_role=role),
        "refresh_token": create_refresh_token(user.id),
        "user": user_to_public(user, active_role=role),
    }


async def refresh_access_token(
    session: AsyncSession, refresh_token: str
) -> tuple[str, UserPublic]:
    """Validate refresh token and mint a new access token."""
    payload = decode_token(refresh_token, "refresh")
    user = await get_user_by_id(session, uuid.UUID(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )
    access = create_access_token(user)
    return access, user_to_public(user)


async def switch_role(
    session: AsyncSession, user: User, role: str, current_active: str
) -> dict[str, Any]:
    """Re-issue access token with a new active_role the user holds.

    Refresh token is unchanged; only access token is rotated.
    """
    del current_active  # reserved for future audit
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown role: {role}",
        )
    roles = [str(r) for r in (user.roles or [])]
    if role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not hold the {role} role",
        )
    # Touch session so SQLAlchemy identity map stays consistent
    await session.refresh(user)
    access = create_access_token(user, active_role=role)
    return {
        "access_token": access,
        "user": user_to_public(user, active_role=role),
        "role": role,
    }
