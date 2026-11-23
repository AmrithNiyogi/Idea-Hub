"""Entry briefs for agents: idea content and signals, never the author."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

from app.models.idea import Idea
from app.services import agent_entry_service as svc

AUTHOR = uuid.UUID("99999999-8888-7777-6666-555555555555")


def _idea(**overrides: Any) -> Idea:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(), title="Runbook from chat", problem="Write-ups take hours.",
        solution="Draft from the timeline.", beneficiaries="On-call engineers",
        success_metrics="Coverage 50% to 90%", tags=["sre"], effort="M", status="under_review",
        category_id=None, anonymous=True, author_id=AUTHOR, created_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return cast(Idea, SimpleNamespace(**base))


def test_build_entry_carries_content_and_signals_without_author() -> None:
    idea = _idea()
    out = svc.build_entry_out(idea, "sre", panel_avg=7.5, panel_n=2, audience_votes=4)
    assert out.title == "Runbook from chat"
    assert out.problem == "Write-ups take hours."
    assert out.category_slug == "sre"
    assert out.is_anonymous is True
    assert out.panel_avg == 7.5
    assert out.panel_n == 2
    assert out.audience_votes == 4
    assert "author" not in out.model_dump()
    assert str(AUTHOR) not in out.model_dump_json()


def test_build_entry_without_scores_reports_none_and_zero() -> None:
    out = svc.build_entry_out(_idea(), None, panel_avg=None, panel_n=0, audience_votes=0)
    assert out.panel_avg is None
    assert out.panel_n == 0
    assert out.audience_votes == 0
