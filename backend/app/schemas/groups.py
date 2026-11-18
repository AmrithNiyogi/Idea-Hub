"""Pydantic I/O for collaboration groups and DMs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class GroupMemberOut(BaseModel):
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    name: str = ""
    email: str = ""
    avatar: int = 1
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class GroupInviteOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    group_name: str = ""
    invitee_id: uuid.UUID
    invited_by: uuid.UUID
    role: str
    status: str
    created_at: datetime
    responded_at: Optional[datetime] = None
    invitee_name: str = ""
    invitee_email: str = ""
    invitee_avatar: int = 1
    invitee_avatar_url: Optional[str] = None
    invited_by_name: str = ""

    model_config = {"from_attributes": True}


class GroupChannelOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    slug: str
    name: str
    description: str = ""
    kind: str = "text"
    sort_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupMessageOut(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    message_type: str = "user"
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupMeetingOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
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


class GroupMcpConnectionOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    idea_id: Optional[uuid.UUID] = None
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


class GroupSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str = ""
    kind: str = "group"
    idea_id: Optional[uuid.UUID] = None
    avatar_url: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    member_count: int = 0
    my_role: Optional[str] = None
    # For DMs: the other participant (when known).
    peer_user_id: Optional[uuid.UUID] = None
    peer_avatar: int = 1
    peer_avatar_url: Optional[str] = None


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str = ""
    kind: str = "group"
    idea_id: Optional[uuid.UUID] = None
    avatar_url: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    channels: list[GroupChannelOut] = Field(default_factory=list)
    members: list[GroupMemberOut] = Field(default_factory=list)
    pending_invites: list[GroupInviteOut] = Field(default_factory=list)
    can_post: bool = False
    can_manage: bool = False
    peer_user_id: Optional[uuid.UUID] = None
    peer_avatar: int = 1
    peer_avatar_url: Optional[str] = None


class GroupCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    idea_id: Optional[uuid.UUID] = None


class GroupUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    idea_id: Optional[uuid.UUID] = None
    clear_idea: bool = False
    avatar_url: Optional[str] = None
    clear_avatar: bool = False


class DmCreateIn(BaseModel):
    user_id: uuid.UUID


class GroupInviteCreateIn(BaseModel):
    user_id: uuid.UUID
    role: Literal["admin", "member"] = "member"


class GroupMessageCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=8000)

    @field_validator("body")
    @classmethod
    def _strip(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("Message body is required.")
        return text


class GroupChannelCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=64)
    description: str = Field(default="", max_length=500)
    kind: Literal["text", "announcements"] = "text"


class GroupMeetingCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    starts_at: datetime
    ends_at: Optional[datetime] = None
    description: str = Field(default="", max_length=4000)
    join_url: str = Field(default="", max_length=1024)
    channel_id: Optional[uuid.UUID] = None
    channel_slug: Optional[str] = Field(default=None, max_length=64)
    notify_teams: bool = True
    announce_in_channel: bool = True


class GroupMcpConnectionCreateIn(BaseModel):
    label: str = Field(default="default", max_length=120)
    endpoint_url: str = Field(min_length=1, max_length=1024)
    auth_header_name: str = Field(default="Authorization", max_length=120)
    auth_header_value: str = Field(default="", max_length=4000)
    transport: Literal["http_jsonrpc", "stub"] = "http_jsonrpc"
    seed_stub_tools: bool = False


class McpToolCallIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class McpToolCallOut(BaseModel):
    ok: bool
    result: Any = None
    error: str = ""
