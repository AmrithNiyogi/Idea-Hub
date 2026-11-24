"""Idea Enhancement as a Kompass workflow: propose improvements to one field of an idea.

Responsibilities:
- Decide whether the live workflow is configured.
- Build the flow's inputs (idea fields plus the one field to improve).
- Run the flow and return its enhancement object, or the reason it failed.

Collaborators:
- ``aistudio_execute_client.execute_flow`` for the HTTP call.
- ``agent_gateway`` calls ``run`` and falls back to the simulated proposal on failure.

Side Effects:
- Outbound call to the Kompass flow execute endpoint. Nothing is written to the database.
- Suggestions are proposals. The author decides what to apply.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services.idea_intelligence_flow import _field

ENGINE_LABEL = "kompass-flow:idea-enhancement"
ENHANCEABLE_FIELDS = ("title", "problem", "solution", "beneficiaries", "success_metrics", "all")


def flow_configured() -> bool:
    """True when the workflow slug is set and live execution is on."""
    return bool((settings.AISTUDIO_WORKFLOW_IDEA_ENHANCEMENT or "").strip()) and studio.use_live_execute()


def normalise_field(field: Any) -> str:
    """The requested field if the flow supports it, otherwise problem."""
    text = str(field or "").strip()
    return text if text in ENHANCEABLE_FIELDS else "problem"


def build_inputs(draft: Any, field: str) -> dict[str, Any]:
    """The flow's init fields: the idea as it stands, and the one field to improve."""
    raw_id = _field(draft, "id") or _field(draft, "idea_id")
    tags = _field(draft, "tags") or []
    return {
        "idea_id": str(raw_id) if raw_id else str(uuid.uuid4()),
        "field": normalise_field(field),
        "title": str(_field(draft, "title") or ""),
        "problem": str(_field(draft, "problem") or ""),
        "solution": str(_field(draft, "solution") or ""),
        "beneficiaries": str(_field(draft, "beneficiaries") or ""),
        "success_metrics": str(_field(draft, "success_metrics") or ""),
        "tags": [str(t) for t in tags],
    }


async def run(draft: Any, field: str) -> tuple[dict[str, Any] | None, str | None]:
    """Run the workflow. Returns (enhancement, None) on success, or (None, reason) on failure."""
    result = await studio.execute_flow(
        slug=settings.AISTUDIO_WORKFLOW_IDEA_ENHANCEMENT,
        inputs=build_inputs(draft, field),
    )
    if not result.success:
        return None, result.error or "the workflow run failed"
    enhancement = result.result.get("enhancement") if isinstance(result.result, dict) else None
    if not isinstance(enhancement, dict):
        return None, "the workflow output has no enhancement object"
    return enhancement, None
