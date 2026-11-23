"""Ideathon Draft agent: input shape, reply filtering, and configuration gaps."""

from __future__ import annotations

import pytest

from app.config.settings import settings
from app.services import ideathon_draft_service as draft

OK = "How might we answer customers faster without losing the human touch?"


def test_draft_input_carries_stage_theme_and_existing_ideathons() -> None:
    past = [{"title": "Customers First", "theme": "Delight", "challenges": [OK]}]
    assert draft.build_draft_input("  Delight the customer ", past) == {
        "stage": "draft",
        "theme": "Delight the customer",
        "existing": past,
    }
    assert draft.build_draft_input("Delight")["existing"] == []


def test_usable_challenges_drops_bad_items_and_caps_at_three() -> None:
    parsed = {
        "challenges": [
            "too short",
            OK,
            42,
            "x" * 301,
            OK + " two",
            OK + " three",
            OK + " four",
        ]
    }
    assert draft.usable_challenges(parsed) == [OK, OK + " two", OK + " three"]


def test_usable_challenges_handles_missing_or_wrong_shape() -> None:
    assert draft.usable_challenges({}) == []
    assert draft.usable_challenges({"challenges": "not a list"}) == []


@pytest.mark.asyncio
async def test_propose_draft_reports_missing_agent_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_DRAFT", "")
    result = await draft.propose_draft("Delight the customer")
    assert result.success is False
    assert "AISTUDIO_AGENT_IDEATHON_DRAFT" in (result.error or "")


def test_usable_names_keeps_distinct_valid_names_up_to_four() -> None:
    parsed = {"names": ["  Customers First  ", "ab", "x" * 81, "Customers First", "B2", "Second", "Third", "Fourth", "Fifth"]}
    assert draft.usable_names(parsed) == ["Customers First", "Second", "Third", "Fourth"]
    assert draft.usable_names({}) == []
