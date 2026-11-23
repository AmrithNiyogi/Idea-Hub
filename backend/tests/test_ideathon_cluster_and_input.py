"""Ideathon Cluster agent wiring, and the string form of the Kompass run input."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services import ideathon_cluster_service as cluster

IDEATHON = uuid.UUID("12345678-1234-1234-1234-123456789abc")
CLUSTER_AGENT = "c72b31ab-a23d-4e9b-a08c-272f9e8dea2e"


def test_cluster_input_is_the_ideathon_and_stage() -> None:
    assert cluster.build_cluster_input(IDEATHON) == {"ideathon_id": str(IDEATHON), "stage": "cluster"}


def test_structured_input_is_sent_as_a_json_string() -> None:
    text = studio._input_text({"ideathon_id": "x", "weights": {"panel": 0.7}})
    assert isinstance(text, str)
    assert json.loads(text) == {"ideathon_id": "x", "weights": {"panel": 0.7}}


def test_string_input_is_sent_unchanged() -> None:
    assert studio._input_text("already text") == "already text"


@pytest.mark.asyncio
async def test_missing_cluster_agent_id_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_CLUSTER", "")
    execute = AsyncMock()
    monkeypatch.setattr(studio, "execute_run", execute)
    result = await cluster.propose_cluster(IDEATHON)
    assert result.success is False
    assert "AISTUDIO_AGENT_IDEATHON_CLUSTER" in (result.error or "")
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_propose_cluster_calls_the_cluster_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_CLUSTER", CLUSTER_AGENT)
    execute = AsyncMock(return_value=studio.ExecuteResult(success=True, result_text="{}"))
    monkeypatch.setattr(studio, "execute_run", execute)
    result = await cluster.propose_cluster(IDEATHON, tool_auth_token="user-token")
    assert result.success is True
    execute.assert_awaited_once_with(
        agent_id=CLUSTER_AGENT,
        input_payload={"ideathon_id": str(IDEATHON), "stage": "cluster"},
        conversation_id=None,
        tool_auth_token="user-token",
    )
