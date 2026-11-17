"""Unit tests for simulated Submit assist, help FAQ, and author optimizer (no DB)."""

from __future__ import annotations

import re

from app.services import agent_simulate_service as S


def test_submit_assist_opens_conversational_on_empty() -> None:
    out = S.submit_assist_turn(draft={}, message="", awaiting_field=None)
    assert out["simulated"] is True
    assert out["patches"] == {}
    assert out["awaiting_field"] is None
    assert "brainstorm" in out["reply"].lower()
    assert "Simulated" in out["notice"]


def test_submit_assist_brainstorm_applies_starter_patches() -> None:
    out = S.submit_assist_turn(
        draft={},
        message="brainstorm onboarding",
        awaiting_field=None,
    )
    assert out["patches"]["title"]
    assert out["patches"]["problem"]
    assert out["patches"]["tags"]
    assert out["patches"].get("category_slug") == "process"
    assert "starter" in out["reply"].lower() or "Updated" in out["reply"] or "applied" in out["reply"].lower()


def test_submit_assist_topic_from_scratch() -> None:
    out = S.submit_assist_turn(
        draft={},
        message="something about cloud cost and staging",
        awaiting_field=None,
    )
    assert "title" in out["patches"]
    assert out["patches"].get("category_slug") == "tech"


def test_submit_assist_shorten_title() -> None:
    draft = {
        "title": "A proposal for an automated self-serve onboarding checklist system",
        "problem": "x" * 30,
        "solution": "y" * 30,
    }
    out = S.submit_assist_turn(
        draft=draft,
        message="make the title shorter",
        awaiting_field=None,
    )
    assert "title" in out["patches"]
    assert len(out["patches"]["title"]) < len(draft["title"])


def test_submit_assist_add_metrics() -> None:
    draft = {
        "title": "Sleep staging at night",
        "problem": "Idle environments burn money every weekend and holiday.",
        "solution": "Schedule sleep and wake for non-prod stacks.",
        "success_metrics": "",
    }
    out = S.submit_assist_turn(
        draft=draft,
        message="add metrics",
        awaiting_field=None,
    )
    assert "success_metrics" in out["patches"]
    assert out["patches"]["success_metrics"]


def test_submit_assist_legacy_awaiting_field_still_works() -> None:
    out = S.submit_assist_turn(
        draft={},
        message="Automate expense receipts",
        awaiting_field="title",
    )
    assert out["patches"]["title"] == "Automate expense receipts"


def test_help_matches_submit_intent() -> None:
    out = S.help_turn(message="How do I submit an idea?")
    assert out["topic"] == "submit"
    assert any(l["href"] == "/submit" for l in out["links"])


def test_help_scrubs_secretish() -> None:
    out = S.help_turn(message="password=hunter2 how do I login with MFA?")
    assert "hunter2" not in out["reply"]
    assert out["topic"] == "sso_mfa"


def test_idea_optimize_opens_with_focus() -> None:
    out = S.idea_optimize_turn(
        idea={"title": "X", "problem": "short", "solution": "y", "tags": []},
        message="",
    )
    assert out["simulated"] is True
    assert out["field_patches"] == {}
    assert "Optimizer" in out["reply"] or "optimizer" in out["reply"].lower()


def test_idea_optimize_patches_metrics() -> None:
    out = S.idea_optimize_turn(
        idea={
            "title": "Automate expense receipts",
            "problem": "Finance chases missing receipts every month.",
            "solution": "Capture at submit time with OCR.",
            "success_metrics": "better",
            "tags": ["finance"],
        },
        message="add a measurable success metric",
    )
    assert "success_metrics" in out["field_patches"]
    assert re.search(r"\d", str(out["field_patches"]["success_metrics"]))


def test_idea_optimize_optimize_all() -> None:
    out = S.idea_optimize_turn(
        idea={
            "title": "Receipts",
            "problem": "Bad process.",
            "solution": "Fix it.",
            "tags": [],
        },
        message="optimize all",
    )
    assert out["field_patches"]
    assert any(
        k in out["field_patches"]
        for k in ("problem", "success_metrics", "tags", "solution")
    )
