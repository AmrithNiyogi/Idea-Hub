"""Ideathon Rank agent wiring: input shape, agent id resolution, and configuration gaps."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services import ideathon_rank_service as rank

IDEATHON = uuid.UUID("12345678-1234-1234-1234-123456789abc")
RANK_AGENT = "f5d7f69e-c414-4f45-9183-136ac53b0f0e"


def test_rank_input_carries_ideathon_stage_and_weights() -> None:
    payload = rank.build_rank_input(IDEATHON, {"impact": 0.6, "effort": 0.4})
    assert payload == {
        "ideathon_id": str(IDEATHON),
        "stage": "rank",
        "weights": {"impact": 0.6, "effort": 0.4},
    }


def test_rank_agent_id_is_read_from_its_own_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_RANK", RANK_AGENT)
    assert studio.resolve_kompass_agent_id("ideathon-rank") == RANK_AGENT


@pytest.mark.asyncio
async def test_missing_agent_id_returns_error_without_calling_kompass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_RANK", "")
    execute = AsyncMock()
    monkeypatch.setattr(studio, "execute_run", execute)
    result = await rank.propose_rank(IDEATHON, {"impact": 1.0})
    assert result.success is False
    assert "AISTUDIO_AGENT_IDEATHON_RANK" in (result.error or "")
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_propose_rank_calls_execute_with_rank_agent_and_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_RANK", RANK_AGENT)
    execute = AsyncMock(return_value=studio.ExecuteResult(success=True, result_text="{}"))
    monkeypatch.setattr(studio, "execute_run", execute)
    result = await rank.propose_rank(IDEATHON, {"impact": 1.0})
    assert result.success is True
    execute.assert_awaited_once_with(
        agent_id=RANK_AGENT,
        input_payload={"ideathon_id": str(IDEATHON), "stage": "rank", "weights": {"impact": 1.0}},
        conversation_id=None,
        tool_auth_token=None,
    )
