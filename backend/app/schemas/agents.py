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
