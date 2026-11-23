"""SMTP delivery for login OTP and domain-event notification emails.

Primary path: STARTTLS SMTP using ``SMTP_*`` settings.

OTP: when ``OTP_EMAIL_OVERRIDE`` is set, delivery goes there while the
authenticated login email is named in the body. On ``ENV=dev``, the OTP is
also printed to the console as a backup. Callers treat a ``False`` return as
hard failure (discard the stored OTP).

Notifications: when ``NOTIFY_EMAIL_ENABLED``, high-signal events are emailed.
Delivery To is ``NOTIFY_EMAIL_OVERRIDE`` falling back to ``OTP_EMAIL_OVERRIDE``,
then the intended account email. The intended recipient and event details are
always named in the body.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from html import escape
from typing import Any
from urllib.parse import urljoin

from app.config.settings import settings
from app.utils.email_layout import (
    TEXT_FOOTER,
    code_box,
    format_duration,
    notice,
    paragraph,
    render_email,
    source_address,
)

logger = logging.getLogger("idea_hub.email")


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def _delivery_address(account_email: str) -> str:
    override = (settings.OTP_EMAIL_OVERRIDE or "").strip()
    return override or account_email


def _notify_delivery_address(intended_email: str) -> str:
    """Resolve SMTP To for domain notifications (override chain)."""
    for candidate in (
        settings.NOTIFY_EMAIL_OVERRIDE,
        settings.OTP_EMAIL_OVERRIDE,
    ):
        value = (candidate or "").strip()
        if value:
            return value
    return intended_email


def _app_link(href: str) -> str:
    """Build an absolute frontend URL from an app-relative path."""
    base = (settings.FRONTEND_ORIGIN or "").rstrip("/") + "/"
    path = href.lstrip("/") if href else ""
    return urljoin(base, path)


def _log_console_backup(*, account_email: str, delivery_to: str, otp: str, user_name: str) -> None:
    """Print OTP to stdout/logs in dev so local login still works if SMTP lags."""
    message = (
        f"\n========== IdeaKonnekt login OTP ==========\n"
        f"Account: {account_email}\n"
        f"Delivered To: {delivery_to}\n"
        f"Hi {user_name},\n"
        f"Your verification code is: {otp}\n"
        f"It expires in {format_duration(settings.LOGIN_OTP_TTL_SECONDS)}.\n"
        f"========================================\n"
    )
    print(message, flush=True)
    logger.info(
        "Login OTP for account=%s delivered_to=%s: %s",
        account_email,
        delivery_to,
        otp,
    )


def _build_bodies(*, account_email: str, otp: str, user_name: str) -> tuple[str, str, str]:
    """Build subject, plain text, and HTML for a login OTP.

    Returns:
        ``(subject, text_body, html_body)``.
    """
    expires_in = format_duration(settings.LOGIN_OTP_TTL_SECONDS)
    app_name = settings.APP_NAME or "IdeaKonnekt"
    subject = f"Your {app_name} login verification code"

    override_note_html = ""
    override_note_text = ""
    if (settings.OTP_EMAIL_OVERRIDE or "").strip():
        override_note_html = paragraph(
            f"Login attempted for account <strong>{escape(account_email)}</strong>."
        )
        override_note_text = f"Login attempted for account: {account_email}\n\n"

    html_body = render_email(
        "Verify your login",
        paragraph(f"Hello <strong>{escape(user_name)}</strong>,")
        + override_note_html
        + paragraph(f"Use this code to finish signing in to <strong>{escape(app_name)}</strong>:")
        + code_box(otp)
        + (
            f'<p style="margin: 0 0 16px; font-size: 13px; color: #6B6075; text-align: center;">'
            f"This code expires in {expires_in} and can be used once.</p>"
        )
        + notice(
            "Didn't try to sign in? Someone may know your password &mdash; "
            "please change it right away and never share this code."
        ),
        preheader=f"Your {app_name} verification code expires in {expires_in}.",
    )

    text_body = f"""
Hello {user_name},

{override_note_text}Use this code to finish signing in to {app_name}:

{otp}

This code expires in {expires_in} and can be used once.

Didn't try to sign in? Someone may know your password - please change it right away and never share this code.

{TEXT_FOOTER}
"""
    return subject, text_body.strip(), html_body


def _send_smtp(*, to_addr: str, subject: str, text_body: str, html_body: str) -> None:
    """Send a multipart message via SMTP; raises on transport/auth failure."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = source_address()
    msg["To"] = to_addr
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    security = settings.SMTP_SECURITY
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    timeout = 15

    if security == "SSL":
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as client:
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as client:
        if security == "STARTTLS":
            client.starttls()
        if settings.SMTP_USERNAME:
            client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        client.send_message(msg)


def send_login_otp_email(*, email: str, otp: str, user_name: str) -> bool:
    """Deliver a login OTP over SMTP (with optional recipient override).

    Authenticating callers still pass the real account ``email``; when
    ``OTP_EMAIL_OVERRIDE`` is set, delivery goes there and the account email is
    mentioned in the message body.

    Args:
        email: Authenticated account email (not necessarily the SMTP To).
        otp: Six-digit verification code (plaintext only at the edge).
        user_name: Display name for the greeting.

    Returns:
        True when SMTP accepted the message; False on misconfiguration or send error.
        In ``dev``, also logs the OTP to the console regardless of SMTP outcome
        once a code has been generated (console is backup; SMTP remains primary).

    Side Effects:
        - Opens an SMTP connection to ``SMTP_HOST``.
        - May print the OTP to stdout when ``ENV=dev``.
    """
    delivery_to = _delivery_address(email)

    if settings.ENV == "dev":
        _log_console_backup(
            account_email=email,
            delivery_to=delivery_to,
            otp=otp,
            user_name=user_name,
        )

    if not _smtp_configured():
        logger.error(
            "SMTP not configured (SMTP_HOST / SMTP_FROM required); cannot send OTP"
        )
        # Dev-only escape hatch: console backup counts as success so local login works
        # without SMTP. Non-dev environments must send real email.
        return settings.ENV == "dev"

    subject, text_body, html_body = _build_bodies(
        account_email=email, otp=otp, user_name=user_name
    )
    try:
        _send_smtp(
            to_addr=delivery_to,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception:
        logger.exception(
            "Failed to send login OTP via SMTP to %s (account=%s)",
            delivery_to,
            email,
        )
        return False

    logger.info(
        "Login OTP email sent to %s (account=%s)",
        delivery_to,
        email,
    )
    return True


def send_event_notification_email(
    *,
    intended_email: str,
    user_name: str,
    kind: str,
    kind_label: str,
    summary: str,
    href: str,
    idea_title: str | None = None,
    is_follower: bool = False,
    meta: dict[str, Any] | None = None,
) -> bool:
    """Send a high-signal IdeaKonnekt event email via the OTP SMTP stack.

    Always names the intended recipient in the body. When an override is
    configured, SMTP ``To`` is the override address (same pattern as OTP).

    Args:
        intended_email: Real account that should receive the alert in production.
        user_name: Display name for the greeting.
        kind: Stable event kind (decision, collab, …).
        kind_label: Human subject prefix.
        summary: Short body matching the in-app notification text.
        href: App-relative deep link.
        idea_title: Optional idea title for subject/context.
        is_follower: When True, copy notes that they follow the idea.
        meta: Optional extras (unused in template today; reserved).

    Returns:
        True when SMTP accepted the message (or ``ENV=dev`` without SMTP).
        False on misconfiguration or send error. Never raises to callers.

    Side Effects:
        Opens an SMTP connection when configured.
    """
    del meta  # reserved for richer templates
    if not settings.NOTIFY_EMAIL_ENABLED:
        return False

    delivery_to = _notify_delivery_address(intended_email)
    app_name = settings.APP_NAME or "IdeaKonnekt"
    link = _app_link(href)
    title_bit = f" — {idea_title}" if idea_title else ""
    subject = f"{app_name}: {kind_label}{title_bit}"

    follow_note_html = ""
    follow_note_text = ""
    if is_follower and idea_title:
        follow_note_html = paragraph(
            f"You follow <strong>{escape(idea_title)}</strong>, so you get "
            "updates when something important happens."
        )
        follow_note_text = (
            f'You follow "{idea_title}", so you get updates when something '
            "important happens.\n\n"
        )
    elif is_follower:
        follow_note_html = paragraph(
            "You follow this idea, so you get updates when something important happens."
        )
        follow_note_text = (
            "You follow this idea, so you get updates when something important happens.\n\n"
        )

    override_note_html = ""
    override_note_text = ""
    if delivery_to.lower() != intended_email.lower():
        override_note_html = paragraph(
            f"Intended recipient: <strong>{escape(user_name)}</strong> "
            f"(&lt;{escape(intended_email)}&gt;)."
        )
        override_note_text = (
            f"Intended recipient: {user_name} <{intended_email}>\n\n"
        )

    html_body = render_email(
        kind_label,
        paragraph(f"Hello <strong>{escape(user_name)}</strong>,")
        + override_note_html
        + follow_note_html
        + paragraph(escape(summary))
        + (
            f'<p style="margin: 16px 0; text-align: center;">'
            f'<a href="{escape(link)}" style="display: inline-block; '
            f"background-color: #7663F2; color: #FFFCFC; text-decoration: none; "
            f'font-weight: bold; padding: 12px 24px; border-radius: 8px;">'
            f"Open in {escape(app_name)}</a></p>"
        )
        + paragraph(
            f'<span style="font-size: 13px; color: #6B6075;">Or open: '
            f'<a href="{escape(link)}" style="color: #4A35B1;">{escape(link)}</a></span>'
        ),
        preheader=summary[:140],
    )

    text_body = f"""
Hello {user_name},

{override_note_text}{follow_note_text}{summary}

Open in {app_name}:
{link}

{TEXT_FOOTER}
""".strip()

    if settings.ENV == "dev":
        print(
            f"\n========== IdeaKonnekt notification ==========\n"
            f"Kind: {kind}\n"
            f"Intended: {intended_email}\n"
            f"Delivered To: {delivery_to}\n"
            f"Subject: {subject}\n"
            f"{summary}\n"
            f"Link: {link}\n"
            f"===========================================\n",
            flush=True,
        )

    if not _smtp_configured():
        logger.warning(
            "SMTP not configured; skipped notification email kind=%s intended=%s",
            kind,
            intended_email,
        )
        return settings.ENV == "dev"

    try:
        _send_smtp(
            to_addr=delivery_to,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception:
        logger.exception(
            "Failed to send notification email kind=%s to %s (intended=%s)",
            kind,
            delivery_to,
            intended_email,
        )
        return False

    logger.info(
        "Notification email sent kind=%s to %s (intended=%s)",
        kind,
        delivery_to,
        intended_email,
    )
    return True
