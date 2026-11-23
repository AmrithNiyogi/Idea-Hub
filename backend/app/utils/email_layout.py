"""KonnektIdea branded HTML email layout.

Visual system mirrors the tracing / Kompass admin house style (purple accent
``#7663F2``, ``#F6F2F3`` page background, ``#160922`` near-black text/footer,
tinted code box, amber notice). Copy and footer are KonnektIdea–specific.

This module must stay free of SMTP I/O — callers compose bodies here and send
elsewhere.
"""

from __future__ import annotations

from email.utils import formataddr
from html import escape

from app.config.settings import settings

SENDER_NAME = "KonnektIdea"

TEXT_FOOTER = (
    "KonnektIdea by DotKonnekt\nThis is an automated message, please do not reply."
)


def source_address() -> str:
    """Format the SMTP From header with the KonnektIdea display name.

    Returns:
        RFC 5322 ``From`` value using ``SMTP_FROM``.

    Raises:
        ValueError: When ``SMTP_FROM`` is empty.
    """
    if not settings.SMTP_FROM:
        raise ValueError("SMTP_FROM is not configured")
    return formataddr((SENDER_NAME, settings.SMTP_FROM))


def format_duration(seconds: int) -> str:
    """Render a duration as whole minutes when exact, otherwise as seconds.

    Args:
        seconds: Non-negative duration in seconds.

    Returns:
        Human-readable duration string (e.g. ``10 minutes``, ``45 seconds``).
    """
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute{'' if minutes == 1 else 's'}"
    return f"{seconds} seconds"


def paragraph(html: str) -> str:
    """Wrap trusted HTML in a body paragraph."""
    return f'<p style="margin: 0 0 12px; font-size: 15px; line-height: 1.6;">{html}</p>'


def code_box(value: str) -> str:
    """Large monospaced box for a one-time code.

    Args:
        value: Plain OTP digits; escaped before embedding.
    """
    return (
        '<div style="text-align: center; padding: 12px 0;">'
        '<div style="display: inline-block; background-color: #F0ECFE; border: 1px solid #AB94F3; '
        "border-radius: 12px; padding: 16px 32px; font-family: 'Courier New', Courier, monospace; "
        f'font-size: 34px; font-weight: bold; letter-spacing: 10px; color: #4A35B1;">{escape(value)}</div></div>'
    )


def notice(html: str) -> str:
    """Amber callout for security or expiry warnings."""
    return (
        '<div style="background-color: #FFF8E7; border-left: 4px solid #E6B353; border-radius: 4px; '
        f'padding: 12px 16px; margin: 8px 0 16px; font-size: 13px; line-height: 1.5; color: #5C4410;">{html}</div>'
    )


def render_email(heading: str, body_html: str, *, preheader: str = "") -> str:
    """Wrap body content in the KonnektIdea header bar and footer.

    Inline styles only — email clients do not reliably load ``<style>`` blocks.
    ``preheader`` is a hidden inbox-preview snippet so clients do not concatenate
    visible body text into a run-together preview.

    Args:
        heading: Escaped into the centered ``h1``.
        body_html: Trusted HTML fragments from helpers in this module.
        preheader: Optional inbox preview text.

    Returns:
        Full HTML document string.
    """
    brand = escape(settings.APP_NAME or "KonnektIdea")
    preheader_block = ""
    if preheader:
        preheader_block = (
            '<div style="display: none; max-height: 0; overflow: hidden; opacity: 0; mso-hide: all;">'
            f"{escape(preheader)}"
            "&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;"
            "&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;"
            "&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;"
            "&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;"
            "</div>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<body style="margin: 0; padding: 0; background-color: #F6F2F3; font-family: Arial, Helvetica, sans-serif; color: #160922;">
    {preheader_block}
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F6F2F3; padding: 32px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 560px; background-color: #FFFCFC; border-radius: 16px; overflow: hidden;">
                    <tr><td style="height: 6px; background-color: #7663F2; font-size: 0; line-height: 0;">&nbsp;</td></tr>
                    <tr>
                        <td align="center" style="padding: 32px 32px 8px;">
                            <div style="font-size: 28px; font-weight: bold; letter-spacing: 0.02em; color: #160922;">{brand}</div>
                            <div style="margin-top: 4px; font-size: 12px; color: #6B6075;">by <span style="color: #E6B353;">dot</span>konnekt</div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 16px 40px 32px;">
                            <h1 style="margin: 0 0 16px; font-size: 22px; line-height: 1.3; color: #160922; text-align: center;">{escape(heading)}</h1>
                            {body_html}
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding: 20px 32px; background-color: #160922; font-size: 12px; line-height: 1.6; color: #AB94F3;">
                            {brand} by <span style="color: #E6B353;">dot</span>konnekt<br>
                            This is an automated message, please do not reply.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
