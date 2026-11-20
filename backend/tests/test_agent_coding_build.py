"""Unit tests for coding-agent-build heuristic (no DB / network)."""

from __future__ import annotations

from app.services import agent_heuristics as H


def test_coding_build_plan_timeline_and_gate() -> None:
    out = H.coding_build_plan(
        idea_id="00000000-0000-0000-0000-000000000001",
        title="Receipt capture",
        status="accepted",
        problem="Finance chases missing receipts every month end close.",
        solution="Capture receipts at expense submit with OCR assist.",
        tags=["finance", "ops"],
        effort="M",
        markdown_chars=420,
    )
    assert out["simulated"] is True
    assert out["prototype_gate"]["required"] is True
    assert out["prototype_gate"]["approved"] is False
    assert out["prototype_gate"]["auto_flip"] is False
    ids = [s["id"] for s in out["timeline"]]
    assert ids == ["context", "skill_pack", "execute", "prototype_gate"]
    assert out["timeline"][-1]["status"] == "pending"
    assert "Receipt capture" in out["plan"]["summary"]
    assert any("finance" in i for i in out["plan"]["items"])


def test_coding_build_plan_flags_thin_fields() -> None:
    out = H.coding_build_plan(
        idea_id="x",
        title="Thin",
        status="accepted",
        problem="short",
        solution="also short",
        tags=[],
        effort="XL",
        markdown_chars=10,
    )
    items = " ".join(out["plan"]["items"]).lower()
    assert "milestones" in items or "shippable" in items
    assert "problem" in items or "solution" in items
