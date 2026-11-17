"""Unit tests for idea status transition helpers."""

from __future__ import annotations

import pytest

from app.constants.lifecycle import (
    DECISION_OUTCOME_MAP,
    can_transition,
)


@pytest.mark.parametrize(
    ("from_status", "to_status", "ok"),
    [
        ("draft", "submitted", True),
        ("draft", "accepted", False),
        ("submitted", "under_review", True),
        ("submitted", "withdrawn", True),
        ("under_review", "accepted", True),
        ("under_review", "needs_info", True),
        ("under_review", "prototype", False),
        ("needs_info", "under_review", True),
        ("accepted", "prototype", True),
        ("merged", "accepted", False),
        ("unknown", "draft", False),
    ],
)
def test_can_transition(from_status: str, to_status: str, ok: bool) -> None:
    assert can_transition(from_status, to_status) is ok


def test_decision_outcome_map_covers_ui_verbs() -> None:
    assert DECISION_OUTCOME_MAP["accept"] == "accepted"
    assert DECISION_OUTCOME_MAP["info"] == "needs_info"
    assert set(DECISION_OUTCOME_MAP) == {
        "accept",
        "park",
        "merge",
        "decline",
        "info",
    }
