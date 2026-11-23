"""Agent gateway schemas (Phase 5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentInfoOut(BaseModel):
    id: str
    prompt_slug: Optional[str] = None
    form: str
    purpose: str
    triggers: list[str]
    approval_default: str
    never: list[str]
    simulated: bool = True


class AgentRunRequest(BaseModel):
    agent_id: str = Field(..., description="Roster agent id, e.g. idea-intelligence")
    event: str = Field(..., description="Trigger event name")
    idea_id: Optional[uuid.UUID] = None
    context: dict[str, Any] = Field(default_factory=dict)
    record: bool = True


class AgentRunOut(BaseModel):
    id: uuid.UUID
    agent_id: str
    event: str
    idea_id: Optional[uuid.UUID] = None
    summary: str
    output: dict[str, Any]
    simulated: bool = True
    engine: str
    approval_required: bool
    approval_role: Optional[str] = None
    approval_state: str
    proposal_key: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProposalDecideIn(BaseModel):
    proposal_key: str
    approve: bool
    reason: str = ""
    snooze_days: int = Field(0, ge=0, le=30)


class ProposalDecisionOut(BaseModel):
    id: uuid.UUID
    proposal_key: str
    state: str
    decided_by: uuid.UUID
    reason: str
    snooze_until: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PendingProposalOut(BaseModel):
    proposal_key: str
    run: AgentRunOut
    evidence: list[str] = Field(default_factory=list)


class KompassMapOut(BaseModel):
    connected: bool = False
    notice: str = "Not connected to Kompass"
    questions: list[dict[str, Any]]


class KompassAnswerIn(BaseModel):
    answered: bool = True
    note: str = ""


class SubmitAssistTurnIn(BaseModel):
    """One conversational turn for the Submit side assistant."""

    draft: dict[str, Any] = Field(
        default_factory=dict,
        description="Current form values (title, problem, solution, tags, …).",
        examples=[{"title": "", "problem": ""}],
    )
    message: str = Field(
        default="",
        max_length=4000,
        description="Latest user message. Empty string starts / continues the guide.",
    )
    awaiting_field: Optional[str] = Field(
        default=None,
        description="Field the assistant last asked for (title, problem, …).",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description=(
            "AI Studio conversation thread id. Omit on first turn; echo the "
            "id returned by the previous response for multi-turn chat."
        ),
    )


class HelpLinkOut(BaseModel):
    label: str
    href: str = Field(..., description="In-app path, e.g. /submit")


class SubmitAssistTurnOut(BaseModel):
    simulated: bool = True
    engine: str
    mode: str = Field(description="simulate | live | kompass-pending")
    reply: str
    patches: dict[str, Any] = Field(default_factory=dict)
    awaiting_field: Optional[str] = None
    field_prompt: Optional[str] = None
    done: bool = False
    notice: str = "Simulated — Kompass soon"
    conversation_id: Optional[str] = Field(
        default=None,
        description="AI Studio conversation id to send on the next turn.",
    )


class HelpTurnIn(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User question about IdeaKonnekt (no secrets).",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="AI Studio conversation thread id for Help FAB multi-turn.",
    )


class HelpTurnOut(BaseModel):
    simulated: bool = True
    engine: str
    mode: str
    topic: str
    reply: str
    links: list[HelpLinkOut] = Field(default_factory=list)
    followups: list[str] = Field(
        default_factory=list,
        description="Up to three follow-up questions the user can send next.",
    )
    notice: str = "Simulated — Kompass soon"
    conversation_id: Optional[str] = Field(
        default=None,
        description="AI Studio conversation id to send on the next turn.",
    )


class IdeaOptimizeTurnIn(BaseModel):
    """One conversational turn for the author Idea Optimizer."""

    idea_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional idea UUID for client correlation (not loaded here).",
    )
    idea: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Current idea fields: title, problem, solution, beneficiaries, "
            "success_metrics, tags, effort, category_id/slug."
        ),
        examples=[
            {
                "title": "Automate expense receipts",
                "problem": "Finance chases missing receipts.",
                "solution": "Capture at submit time.",
                "tags": ["finance"],
            }
        ],
    )
    message: str = Field(
        default="",
        max_length=4000,
        description="Latest author message. Empty string opens the optimizer.",
    )
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Optional prior chat turns for Kompass / client context.",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="AI Studio conversation thread id for this optimizer session.",
    )


class IdeaOptimizeTurnOut(BaseModel):
    """Author optimizer reply with optional field patches (human applies)."""

    simulated: bool = True
    engine: str
    mode: str = Field(description="simulate | live | kompass-pending")
    reply: str
    field_patches: dict[str, Any] = Field(
        default_factory=dict,
        description="Proposed field updates; never persisted by this endpoint.",
    )
    focus_fields: list[str] = Field(
        default_factory=list,
        description="Heuristic weak-field names (problem, success_metrics, …).",
    )
    notice: str = "Simulated — Kompass soon"
    conversation_id: Optional[str] = Field(
        default=None,
        description="AI Studio conversation id to send on the next turn.",
    )
