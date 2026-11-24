"""Idea AI review: DotKonnekt fit, suggestions, live merge, and company context source."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.constants.strategic_themes import STRATEGIC_THEMES
from app.services import idea_ai_review_service as review

THEMES = [dict(t) for t in STRATEGIC_THEMES]


def _fields(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Flaky test dashboard",
        "problem": "Flaky tests cause regression noise and hide real incidents from the on-call engineers each week.",
        "solution": "A dashboard that tracks flaky tests, alerts owners and shows a trend for each service over time.",
        "beneficiaries": "Engineers on call and release managers",
        "success_metrics": "Flaky test rate below 2% per week",
        "tags": ["testing"],
    }
    base.update(overrides)
    return base


def test_idea_touching_several_themes_is_strong_fit() -> None:
    out = review.build_local_review(_fields(), THEMES)
    fit = out["dotkonnekt_fit"]
    assert fit["band"] == "strong"
    assert {t["id"] for t in fit["themes"]} >= {"reliability", "observability"}
    assert out["simulated"] is True
    assert out["missing_fields"] == []


def test_unrelated_idea_is_exploratory_with_angles_not_a_penalty() -> None:
    out = review.build_local_review(
        _fields(title="Plant swap", problem="Desk plants", solution="Swap plants", beneficiaries="",
                success_metrics="", tags=[]),
        THEMES,
    )
    assert out["dotkonnekt_fit"]["band"] == "exploratory"
    assert len(out["dotkonnekt_fit"]["angles"]) == 3
    assert "not marked down" in out["summary"]


def test_thin_fields_get_clarifying_questions() -> None:
    out = review.build_local_review(_fields(problem="Slow", beneficiaries="", success_metrics=""), THEMES)
    assert set(out["missing_fields"]) >= {"problem", "beneficiaries", "success_metrics"}
    questions = [s for s in out["suggestions"] if s["kind"] == "clarifying_question"]
    assert {s["field"] for s in questions} >= {"problem", "beneficiaries", "success_metrics"}


def test_local_review_does_not_invent_beneficiaries() -> None:
    assert review.build_local_review(_fields(), THEMES)["suggested_beneficiaries"] == []


def test_live_enhancement_replaces_suggestions_but_keeps_fit() -> None:
    local = review.build_local_review(_fields(), THEMES)
    merged = review.merge_live(
        local,
        {
            "field": "all",
            "suggestions": [{"kind": "rewrite", "text": "Say who is paged.", "rationale": "Clarity"}],
            "suggestedMetrics": [{"metric": "Flaky rate", "unit": "%", "baselinePrompt": "Today?"}],
            "suggestedBeneficiaries": ["On-call engineers"],
        },
    )
    assert merged["simulated"] is False
    assert merged["suggestions"][0]["text"] == "Say who is paged."
    assert merged["suggested_metrics"][0]["baseline_prompt"] == "Today?"
    assert merged["dotkonnekt_fit"] == local["dotkonnekt_fit"]


async def test_admin_company_context_overrides_default() -> None:
    custom = {"themes": [{"id": "kompass", "label": "Kompass adoption", "words": ["kompass"]}]}
    session = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(value=custom)))
    themes = await review.company_themes(session)  # type: ignore[arg-type]
    assert themes == custom["themes"]


async def test_default_company_context_is_strategic_themes() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    assert await review.company_themes(session) == THEMES  # type: ignore[arg-type]


async def test_build_review_falls_back_when_live_flow_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review.idea_enhancement_flow, "flow_configured", lambda: True)
    monkeypatch.setattr(review.idea_enhancement_flow, "run", AsyncMock(return_value=(None, "timeout")))
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    idea = SimpleNamespace(id=uuid.uuid4(), **_fields())
    out = await review.build_review(session, idea)  # type: ignore[arg-type]
    assert out["simulated"] is True
    assert "Live workflow unavailable: timeout" in out["summary"]


def test_theme_words_match_whole_words_only() -> None:
    themes = [{"id": "obs", "label": "Observability", "words": ["log", "sla"]}]
    hits = review.match_themes({"title": "Translate the blog", "problem": "", "tags": []}, themes)
    assert hits == []
    hits = review.match_themes({"title": "Ship logs faster", "problem": "", "tags": []}, themes)
    assert hits[0]["matched_terms"] == ["log"]


def test_no_generic_metric_suggestion_when_metric_exists() -> None:
    out = review.build_local_review(_fields(), THEMES)
    assert not [s for s in out["suggestions"] if s["field"] == "success_metrics"]
    assert out["suggested_metrics"] == []


def test_metric_scaffold_offered_when_metric_missing() -> None:
    out = review.build_local_review(_fields(success_metrics=""), THEMES)
    assert out["suggested_metrics"]
