"""Pydantic I/O for tracker / integration providers, connections, and idea links."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ConnectFieldOut(BaseModel):
    key: str
    label: str
    secret: bool = False
    required: bool = True
    placeholder: str = ""
    help_text: str = ""


class TrackerProviderOut(BaseModel):
    """Legacy tracker-only catalog shape (still used by Delivery panel)."""

    id: str
    display_name: str
    description: str = ""
    auth_mode: str = ""
    connect_fields: list[ConnectFieldOut] = Field(default_factory=list)


class IntegrationProviderOut(BaseModel):
    """Broader Integrations catalog (trackers + coming-soon stubs)."""

    id: str
    display_name: str
    description: str = ""
    category: str = "tracker"
    status: Literal["available", "coming_soon"] = "available"
    auth_mode: str = ""
    connect_fields: list[ConnectFieldOut] = Field(default_factory=list)
    coming_soon_note: str = ""
    connectable: bool = True


class TrackerConnectionCreate(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(default="default", max_length=120)
    credentials: dict[str, Any] = Field(default_factory=dict)


class TrackerConnectionOut(BaseModel):
    id: uuid.UUID
    provider_id: str
    label: str
    display_label: str
    scope: Literal["user", "organization"] = "user"
    external_account_id: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EffectiveConnectionOut(BaseModel):
    """Resolved connection for a provider from the actor's perspective."""

    provider_id: str
    source: Literal["user", "organization", "none"]
    connection: Optional[TrackerConnectionOut] = None


class IdeaTrackerLinkCreate(BaseModel):
    """Create a remote task or link an existing one.

    Prefer ``connection_id`` from effective connections. If omitted, pass
    ``provider_id`` and the service resolves user → org default.
    """

    connection_id: Optional[uuid.UUID] = None
    provider_id: Optional[str] = Field(default=None, max_length=64)
    mode: Literal["create", "link"] = "create"
    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    external_id_or_url: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Required when mode=link.",
    )
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_connection_or_provider(self) -> "IdeaTrackerLinkCreate":
        if not self.connection_id and not (self.provider_id or "").strip():
            raise ValueError("Provide connection_id or provider_id.")
        return self


class IdeaTrackerLinkOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    provider_id: str
    external_id: str
    external_key: str = ""
    external_url: str = ""
    title: str = ""
    created_by: uuid.UUID
    created_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class RemoteAssigneeOut(BaseModel):
    id: str = ""
    name: str = ""
    email: str = ""
    avatar_url: str = ""
    idea_hub_user_id: Optional[uuid.UUID] = None


class RemoteStatusOptionOut(BaseModel):
    id: str = ""
    name: str
    color: str = ""
    type: str = ""


class RemotePriorityOptionOut(BaseModel):
    id: str = ""
    name: str
    color: str = ""


class LiveTrackerTaskOut(BaseModel):
    """Stored link + live remote fields (or an error if refresh failed)."""

    link_id: uuid.UUID
    provider_id: str
    external_id: str
    external_key: str = ""
    external_url: str = ""
    stored_title: str = ""
    title: str = ""
    status: str = ""
    status_id: str = ""
    status_color: str = ""
    status_type: str = ""
    priority: str = ""
    priority_id: str = ""
    priority_color: str = ""
    due_date: str = ""
    url: str = ""
    assignees: list[RemoteAssigneeOut] = Field(default_factory=list)
    assignable: list[RemoteAssigneeOut] = Field(default_factory=list)
    status_options: list[RemoteStatusOptionOut] = Field(default_factory=list)
    priority_options: list[RemotePriorityOptionOut] = Field(default_factory=list)
    editable_fields: list[str] = Field(default_factory=list)
    live: bool = False
    error: Optional[str] = None
    can_update_status: bool = False
    can_update: bool = False


class IdeaTrackerRemoteUpdate(BaseModel):
    """Write-back to the remote tracker for a linked task."""

    status: Optional[str] = Field(
        default=None,
        max_length=200,
        description=(
            "Remote status to set. ClickUp: status *name* from the list "
            "(e.g. 'in progress'). Jira: target status name (via transition)."
        ),
    )
    title: Optional[str] = Field(default=None, max_length=500)
    priority: Optional[str] = Field(
        default=None,
        max_length=80,
        description=(
            "Priority name/id. ClickUp: urgent|high|normal|low (empty clears). "
            "Jira: priority name from catalog."
        ),
    )
    due_date: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Due date YYYY-MM-DD; empty string clears when supported.",
    )
    assignee_ids: Optional[list[str]] = Field(
        default=None,
        description=(
            "Desired full set of remote user ids. ClickUp: multi-assignee "
            "add/rem diff. Jira: first id becomes the single assignee; "
            "empty list unassigns."
        ),
    )

    @model_validator(mode="after")
    def _require_field(self) -> "IdeaTrackerRemoteUpdate":
        if (
            self.status is None
            and self.title is None
            and self.priority is None
            and self.due_date is None
            and self.assignee_ids is None
        ):
            raise ValueError(
                "Provide status, title, priority, due_date, and/or assignee_ids."
            )
        return self
