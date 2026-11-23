"""Schemas for KonnektIdea → agent handoff (Cursor / Claude Code).

These payloads are intended for pasting into coding agents. They must never
include secrets, credentials, emails, or OTP material — only product context
needed to start implementation.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentPersonRef(BaseModel):
    """Public person reference safe for agent prompts."""

    id: UUID = Field(..., description="User UUID.", examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    name: str = Field(..., description="Display name (never email).", examples=["Priya Shah"])


class AgentCategoryRef(BaseModel):
    """Category label for the idea."""

    id: UUID = Field(..., description="Category UUID.")
    slug: str = Field(..., description="Stable category slug.", examples=["process"])
    label: str = Field(..., description="Human-readable category label.", examples=["Process"])


class AgentStatusEvent(BaseModel):
    """One status-history transition."""

    from_status: str | None = Field(None, description="Prior status, if any.")
    to_status: str = Field(..., description="New status.")
    at: datetime = Field(..., description="When the transition was recorded (UTC).")
    reason: str = Field("", description="Optional reason text; empty when none.")


class AgentDecisionSummary(BaseModel):
    """Latest recorded review decision, if any."""

    outcome: str = Field(..., description="Decision outcome code.", examples=["accept"])
    reason: str = Field(..., description="Mandatory written reason shown to authors.")
    at: datetime = Field(..., description="Decision timestamp (UTC).")
    as_role: str = Field(..., description="Role the decider acted as.", examples=["reviewer"])
    hours: int | None = Field(None, description="Recommended innovation hours, if set.")
    question: str = Field("", description="Needs-info question when outcome is info.")
    change_mind: str = Field("", description="What would change a decline decision.")


class AgentCommentHighlight(BaseModel):
    """Truncated comment used in the handoff pack."""

    kind: str = Field(..., description="Comment kind (discussion / system).", examples=["discussion"])
    body: str = Field(..., description="Comment body, truncated for prompt size.")
    at: datetime = Field(..., description="Comment created_at (UTC).")
    author_name: str | None = Field(
        None,
        description="Author display name when safe to expose; null when redacted.",
    )


class AgentCommentsSummary(BaseModel):
    """Discussion roll-up for agents."""

    count: int = Field(..., description="Total comments on the idea.", ge=0)
    highlights: list[AgentCommentHighlight] = Field(
        default_factory=list,
        description="Up to N most recent comments (truncated bodies).",
    )


class AgentDeliverySummary(BaseModel):
    """Compact delivery project snapshot when innovation hours exist."""

    hours_granted: int = Field(..., description="Granted innovation hours.")
    started_at: datetime | None = Field(None, description="Delivery start time.")
    implemented_at: datetime | None = Field(None, description="When marked implemented.")
    outcome: str = Field("", description="Delivery outcome notes.")
    task_total: int = Field(0, description="Total delivery tasks.", ge=0)
    task_done: int = Field(0, description="Completed delivery tasks.", ge=0)
    open_task_titles: list[str] = Field(
        default_factory=list,
        description="Titles of incomplete tasks (capped).",
    )


class AgentRelatedLink(BaseModel):
    """In-app or external link useful for the coding agent."""

    label: str = Field(..., description="Link label.", examples=["Idea detail"])
    href: str = Field(
        ...,
        description="Absolute or app-relative path.",
        examples=["/ideas/a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )


class AgentPrompts(BaseModel):
    """Tool-tailored prompt wrappers around the same markdown pack."""

    cursor: str = Field(
        ...,
        description="Paste into Cursor Agent chat; includes repo-path guidance.",
    )
    claude: str = Field(
        ...,
        description="Paste into Claude Code; includes CLAUDE.md awareness.",
    )


class AgentSkillPack(BaseModel):
    """Metadata + skill body so the UI can copy/install without a second fetch."""

    name: str = Field(
        ...,
        description="Skill folder / registry name.",
        examples=["idea-hub-pull-idea"],
    )
    skill_markdown: str = Field(
        ...,
        description="Full SKILL.md contents (safe to download or paste).",
    )
    install_cursor: str = Field(
        ...,
        description="Human install steps for Cursor project skills path.",
    )
    install_claude: str = Field(
        ...,
        description="Human install steps for Claude Code skills path.",
    )
    zip_url: str = Field(
        ...,
        description="Authenticated relative API path for the installable zip.",
        examples=["/api/v1/agent-handoff/skill-pack.zip"],
    )


class AgentContextOut(BaseModel):
    """Full agent handoff payload: structured fields plus rendered markdown.

    Auth is required. Anonymous authorship is redacted (author null; no PII).
    Secrets, emails, and credentials are never included.
    """

    idea_id: UUID = Field(..., description="Idea UUID.")
    slug: str | None = Field(None, description="URL slug when present.")
    title: str = Field(..., description="Idea title.")
    status: str = Field(..., description="Current lifecycle status.")
    category: AgentCategoryRef | None = Field(None, description="Category when set.")
    problem: str = Field("", description="Problem statement.")
    solution: str = Field("", description="Proposed solution.")
    beneficiaries: str = Field("", description="Who benefits.")
    success_metrics: str = Field("", description="Success metrics.")
    effort: str = Field("M", description="Effort band S|M|L|XL.")
    tags: list[str] = Field(default_factory=list, description="Idea tags.")
    anonymous: bool = Field(False, description="True when author identity is hidden.")
    author: AgentPersonRef | None = Field(
        None,
        description="Author when not anonymous; otherwise null.",
    )
    owner: AgentPersonRef | None = Field(None, description="Delivery owner when assigned.")
    status_history: list[AgentStatusEvent] = Field(
        default_factory=list,
        description="Chronological status transitions (oldest first).",
    )
    latest_decision: AgentDecisionSummary | None = Field(
        None,
        description="Most recent review decision, if any.",
    )
    comments: AgentCommentsSummary = Field(
        ...,
        description="Comment count and recent highlights.",
    )
    delivery: AgentDeliverySummary | None = Field(
        None,
        description="Delivery summary when a project exists.",
    )
    related_links: list[AgentRelatedLink] = Field(
        default_factory=list,
        description="App paths useful for follow-up.",
    )
    api_base_url: str = Field(
        ...,
        description="Public API origin for agent curl / skill env (no trailing slash).",
        examples=["http://127.0.0.1:8000"],
    )
    skill: AgentSkillPack = Field(
        ...,
        description="Shipped idea-hub-pull-idea skill for download/copy/install.",
    )
    markdown: str = Field(
        ...,
        description="Rendered context.md body (no secrets).",
    )
    prompts: AgentPrompts = Field(
        ...,
        description="Ready-to-paste prompts for Cursor and Claude Code.",
    )
