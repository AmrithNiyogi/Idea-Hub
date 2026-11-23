"""Ideathon Rank agent: propose an ordered shortlist for an ideathon.

Responsibilities:
- Build the run input for the Kompass ``ideakonnekt-ideathon-rank`` agent.
- Call it through the shared AI Studio execute client.

Collaborators:
- ``aistudio_execute_client`` for the HTTP call and agent id resolution.
- The agent fetches its own entries via the ``ik_ideathon_entries`` tool.

Side Effects:
- Outbound call to the Kompass execute endpoint. Nothing is written to the database.
- The result is a proposal only. The organiser confirms any shortlist.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from app.services import aistudio_execute_client as studio

HUB_AGENT_KEY = "ideathon-rank"
STAGE = "rank"


def build_rank_input(ideathon_id: uuid.UUID, weights: Mapping[str, float]) -> dict[str, Any]:
    """Run input for the rank agent: which ideathon, which stage, and the scoring weights."""
    return {
        "ideathon_id": str(ideathon_id),
        "stage": STAGE,
        "weights": {str(k): float(v) for k, v in weights.items()},
    }


async def propose_rank(
    ideathon_id: uuid.UUID,
    weights: Mapping[str, float],
    *,
    conversation_id: str | None = None,
    tool_auth_token: str | None = None,
) -> studio.ExecuteResult:
    """Ask the Rank agent for a proposed shortlist.

    Returns an unsuccessful ``ExecuteResult`` (never raises for configuration gaps) when the
    Rank agent id or the gateway settings are missing.
    """
    agent_id = studio.resolve_kompass_agent_id(HUB_AGENT_KEY)
    if not agent_id:
        return studio.ExecuteResult(
            success=False,
            error="AISTUDIO_AGENT_IDEATHON_RANK is not set; the Rank agent cannot run.",
        )
    return await studio.execute_run(
        agent_id=agent_id,
        input_payload=build_rank_input(ideathon_id, weights),
        conversation_id=conversation_id,
        tool_auth_token=tool_auth_token,
    )
