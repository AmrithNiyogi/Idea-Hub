"""Ideathon Pitch agent: draft pitch summaries and handoff statements for shortlisted ideas.

Responsibilities:
- Build the run input for the Kompass ``ideakonnekt-ideathon-pitch`` agent.
- Pass through the Cluster and Rank outputs when the organiser supplies them.
- Call the agent through the shared AI Studio execute client.

Collaborators:
- ``aistudio_execute_client`` for the HTTP call and agent id resolution.
- The agent fetches idea details via ``ik_get_idea`` and entries via ``ik_ideathon_entries``.

Side Effects:
- Outbound call to the Kompass execute endpoint. Nothing is written to the database.
- The result is a draft. Organisers and authors approve before anything is published.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Mapping, Sequence

from app.services import aistudio_execute_client as studio

HUB_AGENT_KEY = "ideathon-pitch"
PitchStage = Literal["pitch", "handoff", "both"]


def build_pitch_input(
    ideathon_id: uuid.UUID,
    *,
    stage: PitchStage = "both",
    clusters: Sequence[Mapping[str, Any]] | None = None,
    shortlist_suggestion: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run input for the pitch agent: which ideathon, which stage, and any earlier outputs to carry."""
    payload: dict[str, Any] = {"ideathon_id": str(ideathon_id), "stage": stage}
    if clusters is not None:
        payload["clusters"] = [dict(c) for c in clusters]
    if shortlist_suggestion is not None:
        payload["shortlistSuggestion"] = [dict(s) for s in shortlist_suggestion]
    return payload


async def propose_pitch(
    ideathon_id: uuid.UUID,
    *,
    stage: PitchStage = "both",
    clusters: Sequence[Mapping[str, Any]] | None = None,
    shortlist_suggestion: Sequence[Mapping[str, Any]] | None = None,
    conversation_id: str | None = None,
    tool_auth_token: str | None = None,
) -> studio.ExecuteResult:
    """Ask the Pitch agent for pitch summaries and handoff statements.

    Returns an unsuccessful ``ExecuteResult`` (never raises for configuration gaps) when the
    Pitch agent id or the gateway settings are missing.
    """
    agent_id = studio.resolve_kompass_agent_id(HUB_AGENT_KEY)
    if not agent_id:
        return studio.ExecuteResult(
            success=False,
            error="AISTUDIO_AGENT_IDEATHON_PITCH is not set; the Pitch agent cannot run.",
        )
    return await studio.execute_run(
        agent_id=agent_id,
        input_payload=build_pitch_input(
            ideathon_id,
            stage=stage,
            clusters=clusters,
            shortlist_suggestion=shortlist_suggestion,
        ),
        conversation_id=conversation_id,
        tool_auth_token=tool_auth_token,
    )
