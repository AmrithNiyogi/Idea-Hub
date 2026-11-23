"""Ideathon Pitch agent wiring: input shape, pass-through outputs, and configuration gaps."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services import ideathon_pitch_service as pitch

IDEATHON = uuid.UUID("12345678-1234-1234-1234-123456789abc")
PITCH_AGENT = "48a8b05d-5b26-485d-a5cd-9a4df7105fd7"


def test_pitch_input_defaults_to_both_stages() -> None:
    assert pitch.build_pitch_input(IDEATHON) == {"ideathon_id": str(IDEATHON), "stage": "both"}


def test_pitch_input_passes_through_cluster_and_rank_outputs() -> None:
    payload = pitch.build_pitch_input(
        IDEATHON,
        stage="pitch",
        clusters=[{"label": "Support", "ideaIds": ["a"], "keyTerms": ["triage"]}],
        shortlist_suggestion=[{"ideaId": "a", "rank": 1}],
    )
    assert payload["stage"] == "pitch"
    assert payload["clusters"] == [{"label": "Support", "ideaIds": ["a"], "keyTerms": ["triage"]}]
    assert payload["shortlistSuggestion"] == [{"ideaId": "a", "rank": 1}]


def test_pitch_agent_id_is_read_from_its_own_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_PITCH", PITCH_AGENT)
    assert studio.resolve_kompass_agent_id("ideathon-pitch") == PITCH_AGENT


@pytest.mark.asyncio
async def test_missing_agent_id_returns_error_without_calling_kompass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_PITCH", "")
    execute = AsyncMock()
    monkeypatch.setattr(studio, "execute_run", execute)
    result = await pitch.propose_pitch(IDEATHON)
    assert result.success is False
    assert "AISTUDIO_AGENT_IDEATHON_PITCH" in (result.error or "")
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_propose_pitch_calls_execute_with_pitch_agent_and_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_PITCH", PITCH_AGENT)
    execute = AsyncMock(return_value=studio.ExecuteResult(success=True, result_text="{}"))
    monkeypatch.setattr(studio, "execute_run", execute)
    result = await pitch.propose_pitch(IDEATHON, stage="handoff")
    assert result.success is True
    execute.assert_awaited_once_with(
        agent_id=PITCH_AGENT,
        input_payload={"ideathon_id": str(IDEATHON), "stage": "handoff"},
        conversation_id=None,
        tool_auth_token=None,
    )
