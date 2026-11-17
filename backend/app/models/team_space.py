"""Per-idea team collaboration space: channels, messages, meetings, MCP links.

Responsibilities:
- One TeamSpace per idea (lazy-created).
- Discord-like channels + messages for the build team.
- Meeting records (Teams webhook / MCP schedule path).
- Custom MCP connection configs attachable to a space.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TeamSpace(Base):
    """Collaboration workspace for one idea's delivery team."""

    __tablename__ = "team_spaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TeamChannel(Base):
    """Named channel inside a team space (general, decisions, blockers, …)."""

    __tablename__ = "team_channels"
    __table_args__ = (
        UniqueConstraint("space_id", "slug", name="uq_team_channel_space_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("team_spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default="text"
    )
    # text | announcements
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TeamMessage(Base):
    """Chat message posted to a team channel."""

    __tablename__ = "team_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("team_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # system | user | meeting | mcp
    message_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="user"
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class TeamMeeting(Base):
    """Scheduled meeting announced to the team (and optionally Teams)."""

    __tablename__ = "team_meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("team_spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("team_channels.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    join_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # none | teams_webhook | mcp
    notify_via: Mapped[str] = mapped_column(
        String(40), nullable=False, default="none"
    )
    notify_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="pending"
    )
    # pending | posted | skipped | failed
    notify_detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IdeaMcpConnection(Base):
    """Custom MCP endpoint attached to an idea's team space.

    Credentials (auth header value) are Fernet-encrypted JSON — never returned
    by the API. Discovery caches tool names/descriptions in ``tools_cache``.
    """

    __tablename__ = "idea_mcp_connections"
    __table_args__ = (
        UniqueConstraint(
            "space_id", "label", name="uq_idea_mcp_space_label"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("team_spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    endpoint_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    auth_header_name: Mapped[str] = mapped_column(
        String(120), nullable=False, default="Authorization"
    )
    # Fernet-encrypted {"auth_header_value": "…"} — empty string if none.
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")
    transport: Mapped[str] = mapped_column(
        String(40), nullable=False, default="http_jsonrpc"
    )
    # http_jsonrpc | stub
    tools_cache: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    last_discovered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
