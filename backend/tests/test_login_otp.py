"""Login OTP service — Redis HMAC store with FakeRedis."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config.settings import settings
from app.services import login_otp_service
from tests.conftest import FakeRedis


def test_issue_and_verify_otp(fake_redis: FakeRedis) -> None:
    user_id = "user-otp-1"
    otp = login_otp_service.issue_otp(user_id)
    assert len(otp) == 6 and otp.isdigit()
    login_otp_service.verify_otp(user_id, otp)
    # consumed
    with pytest.raises(HTTPException) as exc:
        login_otp_service.verify_otp(user_id, otp)
    assert exc.value.status_code == 401


def test_issue_otp_cooldown(fake_redis: FakeRedis) -> None:
    user_id = "user-otp-2"
    login_otp_service.issue_otp(user_id)
    with pytest.raises(HTTPException) as exc:
        login_otp_service.issue_otp(user_id)
    assert exc.value.status_code == 429


def test_verify_wrong_otp_then_lockout(fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LOGIN_OTP_MAX_ATTEMPTS", 2)
    user_id = "user-otp-3"
    login_otp_service.issue_otp(user_id)
    with pytest.raises(HTTPException) as exc:
        login_otp_service.verify_otp(user_id, "000000")
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc2:
        login_otp_service.verify_otp(user_id, "000000")
    assert exc2.value.status_code == 429


def test_discard_otp(fake_redis: FakeRedis) -> None:
    user_id = "user-otp-4"
    login_otp_service.issue_otp(user_id)
    login_otp_service.discard_otp(user_id)
    with pytest.raises(HTTPException) as exc:
        login_otp_service.verify_otp(user_id, "123456")
    assert exc.value.status_code == 401


def test_issue_otp_redis_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    boom = MagicMock(side_effect=RedisError("down"))
    monkeypatch.setattr("app.services.login_otp_service.get_redis", boom)
    with pytest.raises(HTTPException) as exc:
        login_otp_service.issue_otp("u")
    assert exc.value.status_code == 503


def test_verify_otp_redis_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    boom = MagicMock(side_effect=RedisError("down"))
    monkeypatch.setattr("app.services.login_otp_service.get_redis", boom)
    with pytest.raises(HTTPException) as exc:
        login_otp_service.verify_otp("u", "123456")
    assert exc.value.status_code == 503


def test_discard_otp_swallows_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.delete.side_effect = RedisError("down")
    monkeypatch.setattr(
        "app.services.login_otp_service.get_redis", lambda: client
    )
    login_otp_service.discard_otp("u")  # must not raise
