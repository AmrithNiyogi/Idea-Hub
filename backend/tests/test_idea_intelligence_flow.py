"""Idea Intelligence workflow: input mapping, output reading, and the execute call shape."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services import idea_intelligence_flow as flow

IDEA = uuid.UUID("6f1c2a9e-4b7d-4e8a-9c31-2d5f8a7b1e60")


def test_build_inputs_from_idea_row() -> None:
    idea = SimpleNamespace(id=IDEA, title="T", problem="P", solution="S", tags=["support", 3])
    assert flow.build_inputs(idea) == {
        "idea_id": str(IDEA), "title": "T", "problem": "P", "solution": "S", "tags": ["support", "3"],
    }


def test_build_inputs_from_draft_dict_without_id_gets_fresh_uuid() -> None:
    out = flow.build_inputs({"title": "T", "problem": "P", "tags": []})
    uuid.UUID(out["idea_id"])
    assert out["solution"] == ""


def test_flow_configured_needs_slug_and_live_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_INTELLIGENCE", "")
    assert flow.flow_configured() is False
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_INTELLIGENCE", "ideakonnekt-wf-idea-intelligence")
    monkeypatch.setattr(studio, "use_live_execute", lambda: True)
    assert flow.flow_configured() is True
    monkeypatch.setattr(studio, "use_live_execute", lambda: False)
    assert flow.flow_configured() is False


def _patch_post(monkeypatch: pytest.MonkeyPatch, body: dict[str, Any], status: int = 200) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = status
        content = b"x"

        def json(self) -> dict[str, Any]:
            return body

    class FakeClient:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, url: str, headers: Any = None, json: Any = None) -> FakeResponse:
            captured.update(url=url, headers=headers, json=json)
            return FakeResponse()

    monkeypatch.setattr(studio.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(settings, "AISTUDIO_API_BASE_URL", "https://gw.example")
    monkeypatch.setattr(settings, "AISTUDIO_TENANT_ID", "devtest")
    monkeypatch.setattr(settings, "AISTUDIO_PROJECT_SLUG", "idea-hub")
    return captured


@pytest.mark.asyncio
async def test_run_returns_intelligence_and_calls_flow_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_INTELLIGENCE", "ideakonnekt-wf-idea-intelligence")
    intel = {"ideaId": str(IDEA), "suggestedCategory": "process", "similarIdeas": [], "missingFields": [], "duplicateRisk": "low", "suggestedTags": []}
    captured = _patch_post(monkeypatch, {"success": True, "data": {"output": {"intelligence": intel}, "errors": [], "status": "completed", "session_id": "s"}})
    out, err = await flow.run({"id": IDEA, "title": "T", "problem": "P", "solution": "S", "tags": []})
    assert err is None
    assert out == intel
    assert captured["url"] == "https://gw.example/api/v1/flows/execute/ideakonnekt-wf-idea-intelligence"
    assert set(captured["json"]) == {"inputs"}
    assert captured["json"]["inputs"]["idea_id"] == str(IDEA)


@pytest.mark.asyncio
async def test_run_reports_failure_states(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_INTELLIGENCE", "ideakonnekt-wf-idea-intelligence")
    _patch_post(monkeypatch, {"data": {"output": {}, "errors": ["guardrail blocked"], "status": "completed"}})
    out, err = await flow.run({"title": "T"})
    assert out is None and err == "guardrail blocked"

    _patch_post(monkeypatch, {"data": {"output": {"other": 1}, "errors": [], "status": "completed"}})
    out, err = await flow.run({"title": "T"})
    assert out is None and "no intelligence" in (err or "")

    _patch_post(monkeypatch, {"data": {"output": {}, "errors": [], "status": "paused"}})
    out, err = await flow.run({"title": "T"})
    assert out is None and "paused" in (err or "")
