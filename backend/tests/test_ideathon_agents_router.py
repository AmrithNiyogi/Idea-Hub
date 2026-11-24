"""Organiser endpoints for the Ideathon Rank and Pitch agents (gateway mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.config.settings import settings
from app.dependencies.phase23_auth import Actor
from app.routers import ideathon_agents as router
from app.schemas.ideathon_agents import PitchRunIn, RankRunIn
from app.services import aistudio_execute_client as studio
from app.services import ideathon_pitch_service, ideathon_rank_service
from app.services.ideathon_service import IdeathonService

IDEATHON = uuid.UUID("12345678-1234-1234-1234-123456789abc")
RANK_AGENT = "f5d7f69e-c414-4f45-9183-136ac53b0f0e"
PITCH_AGENT = "48a8b05d-5b26-485d-a5cd-9a4df7105fd7"


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_API_BASE_URL", "https://gateway.example")
    monkeypatch.setattr(settings, "AISTUDIO_TENANT_ID", "devtest")
    monkeypatch.setattr(settings, "AISTUDIO_PROJECT_SLUG", "ideakonnekt-idea-hub")
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_RANK", RANK_AGENT)
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_PITCH", PITCH_AGENT)
    monkeypatch.setattr(IdeathonService, "get", AsyncMock(return_value=None))


USER_TOKEN = "user-access-token-for-test"


def _request(token: str | None) -> MagicMock:
    """A request whose cookies hold the signed-in user's access_token (or none)."""
    req = MagicMock()
    req.cookies = {"access_token": token} if token else {}
    return req


def _actor(role: str) -> Actor:
    return Actor(id=uuid.uuid4(), active_role=role)


@pytest.mark.asyncio
async def test_contributor_cannot_run_rank(configured: None) -> None:
    with pytest.raises(HTTPException) as exc:
        await router.run_rank(IDEATHON, RankRunIn(), _request(USER_TOKEN), MagicMock(), _actor("contributor"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_unknown_ideathon_is_not_found(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    monkeypatch.setattr(IdeathonService, "get", AsyncMock(side_effect=HTTPException(404, "Ideathon not found.")))
    with pytest.raises(HTTPException) as exc:
        await router.run_rank(IDEATHON, RankRunIn(), _request(USER_TOKEN), MagicMock(), _actor("leadership"))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_gateway_not_configured_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_API_BASE_URL", "")
    with pytest.raises(HTTPException) as exc:
        await router.run_pitch(IDEATHON, PitchRunIn(), _request(USER_TOKEN), MagicMock(), _actor("admin"))
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_missing_agent_id_returns_503(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_AGENT_IDEATHON_RANK", "")
    with pytest.raises(HTTPException) as exc:
        await router.run_rank(IDEATHON, RankRunIn(), _request(USER_TOKEN), MagicMock(), _actor("leadership"))
    assert exc.value.status_code == 503
    assert "ideathon-rank" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_organiser_rank_run_returns_agent_output(
    monkeypatch: pytest.MonkeyPatch, configured: None
) -> None:
    run = AsyncMock(
        return_value=studio.ExecuteResult(success=True, result_text='{"shortlist": []}', conversation_id="c-1")
    )
    monkeypatch.setattr(ideathon_rank_service, "propose_rank", run)
    monkeypatch.setattr(router.EntryScoringService, "rank_context", AsyncMock(return_value={"entries": []}))
    out = await router.run_rank(IDEATHON, RankRunIn(weights={"impact": 1.0}), _request(USER_TOKEN), MagicMock(), _actor("leadership"))
    assert out.success is True
    assert out.result_text == '{"shortlist": []}'
    assert out.conversation_id == "c-1"
    run.assert_awaited_once_with(
        IDEATHON, {"impact": 1.0}, tool_auth_token=USER_TOKEN, context={"entries": []}
    )


@pytest.mark.asyncio
async def test_upstream_failure_returns_502(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    monkeypatch.setattr(
        ideathon_pitch_service,
        "propose_pitch",
        AsyncMock(return_value=studio.ExecuteResult(success=False, error="gateway timeout")),
    )
    with pytest.raises(HTTPException) as exc:
        await router.run_pitch(IDEATHON, PitchRunIn(stage="pitch"), _request(USER_TOKEN), MagicMock(), _actor("admin"))
    assert exc.value.status_code == 502
    assert exc.value.detail == "gateway timeout"


@pytest.mark.asyncio
async def test_missing_access_token_returns_401(configured: None) -> None:
    with pytest.raises(HTTPException) as exc:
        await router.run_rank(IDEATHON, RankRunIn(), _request(None), MagicMock(), _actor("leadership"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_pitch_forwards_the_callers_token(monkeypatch: pytest.MonkeyPatch, configured: None) -> None:
    run = AsyncMock(return_value=studio.ExecuteResult(success=True, result_text="{}"))
    monkeypatch.setattr(ideathon_pitch_service, "propose_pitch", run)
    await router.run_pitch(IDEATHON, PitchRunIn(stage="both"), _request("caller-token"), MagicMock(), _actor("admin"))
    assert run.await_args is not None
    assert run.await_args.kwargs["tool_auth_token"] == "caller-token"


def test_execute_headers_use_the_per_run_token_over_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_TOOL_AUTH_TOKEN", "fallback-token")
    assert studio.build_execute_headers("caller-token")["X-Authorization"] == "Bearer caller-token"
    assert studio.build_execute_headers()["X-Authorization"] == "Bearer fallback-token"
    assert studio.build_execute_headers("Bearer already")["X-Authorization"] == "Bearer already"
