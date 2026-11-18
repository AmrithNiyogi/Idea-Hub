"""Team collaboration space (superseded by groups_001).

Kept so databases already stamped at team_space_001 can upgrade.
Fresh installs: integrations_001 → team_space_001 → groups_001
(groups_001 migrates these tables into hub_groups).

Revision ID: team_space_001
Revises: integrations_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "team_space_001"
down_revision: Union[str, None] = "integrations_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    if _has_table("team_spaces") or _has_table("hub_groups"):
        return
    op.create_table(
        "team_spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideas.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_team_spaces_idea_id", "team_spaces", ["idea_id"])

    op.create_table(
        "team_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "space_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(32), nullable=False, server_default="text"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("space_id", "slug", name="uq_team_channel_space_slug"),
    )
    op.create_index("ix_team_channels_space_id", "team_channels", ["space_id"])

    op.create_table(
        "team_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "message_type", sa.String(32), nullable=False, server_default="user"
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_team_messages_channel_id", "team_messages", ["channel_id"])
    op.create_index("ix_team_messages_author_id", "team_messages", ["author_id"])
    op.create_index("ix_team_messages_created_at", "team_messages", ["created_at"])

    op.create_table(
        "team_meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "space_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team_channels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("join_url", sa.String(1024), nullable=False, server_default=""),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "notify_via", sa.String(40), nullable=False, server_default="none"
        ),
        sa.Column(
            "notify_status",
            sa.String(40),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("notify_detail", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_team_meetings_space_id", "team_meetings", ["space_id"])

    op.create_table(
        "idea_mcp_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "space_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(120), nullable=False, server_default="default"),
        sa.Column("endpoint_url", sa.String(1024), nullable=False),
        sa.Column(
            "auth_header_name",
            sa.String(120),
            nullable=False,
            server_default="Authorization",
        ),
        sa.Column(
            "credentials_encrypted", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column(
            "transport",
            sa.String(40),
            nullable=False,
            server_default="http_jsonrpc",
        ),
        sa.Column(
            "tools_cache",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("space_id", "label", name="uq_idea_mcp_space_label"),
    )
    op.create_index(
        "ix_idea_mcp_connections_space_id", "idea_mcp_connections", ["space_id"]
    )
    op.create_index(
        "ix_idea_mcp_connections_idea_id", "idea_mcp_connections", ["idea_id"]
    )


def downgrade() -> None:
    if not _has_table("team_spaces"):
        return
    if _has_table("idea_mcp_connections"):
        op.drop_table("idea_mcp_connections")
    if _has_table("team_meetings"):
        op.drop_table("team_meetings")
    if _has_table("team_messages"):
        op.drop_table("team_messages")
    if _has_table("team_channels"):
        op.drop_table("team_channels")
    op.drop_table("team_spaces")
