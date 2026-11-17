"""Integrations catalog + tracker builtins smoke tests."""

from __future__ import annotations

from app.integrations.registry import get_integration, list_integrations


def test_catalog_includes_trackers_and_stubs() -> None:
    ids = {d.id for d in list_integrations()}
    assert {"clickup", "jira", "custom_webhook"} <= ids
    assert {"google_sheets", "notion", "teams"} <= ids


def test_tracker_category_filters() -> None:
    trackers = list_integrations(category="tracker")
    assert all(d.category == "tracker" for d in trackers)
    assert {d.id for d in trackers} >= {"clickup", "jira", "custom_webhook"}


def test_stubs_are_coming_soon() -> None:
    sheets = get_integration("google_sheets")
    assert sheets.status == "coming_soon"
    assert sheets.category == "sheets"
    assert sheets.public_dict()["connectable"] is False


def test_clickup_is_connectable() -> None:
    clickup = get_integration("clickup")
    assert clickup.status == "available"
    assert clickup.category == "tracker"
    pub = clickup.public_dict()
    assert pub["connectable"] is True
    assert any(f["key"] == "api_token" for f in pub["connect_fields"])
