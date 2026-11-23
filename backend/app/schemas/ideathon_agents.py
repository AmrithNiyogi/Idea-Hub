"""Request and response schemas for the Ideathon Rank and Pitch agent endpoints."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RankRunIn(BaseModel):
    """Scoring weights for the Rank agent, keyed by criterion name."""

    weights: dict[str, float] = Field(default_factory=dict)


class PitchRunIn(BaseModel):
    """Stage to draft and any Cluster / Rank outputs to carry into the pitch."""

    stage: Literal["pitch", "handoff", "both"] = "both"
    clusters: Optional[list[dict[str, Any]]] = None
    shortlist_suggestion: Optional[list[dict[str, Any]]] = None


class AgentRunOut(BaseModel):
    """Normalised outcome of one agent run. ``result_text`` holds the agent's reply as text."""

    success: bool
    result_text: str = ""
    conversation_id: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


class DraftRunIn(BaseModel):
    """Theme the organiser typed on the create form; the Draft agent words challenges for it."""

    theme: str = Field(min_length=1, max_length=200)


class DraftRunOut(BaseModel):
    """Name options and challenge statements proposed by the Draft agent. The organiser picks or types the name."""

    success: bool
    names: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
