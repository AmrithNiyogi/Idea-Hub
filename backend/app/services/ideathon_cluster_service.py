"""Ideathon Cluster agent: group the ideathon's entries into theme clusters.

Responsibilities:
- Build the run input for the Kompass ``ideakonnekt-ideathon-cluster`` agent.
- Call it through the shared AI Studio execute client.

Collaborators:
- ``aistudio_execute_client`` for the HTTP call and agent id resolution.
- The agent reads the entries itself through the ``ik_ideathon_entries`` and ``ik_search_similar`` tools.

Side Effects:
- Outbound call to the Kompass execute endpoint. Nothing is written to the database.
- The result is a proposal. The organiser confirms the clusters.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.services import aistudio_execute_client as studio

HUB_AGENT_KEY = "ideathon-cluster"


def build_cluster_input(ideathon_id: uuid.UUID) -> dict[str, Any]:
    """Run input for the cluster agent: which ideathon to group."""
    return {"ideathon_id": str(ideathon_id), "stage": "cluster"}


async def propose_cluster(
    ideathon_id: uuid.UUID,
    *,
    conversation_id: str | None = None,
    tool_auth_token: str | None = None,
) -> studio.ExecuteResult:
    """Ask the Cluster agent to group the ideathon's entries.

    Returns an unsuccessful ``ExecuteResult`` (never raises for configuration gaps) when the
    Cluster agent id or the gateway settings are missing.
    """
    agent_id = studio.resolve_kompass_agent_id(HUB_AGENT_KEY)
    if not agent_id:
        return studio.ExecuteResult(
            success=False,
            error="AISTUDIO_AGENT_IDEATHON_CLUSTER is not set; the Cluster agent cannot run.",
        )
    return await studio.execute_run(
        agent_id=agent_id,
        input_payload=build_cluster_input(ideathon_id),
        conversation_id=conversation_id,
        tool_auth_token=tool_auth_token,
    )
