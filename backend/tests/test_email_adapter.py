"""SMTP adapter — OTP and notification email helpers (SMTP mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.config.settings import settings
from app.services import email_adapter


def test_delivery_address_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OTP_EMAIL_OVERRIDE", "ops@example.com")
    assert email_adapter._delivery_address("user@example.com") == "ops@example.com"
    monkeypatch.setattr(settings, "OTP_EMAIL_OVERRIDE", None)
    assert email_adapter._delivery_address("user@example.com") == "user@example.com"


def test_notify_delivery_address_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NOTIFY_EMAIL_OVERRIDE", "n@example.com")
    monkeypatch.setattr(settings, "OTP_EMAIL_OVERRIDE", "o@example.com")
    assert email_adapter._notify_delivery_address("u@example.com") == "n@example.com"
    monkeypatch.setattr(settings, "NOTIFY_EMAIL_OVERRIDE", None)
    assert email_adapter._notify_delivery_address("u@example.com") == "o@example.com"
    monkeypatch.setattr(settings, "OTP_EMAIL_OVERRIDE", None)
    assert email_adapter._notify_delivery_address("u@example.com") == "u@example.com"


def test_app_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173")
    assert email_adapter._app_link("/ideas/1").endswith("/ideas/1")


def test_send_login_otp_dev_without_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM", "")
    ok = email_adapter.send_login_otp_email(
        email="priya@dotkonnekt.example", otp="123456", user_name="Priya"
    )
    assert ok is True


def test_send_login_otp_nondev_requires_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENV", "prod")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM", "")
    ok = email_adapter.send_login_otp_email(
        email="priya@dotkonnekt.example", otp="123456", user_name="Priya"
    )
    assert ok is False


def test_send_login_otp_smtp_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_FROM", "noreply@example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_SECURITY", "STARTTLS")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "u")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(settings, "OTP_EMAIL_OVERRIDE", None)

    with patch.object(email_adapter, "_send_smtp") as send:
        ok = email_adapter.send_login_otp_email(
            email="priya@dotkonnekt.example", otp="654321", user_name="Priya"
        )
    assert ok is True
    send.assert_called_once()


def test_send_login_otp_smtp_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_FROM", "noreply@example.com")
    with patch.object(
        email_adapter, "_send_smtp", side_effect=RuntimeError("boom")
    ):
        ok = email_adapter.send_login_otp_email(
            email="priya@dotkonnekt.example", otp="654321", user_name="Priya"
        )
    assert ok is False


def test_send_event_notification_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NOTIFY_EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_FROM", "noreply@example.com")
    with patch.object(email_adapter, "_send_smtp") as send:
        ok = email_adapter.send_event_notification_email(
            intended_email="elena@dotkonnekt.example",
            user_name="Elena",
            kind="decision",
            kind_label="Decision",
            summary="Idea accepted",
            href="/ideas/1",
            idea_title="Ship it",
            is_follower=True,
        )
    assert ok is True
    send.assert_called_once()


def test_send_smtp_uses_ssl_and_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_SECURITY", "SSL")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(settings, "SMTP_FROM", "from@example.com")

    ssl_client = MagicMock()
    ssl_client.__enter__ = MagicMock(return_value=ssl_client)
    ssl_client.__exit__ = MagicMock(return_value=False)
    with patch(
        "app.services.email_adapter.smtplib.SMTP_SSL", return_value=ssl_client
    ):
        email_adapter._send_smtp(
            to_addr="to@example.com",
            subject="s",
            text_body="t",
            html_body="<p>h</p>",
        )
    ssl_client.send_message.assert_called_once()

    monkeypatch.setattr(settings, "SMTP_SECURITY", "NONE")
    monkeypatch.setattr(settings, "SMTP_PORT", 25)
    plain = MagicMock()
    plain.__enter__ = MagicMock(return_value=plain)
    plain.__exit__ = MagicMock(return_value=False)
    with patch("app.services.email_adapter.smtplib.SMTP", return_value=plain):
        email_adapter._send_smtp(
            to_addr="to@example.com",
            subject="s",
            text_body="t",
            html_body="<p>h</p>",
        )
    plain.send_message.assert_called_once()
