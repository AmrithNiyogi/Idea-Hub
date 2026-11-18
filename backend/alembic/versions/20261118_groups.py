"""First-class collaboration groups (channels, messages, meetings, MCP).

Replaces idea-1:1 team_spaces with hub_groups that can exist without an idea.
If team_spaces already exists (team_space_001), data is migrated.

Revision ID: groups_001
Revises: integrations_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "groups_001"
down_revision: Union[str, None] = "team_space_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def upgrade() -> None:
    if _has_table("team_spaces") and not _has_table("hub_groups"):
        _migrate_from_team_spaces()
        return
    if _has_table("hub_groups"):
        return
    _create_fresh()


def _create_fresh() -> None:
    op.create_table(
        "hub_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideas.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
    op.create_index("ix_hub_groups_idea_id", "hub_groups", ["idea_id"], unique=True)

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member_user"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    op.create_table(
        "group_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
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
        sa.UniqueConstraint("group_id", "slug", name="uq_group_channel_slug"),
    )
    op.create_index("ix_group_channels_group_id", "group_channels", ["group_id"])

    op.create_table(
        "group_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("group_channels.id", ondelete="CASCADE"),
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
    op.create_index("ix_group_messages_channel_id", "group_messages", ["channel_id"])
    op.create_index("ix_group_messages_author_id", "group_messages", ["author_id"])
    op.create_index("ix_group_messages_created_at", "group_messages", ["created_at"])

    op.create_table(
        "group_meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("group_channels.id", ondelete="SET NULL"),
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
    op.create_index("ix_group_meetings_group_id", "group_meetings", ["group_id"])

    op.create_table(
        "group_mcp_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideas.id", ondelete="SET NULL"),
            nullable=True,
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
        sa.UniqueConstraint("group_id", "label", name="uq_group_mcp_label"),
    )
    op.create_index(
        "ix_group_mcp_connections_group_id", "group_mcp_connections", ["group_id"]
    )


def _migrate_from_team_spaces() -> None:
    """Evolve team_space_001 tables into hub_groups schema."""
    op.rename_table("team_spaces", "hub_groups")
    op.execute('ALTER TABLE hub_groups RENAME COLUMN title TO name')
    op.add_column(
        "hub_groups",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.drop_constraint("team_spaces_idea_id_key", "hub_groups", type_="unique")
    op.drop_index("ix_team_spaces_idea_id", table_name="hub_groups")
    op.alter_column("hub_groups", "idea_id", nullable=True)
    op.create_index("ix_hub_groups_idea_id", "hub_groups", ["idea_id"], unique=True)
    # idea FK was CASCADE; recreate as SET NULL for optional link
    op.drop_constraint("team_spaces_idea_id_fkey", "hub_groups", type_="foreignkey")
    op.create_foreign_key(
        "hub_groups_idea_id_fkey",
        "hub_groups",
        "ideas",
        ["idea_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member_user"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])
    op.execute(
        """
        INSERT INTO group_members (id, group_id, user_id, role, joined_at)
        SELECT gen_random_uuid(), id, created_by, 'owner', created_at
        FROM hub_groups
        ON CONFLICT DO NOTHING
        """
    )

    op.rename_table("team_channels", "group_channels")
    op.execute('ALTER TABLE group_channels RENAME COLUMN space_id TO group_id')
    op.drop_constraint("uq_team_channel_space_slug", "group_channels", type_="unique")
    op.create_unique_constraint(
        "uq_group_channel_slug", "group_channels", ["group_id", "slug"]
    )
    op.drop_index("ix_team_channels_space_id", table_name="group_channels")
    op.create_index("ix_group_channels_group_id", "group_channels", ["group_id"])

    op.rename_table("team_messages", "group_messages")
    op.drop_index("ix_team_messages_channel_id", table_name="group_messages")
    op.drop_index("ix_team_messages_author_id", table_name="group_messages")
    op.drop_index("ix_team_messages_created_at", table_name="group_messages")
    op.create_index("ix_group_messages_channel_id", "group_messages", ["channel_id"])
    op.create_index("ix_group_messages_author_id", "group_messages", ["author_id"])
    op.create_index("ix_group_messages_created_at", "group_messages", ["created_at"])

    op.rename_table("team_meetings", "group_meetings")
    op.execute('ALTER TABLE group_meetings RENAME COLUMN space_id TO group_id')
    op.drop_index("ix_team_meetings_space_id", table_name="group_meetings")
    op.create_index("ix_group_meetings_group_id", "group_meetings", ["group_id"])

    if _has_table("idea_mcp_connections"):
        op.rename_table("idea_mcp_connections", "group_mcp_connections")
        op.execute(
            'ALTER TABLE group_mcp_connections RENAME COLUMN space_id TO group_id'
        )
        op.alter_column("group_mcp_connections", "idea_id", nullable=True)
        op.drop_constraint(
            "uq_idea_mcp_space_label", "group_mcp_connections", type_="unique"
        )
        op.create_unique_constraint(
            "uq_group_mcp_label", "group_mcp_connections", ["group_id", "label"]
        )
        op.drop_index(
            "ix_idea_mcp_connections_space_id", table_name="group_mcp_connections"
        )
        op.drop_index(
            "ix_idea_mcp_connections_idea_id", table_name="group_mcp_connections"
        )
        op.create_index(
            "ix_group_mcp_connections_group_id",
            "group_mcp_connections",
            ["group_id"],
        )
        op.drop_constraint(
            "idea_mcp_connections_idea_id_fkey",
            "group_mcp_connections",
            type_="foreignkey",
        )
        op.create_foreign_key(
            "group_mcp_connections_idea_id_fkey",
            "group_mcp_connections",
            "ideas",
            ["idea_id"],
            ["id"],
            ondelete="SET NULL",
        )
    elif not _has_table("group_mcp_connections"):
        op.create_table(
            "group_mcp_connections",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "group_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "idea_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("ideas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "label", sa.String(120), nullable=False, server_default="default"
            ),
            sa.Column("endpoint_url", sa.String(1024), nullable=False),
            sa.Column(
                "auth_header_name",
                sa.String(120),
                nullable=False,
                server_default="Authorization",
            ),
            sa.Column(
                "credentials_encrypted",
                sa.Text(),
                nullable=False,
                server_default="",
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
            sa.Column(
                "last_discovered_at", sa.DateTime(timezone=True), nullable=True
            ),
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
            sa.UniqueConstraint("group_id", "label", name="uq_group_mcp_label"),
        )
        op.create_index(
            "ix_group_mcp_connections_group_id",
            "group_mcp_connections",
            ["group_id"],
        )


def downgrade() -> None:
    if _has_table("group_mcp_connections"):
        op.drop_table("group_mcp_connections")
    if _has_table("group_meetings"):
        op.drop_table("group_meetings")
    if _has_table("group_messages"):
        op.drop_table("group_messages")
    if _has_table("group_channels"):
        op.drop_table("group_channels")
    if _has_table("group_members"):
        op.drop_table("group_members")
    if _has_table("hub_groups"):
        op.drop_table("hub_groups")
