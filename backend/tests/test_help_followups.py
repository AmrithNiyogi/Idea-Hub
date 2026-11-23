"""Help agent follow-up questions: cleanup from the agent reply and simulated suggestions."""

from __future__ import annotations

from app.services import agent_simulate_service as simulate
from app.services.agent_live_turns import clean_followups


def test_clean_followups_keeps_three_unique_non_empty_questions() -> None:
    raw = [" How do I submit? ", "", "How do I submit?", "Next?", "Another?", "Fourth?"]
    assert clean_followups(raw) == ["How do I submit?", "Next?", "Another?"]


def test_clean_followups_ignores_non_list_values() -> None:
    assert clean_followups(None) == []
    assert clean_followups("How do I submit?") == []


def test_simulated_submit_reply_has_followups() -> None:
    out = simulate.help_turn(message="how do I submit an idea")
    assert out["topic"] == "submit"
    assert out["followups"], "submit topic should suggest follow-up questions"
    assert len(out["followups"]) <= 3


def test_simulated_fallback_suggests_followups() -> None:
    out = simulate.help_turn(message="what is the weather today")
    assert out["topic"] == "fallback"
    assert out["followups"]
