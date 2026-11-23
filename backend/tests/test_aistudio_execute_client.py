"""Unit tests for AI Studio runs/execute client (no network)."""

from __future__ import annotations

import json

import pytest

from app.services import aistudio_execute_client as C


def test_normalize_nested_result() -> None:
    payload = {
        "data": {
            "data": {
                "success": True,
                "result": "Hello from agent",
                "conversation_id": "conv-1",
                "metadata": {"x": 1},
            }
        }
    }
    out = C.normalize_execution_payload(payload)
    assert out.success is True
    assert out.result_text == "Hello from agent"
    assert out.conversation_id == "conv-1"
    assert out.metadata == {"x": 1}


def test_parse_structured_result_fenced_json() -> None:
    raw = '```json\n{"reply": "hi", "patches": {"title": "T"}}\n```'
    parsed = C.parse_structured_result(raw)
    assert parsed["reply"] == "hi"
    assert parsed["patches"]["title"] == "T"


def test_hub_agent_env_keys_cover_surfaces() -> None:
    assert set(C.HUB_AGENT_ENV_KEYS) == {
        "submit-assist",
        "help",
        "idea-optimizer",
        "review-intelligence",
        "coding-agent-build",
        "ideathon-rank",
        "ideathon-pitch",
        "ideathon-cluster",
        "ideathon-draft",
    }


@pytest.mark.asyncio
async def test_execute_run_requires_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(C.settings, "AISTUDIO_API_BASE_URL", "")
    monkeypatch.setattr(C.settings, "AISTUDIO_TENANT_ID", "")
    monkeypatch.setattr(C.settings, "AISTUDIO_PROJECT_SLUG", "")
    out = await C.execute_run(agent_id="x", input_payload="hi")
    assert out.success is False
    assert "not configured" in (out.error or "").lower()


@pytest.mark.asyncio
async def test_execute_run_posts_expected_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        C.settings,
        "AISTUDIO_API_BASE_URL",
        "https://aistudio-apigateway-v2-staging.dotkonnekt.com",
    )
    monkeypatch.setattr(C.settings, "AISTUDIO_TENANT_ID", "devtest")
    monkeypatch.setattr(C.settings, "AISTUDIO_PROJECT_SLUG", "idea-hub")
    monkeypatch.setattr(C.settings, "AISTUDIO_TOOL_AUTH_TOKEN", "tool-tok")
    monkeypatch.setattr(C.settings, "AISTUDIO_EXECUTE_TIMEOUT_SECONDS", 5)

    captured: dict = {}

    class FakeResponse:
        status_code = 200
        content = b'{"data":{"result":"ok","conversation_id":"c-9"}}'

        def json(self) -> dict:
            return json.loads(self.content)

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url, headers=None, json=None):  # noqa: A002
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(C.httpx, "AsyncClient", FakeClient)

    out = await C.execute_run(
        agent_id="help-agent",
        input_payload="How do I submit?",
        conversation_id="c-prev",
    )
    assert out.success is True
    assert out.conversation_id == "c-9"
    assert captured["url"].endswith("/api/v1/agents/help-agent/execute")
    assert captured["headers"]["X-Tenant-ID"] == "devtest"
    assert captured["headers"]["project-slug"] == "idea-hub"
    assert captured["headers"]["X-Authorization"] == "Bearer tool-tok"
    assert captured["json"] == {
        "task": "How do I submit?",
        "session_id": "c-prev",
    }
