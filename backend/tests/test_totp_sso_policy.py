"""SSO-only accounts must not enroll or manage authenticator MFA."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock

from app.services import totp_service


def test_mfa_status_sso_only(make_user) -> None:
    user = make_user(has_password=False, totp_enabled=False)
    status = totp_service.mfa_status(user)
    assert status["has_password"] is False
    assert status["mfa_available"] is False
    assert status["totp_enabled"] is False
    assert status["totp_pending_setup"] is False


def test_mfa_status_password_user(make_user) -> None:
    user = make_user(has_password=True)
    status = totp_service.mfa_status(user)
    assert status["has_password"] is True
    assert status["mfa_available"] is True


@pytest.mark.asyncio
async def test_begin_setup_rejects_sso_only(make_user) -> None:
    user = make_user(has_password=False)
    with pytest.raises(HTTPException) as exc:
        await totp_service.begin_setup(AsyncMock(), user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_confirm_setup_rejects_sso_only(make_user) -> None:
    user = make_user(has_password=False)
    with pytest.raises(HTTPException) as exc:
        await totp_service.confirm_setup(AsyncMock(), user, "123456")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_disable_totp_rejects_sso_only(make_user) -> None:
    user = make_user(
        has_password=False,
        totp_enabled=True,
        totp_secret="cipher",
    )
    with pytest.raises(HTTPException) as exc:
        await totp_service.disable_totp(
            AsyncMock(), user, password="x", code="123456"
        )
    assert exc.value.status_code == 403
