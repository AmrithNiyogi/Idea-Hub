"""Login OTP service — Redis HMAC storage mirroring Kompass admin.

Keys:
  - ``login_otp:{user_id}`` hash fields ``hash``, ``attempts`` (TTL 600s)
  - ``login_otp_cooldown:{user_id}`` SET NX EX 60s resend gate
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets

from fastapi import HTTPException, status
from redis.exceptions import RedisError

from app.config.settings import settings
from app.db.session import get_redis

logger = logging.getLogger("idea_hub.login_otp")


def _otp_key(user_id: str) -> str:
    return f"login_otp:{user_id}"


def _cooldown_key(user_id: str) -> str:
    return f"login_otp_cooldown:{user_id}"


def _hash_otp(user_id: str, otp: str) -> str:
    return hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        f"{user_id}:{otp}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _unavailable(exc: RedisError) -> HTTPException:
    logger.error("Redis error in login OTP: %s", exc, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Login verification is temporarily unavailable",
    )


def issue_otp(user_id: str) -> str:
    """Generate and store a new OTP, resetting attempts.

    Raises:
        HTTPException: 429 inside resend cooldown, 503 if Redis is down.
    """
    try:
        client = get_redis()
        acquired = client.set(
            _cooldown_key(user_id),
            "1",
            nx=True,
            ex=settings.LOGIN_OTP_RESEND_COOLDOWN_SECONDS,
        )
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait before requesting another code",
            )

        otp = f"{secrets.randbelow(1_000_000):06d}"
        key = _otp_key(user_id)
        pipe = client.pipeline()
        pipe.delete(key)
        pipe.hset(key, mapping={"hash": _hash_otp(user_id, otp), "attempts": 0})
        pipe.expire(key, settings.LOGIN_OTP_TTL_SECONDS)
        pipe.execute()
        return otp
    except HTTPException:
        raise
    except RedisError as exc:
        raise _unavailable(exc) from exc


def discard_otp(user_id: str) -> None:
    """Drop stored OTP and cooldown (e.g. when email send failed)."""
    try:
        get_redis().delete(_otp_key(user_id), _cooldown_key(user_id))
    except RedisError as exc:
        logger.warning("Could not discard login OTP: %s", exc)


def verify_otp(user_id: str, otp: str) -> None:
    """Verify submitted OTP; consume on success.

    Raises:
        HTTPException: 401 wrong/expired, 429 too many attempts, 503 Redis down.
    """
    try:
        client = get_redis()
        key = _otp_key(user_id)
        stored = client.hget(key, "hash")
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Verification code expired. Request a new one.",
            )

        attempts = client.hincrby(key, "attempts", 1)
        if attempts > settings.LOGIN_OTP_MAX_ATTEMPTS:
            client.delete(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect codes. Request a new one.",
            )

        if not hmac.compare_digest(stored, _hash_otp(user_id, otp)):
            if attempts >= settings.LOGIN_OTP_MAX_ATTEMPTS:
                client.delete(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many incorrect codes. Request a new one.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification code",
            )

        client.delete(key, _cooldown_key(user_id))
    except HTTPException:
        raise
    except RedisError as exc:
        raise _unavailable(exc) from exc
