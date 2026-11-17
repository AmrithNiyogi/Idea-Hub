"""Microsoft Teams Incoming Webhook adapter (chat category).

MVP: store an Incoming Webhook URL under Integrations (user or org scope)
and POST MessageCard JSON when scheduling a team meeting (or announcing
an idea update via create_issue).

Create a webhook in Teams: Channel → Connectors → Incoming Webhook → copy URL.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from app.trackers.base import (
    ConnectField,
    ConnectionProbe,
    CreateIssuePayload,
    ExternalIssue,
    RemoteTask,
    UpdateTaskPayload,
)


class TeamsWebhookProvider:
    """Chat adapter: Incoming Webhook for meeting cards / announcements."""

    id = "teams"
    display_name = "Microsoft Teams"
    description = (
        "Post meeting cards and team announcements to a Teams channel "
        "via an Incoming Webhook URL."
    )
    auth_mode = "webhook"
    integration_category = "chat"
    connect_fields = [
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
    ]

    async def validate_connection(
        self, credentials: dict[str, Any]
    ) -> ConnectionProbe:
        url = require_https_webhook(credentials.get("webhook_url"))
        label = (
            str(credentials.get("channel_label") or "").strip() or "Teams webhook"
        )
        return ConnectionProbe(
            display_label=label,
            external_account_id="",
            meta={"webhook_host": urlparse(url).hostname or ""},
        )

    async def create_issue(
        self,
        credentials: dict[str, Any],
        payload: CreateIssuePayload,
    ) -> ExternalIssue:
        """Post an idea announcement card to the Teams channel."""
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": payload.title,
            "themeColor": "5B4BDB",
            "title": payload.title,
            "sections": [
                {
                    "activityTitle": "Idea Hub",
                    "text": (payload.description or "")[:2000] or payload.title,
                    "facts": [
                        {"name": "Idea", "value": payload.idea_id},
                        {"name": "Status", "value": payload.status_hint or "—"},
                    ],
                    "markdown": True,
                }
            ],
            "potentialAction": (
                [
                    {
                        "@type": "OpenUri",
                        "name": "Open in Idea Hub",
                        "targets": [
                            {"os": "default", "uri": payload.idea_url}
                        ],
                    }
                ]
                if payload.idea_url
                else []
            ),
        }
        result = await post_webhook(credentials, card)
        eid = str(uuid4())
        return ExternalIssue(
            external_id=eid,
            url=payload.idea_url or "",
            key=eid[:8],
            raw=result,
        )

    async def resolve_existing(
        self,
        credentials: dict[str, Any],
        external_id_or_url: str,
    ) -> ExternalIssue:
        _ = credentials
        raise ValueError(
            "Teams Incoming Webhook does not support linking existing messages. "
            "Use Schedule meeting from the idea team space instead."
        )

    async def get_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
    ) -> RemoteTask:
        _ = credentials, external_id
        raise ValueError("Teams Incoming Webhook cannot fetch live message state.")

    async def update_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask:
        _ = credentials, external_id, payload
        raise ValueError("Teams Incoming Webhook cannot update posted messages.")


# Backward-compatible alias used by team_space_service helpers
TEAMS = TeamsWebhookProvider()


def require_https_webhook(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Webhook URL must be a valid https:// URL.")
    return url


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
    facts = [{"name": "When", "value": when}]
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
    url = require_https_webhook(credentials.get("webhook_url"))
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload)
    text = (resp.text or "")[:300]
    if resp.status_code >= 400:
        raise ValueError(f"Teams webhook returned {resp.status_code}: {text}")
    return {"status_code": resp.status_code, "body": text}


# Legacy name used in earlier drafts
validate_connection = TeamsWebhookProvider().validate_connection
