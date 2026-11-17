"""Stub-path tests for agent_live_turns (no network)."""

from __future__ import annotations

import pytest

from app.services import agent_live_turns as L
from app.services import aistudio_execute_client as studio


@pytest.mark.asyncio
async def test_help_turn_uses_simulate_when_not_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(studio, "use_live_execute", lambda: False)
    out = await L.help_turn(message="How do I submit an idea?")
    assert out["simulated"] is True
    assert "submit" in out["reply"].lower() or out["topic"] == "submit"
    assert out.get("conversation_id") is None


@pytest.mark.asyncio
async def test_help_turn_echoes_conversation_id_in_simulate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(studio, "use_live_execute", lambda: False)
    out = await L.help_turn(message="roles?", conversation_id="thread-1")
    assert out["conversation_id"] == "thread-1"


@pytest.mark.asyncio
async def test_live_help_requires_agent_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(studio, "use_live_execute", lambda: True)
    monkeypatch.setattr(studio, "resolve_kompass_agent_id", lambda _k: None)
    with pytest.raises(Exception) as exc:
        await L.help_turn(message="hi")
    assert getattr(exc.value, "status_code", None) == 503
