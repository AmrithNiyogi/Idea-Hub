"""Authenticator-app MFA (TOTP) — enrollment, login verify, disable.

Architecture:
  - Shared secrets are Fernet-encrypted at rest (key derived from JWT_SECRET_KEY).
  - Pending enrollment secrets live in Redis until confirm (or TTL expiry).
  - Login may verify either Redis email OTP or TOTP; this module owns TOTP only.

Must never:
  - Return the decrypted secret after enrollment is confirmed.
  - Log raw secrets or otpauth URIs in production logs.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
from typing import Any

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import get_redis
from app.models.user import User
from app.services import auth_service

logger = logging.getLogger("idea_hub.totp")

_SETUP_KEY_PREFIX = "totp_setup:"
_SETUP_TTL_SECONDS = 600
_TOTP_VALID_WINDOW = 1  # ±1 step (±30s)


def _fernet() -> Fernet:
    """Build a Fernet cipher from the JWT secret (stable across process restarts)."""
    digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    """Encrypt a TOTP base32 secret for column storage."""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a stored TOTP secret.

    Raises:
        HTTPException: 500 if the ciphertext is corrupt or the key changed.
    """
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        logger.error("TOTP secret decrypt failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticator configuration is invalid. Contact an admin.",
        ) from exc


def _setup_key(user_id: str) -> str:
    return f"{_SETUP_KEY_PREFIX}{user_id}"


def _otpauth_uri(*, secret: str, email: str) -> str:
    issuer = settings.APP_NAME or "KonnektIdea"
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def _qr_png_base64(otpauth_uri: str) -> str:
    """Render a PNG QR code as a base64 string (no data: prefix)."""
    img = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def verify_code(secret: str, code: str) -> bool:
    """Return True if ``code`` is a valid TOTP for ``secret`` within the window."""
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code, valid_window=_TOTP_VALID_WINDOW))


def user_has_password(user: User) -> bool:
    """Return True when the account has a usable local password path.

    Microsoft SSO-only users are created with ``has_password=False`` and a
    random unusable hash. Linked seed/password accounts keep ``True``.

    Args:
        user: ORM or ORM-like user with optional ``has_password``.

    Returns:
        bool: Defaults to True when the attribute is missing (legacy fixtures).
    """
    return bool(getattr(user, "has_password", True))


def require_password_for_mfa(user: User) -> None:
    """Reject TOTP enroll/confirm/disable for SSO-only accounts.

    Raises:
        HTTPException: 403 when ``has_password`` is false.
    """
    if not user_has_password(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Authenticator MFA is not available for Microsoft SSO-only "
                "accounts. Use password login (or set a password) to enable MFA."
            ),
        )


async def begin_setup(session: AsyncSession, user: User) -> dict[str, Any]:
    """Start TOTP enrollment: mint a secret, stash in Redis, return QR material.

    Does not enable MFA until ``confirm_setup`` succeeds. Replaces any prior
    pending setup for the user. SSO-only accounts (``has_password=False``)
    are rejected.

    Args:
        session: Async SQLAlchemy session (unused; reserved for future audit).
        user: Authenticated user beginning enrollment.

    Returns:
        dict with secret, otpauth_uri, qr_png_base64, and expires_in_seconds.

    Raises:
        HTTPException: 403 SSO-only; 400 if MFA already enabled; 503 if Redis is down.

    Side Effects:
        Writes ``totp_setup:{user_id}`` in Redis with TTL.
    """
    del session  # enrollment is Redis-staged until confirm
    require_password_for_mfa(user)
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticator MFA is already enabled. Disable it first.",
        )
    secret = pyotp.random_base32()
    uri = _otpauth_uri(secret=secret, email=user.email)
    try:
        get_redis().setex(_setup_key(str(user.id)), _SETUP_TTL_SECONDS, secret)
    except RedisError as exc:
        logger.error("Redis error storing TOTP setup: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MFA setup is temporarily unavailable",
        ) from exc
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_png_base64": _qr_png_base64(uri),
        "expires_in_seconds": _SETUP_TTL_SECONDS,
    }


async def confirm_setup(
    session: AsyncSession, user: User, code: str
) -> User:
    """Verify a code against the pending secret and enable MFA on the user.

    Args:
        session: Async SQLAlchemy session.
        user: Authenticated user confirming enrollment.
        code: 6-digit authenticator code.

    Returns:
        User: Updated ORM user with totp_enabled=True.

    Raises:
        HTTPException: 403 SSO-only; 400 expired/missing setup or already
            enabled; 401 bad code.

    Side Effects:
        Persists encrypted secret, sets totp_enabled, deletes Redis setup key.
    """
    require_password_for_mfa(user)
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticator MFA is already enabled",
        )
    try:
        client = get_redis()
        key = _setup_key(str(user.id))
        secret = client.get(key)
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA setup expired. Start setup again.",
            )
        if isinstance(secret, bytes):
            secret = secret.decode("utf-8")
        if not verify_code(secret, code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authenticator code",
            )
        user.totp_secret = encrypt_secret(secret)
        user.totp_enabled = True
        await session.commit()
        await session.refresh(user)
        client.delete(key)
        logger.info("TOTP MFA enabled for %s", user.email)
        return user
    except HTTPException:
        raise
    except RedisError as exc:
        logger.error("Redis error confirming TOTP setup: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MFA setup is temporarily unavailable",
        ) from exc


async def disable_totp(
    session: AsyncSession,
    user: User,
    *,
    password: str,
    code: str,
) -> User:
    """Disable MFA after verifying password and a current authenticator code.

    Args:
        session: Async SQLAlchemy session.
        user: Authenticated user disabling MFA.
        password: Current account password.
        code: Current 6-digit TOTP code.

    Returns:
        User: Updated ORM user with MFA cleared.

    Raises:
        HTTPException: 403 SSO-only; 400 if MFA not enabled; 401 bad password
            or code.

    Side Effects:
        Clears totp_secret / totp_enabled and any pending Redis setup key.
    """
    require_password_for_mfa(user)
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticator MFA is not enabled",
        )
    if not auth_service.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    plain = decrypt_secret(user.totp_secret)
    if not verify_code(plain, code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticator code",
        )
    user.totp_secret = None
    user.totp_enabled = False
    await session.commit()
    await session.refresh(user)
    try:
        get_redis().delete(_setup_key(str(user.id)))
    except RedisError as exc:
        logger.warning("Could not clear TOTP setup key: %s", exc)
    logger.info("TOTP MFA disabled for %s", user.email)
    return user


def verify_user_totp(user: User, code: str) -> None:
    """Verify a login authenticator code for an enrolled user.

    Raises:
        HTTPException: 401 if MFA is not enabled or the code is wrong.
    """
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticator MFA is not enabled for this account",
        )
    plain = decrypt_secret(user.totp_secret)
    if not verify_code(plain, code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticator code",
        )


def mfa_status(user: User) -> dict[str, Any]:
    """Return public MFA flags for the signed-in user (never the secret).

    Includes ``has_password`` / ``mfa_available`` so clients can hide enroll UI
    for Microsoft SSO-only accounts without guessing from the password hash.
    """
    has_pw = user_has_password(user)
    return {
        "totp_enabled": bool(user.totp_enabled),
        "totp_pending_setup": _has_pending_setup(str(user.id)) if has_pw else False,
        "has_password": has_pw,
        "mfa_available": has_pw,
    }


def _has_pending_setup(user_id: str) -> bool:
    try:
        return bool(get_redis().exists(_setup_key(user_id)))
    except RedisError:
        return False


def admin_clear_totp(user: User) -> None:
    """Clear MFA fields without a TOTP code (admin / lockout recovery).

    Caller must persist the session. Does not verify password or TOTP.
    """
    user.totp_secret = None
    user.totp_enabled = False
