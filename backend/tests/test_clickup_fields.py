"""ClickUp priority / due_date / assignee mapping helpers."""

from __future__ import annotations

import pytest

from app.trackers.clickup import (
    _clickup_priority_value,
    _iso_date_to_ms,
    _ms_to_iso_date,
    _parse_clickup_priority,
    _task_from_clickup,
)


def test_priority_parse_object() -> None:
    name, pid, color = _parse_clickup_priority(
        {"id": "1", "priority": "urgent", "color": "#f50000"}
    )
    assert name == "urgent"
    assert pid == "1"
    assert color == "#f50000"


def test_priority_value_roundtrip() -> None:
    assert _clickup_priority_value("high") == 2
    assert _clickup_priority_value("3") == 3
    assert _clickup_priority_value("") is None
    with pytest.raises(ValueError):
        _clickup_priority_value("critical")


def test_due_date_ms_roundtrip() -> None:
    ms = _iso_date_to_ms("2026-12-01")
    assert _ms_to_iso_date(ms) == "2026-12-01"
    assert _ms_to_iso_date(None) == ""
    assert _ms_to_iso_date("2026-11-17T00:00:00Z") == "2026-11-17"


def test_task_from_clickup_includes_editable_and_assignees() -> None:
    remote = _task_from_clickup(
        {
            "id": "14znrcgnj49",
            "name": "Demo",
            "status": {"status": "to do", "color": "#d3d3d3", "type": "open"},
            "priority": {"id": "3", "priority": "normal", "color": "#6fddff"},
            "due_date": str(_iso_date_to_ms("2026-11-20")),
            "assignees": [
                {
                    "id": 123,
                    "username": "Ada",
                    "email": "ada@example.com",
                    "profilePicture": "https://example.com/a.png",
                }
            ],
            "url": "https://app.clickup.com/t/14znrcgnj49",
        },
        "14znrcgnj49",
        [],
        assignable=[],
    )
    assert remote.priority == "normal"
    assert remote.due_date == "2026-11-20"
    assert remote.assignees[0].email == "ada@example.com"
    assert remote.assignees[0].avatar_url.endswith("a.png")
    assert "assignees" in remote.editable_fields
    assert len(remote.priority_options) == 4
