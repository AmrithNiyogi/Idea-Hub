"""Integrations catalog + tracker builtins + Notion adapter smoke tests."""

from __future__ import annotations

from app.integrations.adapters import get_adapter, list_adapters, resolve_provider
from app.integrations.registry import get_integration, list_integrations
from app.trackers.registry import get_provider


def test_catalog_includes_trackers_notion_and_stubs() -> None:
    ids = {d.id for d in list_integrations()}
    assert {"clickup", "jira", "custom_webhook"} <= ids
    assert {"google_sheets", "notion", "teams"} <= ids


def test_tracker_category_filters() -> None:
    trackers = list_integrations(category="tracker")
    assert all(d.category == "tracker" for d in trackers)
    assert {d.id for d in trackers} >= {"clickup", "jira", "custom_webhook"}
    assert "notion" not in {d.id for d in trackers}


def test_notion_is_available_docs() -> None:
    notion = get_integration("notion")
    assert notion.status == "available"
    assert notion.category == "docs"
    pub = notion.public_dict()
    assert pub["connectable"] is True
    keys = {f["key"] for f in pub["connect_fields"]}
    assert "integration_token" in keys
    assert "parent_page_id" in keys or "database_id" in keys


def test_stubs_are_coming_soon() -> None:
    sheets = get_integration("google_sheets")
    assert sheets.status == "coming_soon"
    assert sheets.category == "sheets"
    assert sheets.public_dict()["connectable"] is False


def test_teams_is_available_chat() -> None:
    teams = get_integration("teams")
    assert teams.status == "available"
    assert teams.category == "chat"
    pub = teams.public_dict()
    assert pub["connectable"] is True
    assert any(f["key"] == "webhook_url" for f in pub["connect_fields"])
    assert resolve_provider("teams").id == "teams"
    assert get_adapter("teams").id == "teams"
    try:
        get_provider("teams")
        raise AssertionError("teams must not be a tracker provider")
    except KeyError:
        pass


def test_clickup_is_connectable() -> None:
    clickup = get_integration("clickup")
    assert clickup.status == "available"
    assert clickup.category == "tracker"
    pub = clickup.public_dict()
    assert pub["connectable"] is True
    assert any(f["key"] == "api_token" for f in pub["connect_fields"])


def test_notion_adapter_not_in_tracker_registry() -> None:
    assert any(a.id == "notion" for a in list_adapters())
    try:
        get_provider("notion")
        raise AssertionError("notion must not be a tracker provider")
    except KeyError:
        pass
    assert resolve_provider("notion").id == "notion"
    assert get_adapter("notion").id == "notion"
