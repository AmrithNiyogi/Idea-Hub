"""Idea Intelligence as a Kompass workflow: map the idea onto the flow's inputs and read its result.

Responsibilities:
- Decide whether the live workflow is configured.
- Build the flow's init inputs (idea_id, title, problem, solution, tags) from a draft or saved idea.
- Run the flow and return the ``intelligence`` object from its output, or the reason it failed.

Collaborators:
- ``aistudio_execute_client.execute_flow`` for the HTTP call.
- ``agent_gateway`` calls ``run`` and falls back to the simulated result on failure.

Side Effects:
- Outbound call to the Kompass flow execute endpoint. Nothing is written to the database.
- An unsaved draft has no id, so a fresh UUID is sent. The result is not stored under it.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import settings
from app.services import aistudio_execute_client as studio

ENGINE_LABEL = "kompass-flow:idea-intelligence"


def flow_configured() -> bool:
    """True when the workflow slug is set and live execution is on."""
    return bool((settings.AISTUDIO_WORKFLOW_IDEA_INTELLIGENCE or "").strip()) and studio.use_live_execute()


def _field(draft: Any, name: str) -> Any:
    if isinstance(draft, dict):
        return draft.get(name)
    return getattr(draft, name, None)


def build_inputs(draft: Any) -> dict[str, Any]:
    """The flow's init fields. Accepts an Idea row or a plain dict from the Submit page."""
    raw_id = _field(draft, "id") or _field(draft, "idea_id")
    idea_id = str(raw_id) if raw_id else str(uuid.uuid4())
    tags = _field(draft, "tags") or []
    return {
        "idea_id": idea_id,
        "title": str(_field(draft, "title") or ""),
        "problem": str(_field(draft, "problem") or ""),
        "solution": str(_field(draft, "solution") or ""),
        "tags": [str(t) for t in tags],
    }


async def run(draft: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Run the workflow. Returns (intelligence, None) on success, or (None, reason) on failure."""
    result = await studio.execute_flow(
        slug=settings.AISTUDIO_WORKFLOW_IDEA_INTELLIGENCE,
        inputs=build_inputs(draft),
    )
    if not result.success:
        return None, result.error or "the workflow run failed"
    intelligence = result.result.get("intelligence") if isinstance(result.result, dict) else None
    if not isinstance(intelligence, dict):
        return None, "the workflow output has no intelligence object"
    return intelligence, None
