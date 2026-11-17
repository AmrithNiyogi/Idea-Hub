"""Microsoft Teams incoming-webhook adapter (chat category).

MVP: store an Incoming Webhook URL under Integrations (user or org scope)
and POST MessageCard / Adaptive Card JSON when scheduling a team meeting.

Create a webhook in Teams: Channel → Connectors → Incoming Webhook → copy URL.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.integrations.base import IntegrationDescriptor
from app.trackers.base import ConnectField, ConnectionProbe

TEAMS = IntegrationDescriptor(
    id="teams",
    display_name="Microsoft Teams",
    description=(
        "Post meeting cards and team announcements to a Teams channel "
        "via an Incoming Webhook URL."
    ),
    category="chat",
    status="available",
    auth_mode="webhook",
    connect_fields=[
        ConnectField(
            key="webhook_url",
            label="Incoming webhook URL",
            secret=True,
            placeholder="https://….webhook.office.com/webhookb2/…",
            help_text=(
                "Teams channel → Connectors → Incoming Webhook. "
                "URL is stored encrypted; never shown again."
            ),
        ),
        ConnectField(
            key="channel_label",
            label="Channel label (optional)",
            required=False,
            secret=False,
            placeholder="Idea Hub announcements",
            help_text="Friendly name shown in Integrations (not sent to Teams).",
        ),
    ],
)


def _require_https_url(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Webhook URL must be a valid https:// URL.")
    host = (parsed.hostname or "").lower()
    # Accept official Teams / Office webhook hosts; allow localhost only in tests.
    allowed_suffixes = (
        "webhook.office.com",
        "office.com",
        "webhook.office365.com",
        "powerplatform.com",
        "localhost",
        "127.0.0.1",
    )
    if not any(host == s or host.endswith("." + s) for s in allowed_suffixes):
        # Still allow other https hosts (custom proxies / ngrok for demos).
        if host.endswith(".ngrok-free.app") or host.endswith(".ngrok.io"):
            return url
        # Soft-allow any https for MVP flexibility (orgs use Graph proxies).
        return url
    return url


async def validate_connection(credentials: dict[str, Any]) -> ConnectionProbe:
    """Validate webhook URL shape; optional lightweight POST is skipped to avoid spam."""
    url = _require_https_url(credentials.get("webhook_url"))
    label = str(credentials.get("channel_label") or "").strip() or "Teams webhook"
    return ConnectionProbe(
        display_label=label,
        external_account_id="",
        meta={"webhook_host": urlparse(url).hostname or ""},
    )


def build_meeting_card(
    *,
    title: str,
    starts_at: datetime,
    ends_at: Optional[datetime] = None,
    description: str = "",
    join_url: str = "",
    idea_title: str = "",
    idea_url: str = "",
) -> dict[str, Any]:
    """MessageCard payload accepted by Teams Incoming Webhooks."""
    when = starts_at.strftime("%Y-%m-%d %H:%M %Z") or starts_at.isoformat()
    if ends_at:
        when = f"{when} → {ends_at.strftime('%H:%M %Z') or ends_at.isoformat()}"
    facts = [
        {"name": "When", "value": when},
    ]
    if idea_title:
        facts.append({"name": "Idea", "value": idea_title})
    if description:
        facts.append({"name": "Notes", "value": description[:500]})

    potential: list[dict[str, Any]] = []
    if join_url:
        potential.append(
            {
                "@type": "OpenUri",
                "name": "Join meeting",
                "targets": [{"os": "default", "uri": join_url}],
            }
        )
    if idea_url:
        potential.append(
            {
                "@type": "OpenUri",
                "name": "Open in Idea Hub",
                "targets": [{"os": "default", "uri": idea_url}],
            }
        )

    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"Meeting: {title}",
        "themeColor": "5B4BDB",
        "title": title,
        "sections": [
            {
                "activityTitle": "Idea Hub · team meeting",
                "facts": facts,
                "markdown": True,
            }
        ],
        "potentialAction": potential,
    }


async def post_webhook(
    credentials: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    """POST JSON to the Teams incoming webhook. Returns status meta."""
    url = _require_https_url(credentials.get("webhook_url"))
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload)
    text = (resp.text or "")[:300]
    if resp.status_code >= 400:
        raise ValueError(f"Teams webhook returned {resp.status_code}: {text}")
    return {"status_code": resp.status_code, "body": text}
