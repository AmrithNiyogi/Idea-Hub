"""Idea Enhancement workflow: field handling, input shape, and output reading."""

from __future__ import annotations

from typing import Any

import pytest

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services import idea_enhancement_flow as flow


def test_unknown_field_falls_back_to_problem() -> None:
    assert flow.normalise_field("success_metrics") == "success_metrics"
    assert flow.normalise_field("status") == "problem"
    assert flow.normalise_field(None) == "problem"


def test_build_inputs_carries_all_fields_and_the_target() -> None:
    out = flow.build_inputs(
        {"title": "T", "problem": "P", "solution": "S", "beneficiaries": "B", "success_metrics": "", "tags": ["x"]},
        "success_metrics",
    )
    assert out["field"] == "success_metrics"
    assert out["beneficiaries"] == "B"
    assert out["tags"] == ["x"]
    assert out["idea_id"]


def test_flow_configured_needs_slug_and_live_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_ENHANCEMENT", "")
    assert flow.flow_configured() is False
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_ENHANCEMENT", "ideakonnekt-wf-idea-enhancement")
    monkeypatch.setattr(studio, "use_live_execute", lambda: True)
    assert flow.flow_configured() is True


@pytest.mark.asyncio
async def test_run_returns_enhancement_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_ENHANCEMENT", "ideakonnekt-wf-idea-enhancement")
    seen: dict[str, Any] = {}

    async def fake_execute_flow(**kwargs: Any) -> studio.ExecuteResult:
        seen.update(kwargs)
        return studio.ExecuteResult(success=True, result={"enhancement": {"field": "problem", "suggestions": []}})

    monkeypatch.setattr(studio, "execute_flow", fake_execute_flow)
    out, err = await flow.run({"title": "T", "problem": "P"}, "problem")
    assert err is None and out == {"field": "problem", "suggestions": []}
    assert seen["slug"] == "ideakonnekt-wf-idea-enhancement"
    assert seen["inputs"]["field"] == "problem"


@pytest.mark.asyncio
async def test_run_reports_missing_enhancement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AISTUDIO_WORKFLOW_IDEA_ENHANCEMENT", "ideakonnekt-wf-idea-enhancement")

    async def fake_execute_flow(**kwargs: Any) -> studio.ExecuteResult:
        return studio.ExecuteResult(success=True, result={"other": 1})

    monkeypatch.setattr(studio, "execute_flow", fake_execute_flow)
    out, err = await flow.run({"title": "T"}, "title")
    assert out is None and "no enhancement" in (err or "")
