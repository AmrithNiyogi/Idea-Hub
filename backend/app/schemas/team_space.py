"""Pydantic I/O for team collaboration spaces."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TeamChannelOut(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    slug: str
    name: str
    description: str = ""
    kind: str = "text"
    sort_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMessageOut(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    message_type: str = "user"
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMeetingOut(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    channel_id: Optional[uuid.UUID] = None
    title: str
    description: str = ""
    starts_at: datetime
    ends_at: Optional[datetime] = None
    join_url: str = ""
    created_by: uuid.UUID
    notify_via: str = "none"
    notify_status: str = "pending"
    notify_detail: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class IdeaMcpConnectionOut(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    idea_id: uuid.UUID
    label: str
    endpoint_url: str
    auth_header_name: str = "Authorization"
    has_auth: bool = False
    transport: str = "http_jsonrpc"
    tools_cache: list[dict[str, Any]] = Field(default_factory=list)
    last_discovered_at: Optional[datetime] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamSpaceOut(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    title: str
    created_by: uuid.UUID
    created_at: datetime
    channels: list[TeamChannelOut] = Field(default_factory=list)
    can_post: bool = False
    can_manage: bool = False

    model_config = {"from_attributes": True}


class TeamMessageCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=8000)

    @field_validator("body")
    @classmethod
    def _strip(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("Message body is required.")
        return text


class TeamChannelCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=64)
    description: str = Field(default="", max_length=500)
    kind: Literal["text", "announcements"] = "text"


class TeamMeetingCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    starts_at: datetime
    ends_at: Optional[datetime] = None
    description: str = Field(default="", max_length=4000)
    join_url: str = Field(default="", max_length=1024)
    channel_id: Optional[uuid.UUID] = None
    channel_slug: Optional[str] = Field(default=None, max_length=64)
    # Post MessageCard to Teams Incoming Webhook (effective connection).
    notify_teams: bool = True
    # Also post a meeting message into the idea channel.
    announce_in_channel: bool = True


class IdeaMcpConnectionCreateIn(BaseModel):
    label: str = Field(default="default", max_length=120)
    endpoint_url: str = Field(min_length=1, max_length=1024)
    auth_header_name: str = Field(default="Authorization", max_length=120)
    auth_header_value: str = Field(default="", max_length=4000)
    transport: Literal["http_jsonrpc", "stub"] = "http_jsonrpc"
    # When true (or transport=stub), seed tools_cache with known team tools.
    seed_stub_tools: bool = False


class McpToolCallIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class McpToolCallOut(BaseModel):
    ok: bool
    result: Any = None
    error: str = ""
