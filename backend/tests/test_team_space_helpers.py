"""Unit tests for group helpers (slug, meeting card, MCP stub catalog)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.integrations.mcp_client import STUB_TOOL_CATALOG
from app.integrations.teams_webhook import build_meeting_card, require_https_webhook
from app.constants.notification_kinds import EMAIL_KINDS
from app.services.groups_service import _slugify, dm_pair_key


def test_slugify() -> None:
    assert _slugify("General Chat!") == "general-chat"
    assert _slugify("  ") == "channel"


def test_teams_webhook_url() -> None:
    url = require_https_webhook(
        "https://example.webhook.office.com/webhookb2/abc"
    )
    assert url.startswith("https://")
    try:
        require_https_webhook("http://insecure.example/hook")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_meeting_card_shape() -> None:
    card = build_meeting_card(
        title="Sync",
        starts_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        join_url="https://teams.microsoft.com/l/meetup-join/x",
        idea_title="Demo",
        idea_url="http://localhost:5173/ideas/1",
    )
    assert card["@type"] == "MessageCard"
    assert card["title"] == "Sync"
    assert any(a["name"] == "Join meeting" for a in card["potentialAction"])


def test_stub_tools_include_schedule_meeting() -> None:
    names = {t["name"] for t in STUB_TOOL_CATALOG}
    assert "schedule_meeting" in names


def test_dm_pair_key_is_order_independent() -> None:
    import uuid

    a, b = uuid.uuid4(), uuid.uuid4()
    assert dm_pair_key(a, b) == dm_pair_key(b, a)
    assert dm_pair_key(a, b).count(":") == 1


def test_group_invite_emails_by_default() -> None:
    assert "group_invite" in EMAIL_KINDS
