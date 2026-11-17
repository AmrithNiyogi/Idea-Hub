"""HTTP cookie helpers for JWT access/refresh tokens."""

from __future__ import annotations

from fastapi import Response

from app.config.settings import settings


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str | None = None
) -> None:
    """Set httpOnly auth cookies and mirror tokens on response headers."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.headers["access-token"] = access_token

    if refresh_token is not None:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
        )
        response.headers["refresh-token"] = refresh_token


def clear_auth_cookies(response: Response) -> None:
    """Delete auth cookies (logout)."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
