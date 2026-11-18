"""Group invites, soft-delete, avatar, and DM kind.

Revision ID: groups_002
Revises: groups_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "groups_002"
down_revision: Union[str, None] = "groups_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if _has_table("hub_groups"):
        if not _has_column("hub_groups", "kind"):
            op.add_column(
                "hub_groups",
                sa.Column(
                    "kind",
                    sa.String(length=16),
                    nullable=False,
                    server_default="group",
                ),
            )
            op.create_index("ix_hub_groups_kind", "hub_groups", ["kind"])
        if not _has_column("hub_groups", "deleted_at"):
            op.add_column(
                "hub_groups",
                sa.Column(
                    "deleted_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            )
            op.create_index(
                "ix_hub_groups_deleted_at", "hub_groups", ["deleted_at"]
            )
        if not _has_column("hub_groups", "avatar_url"):
            op.add_column(
                "hub_groups",
                sa.Column(
                    "avatar_url",
                    sa.String(length=512),
                    nullable=True,
                ),
            )
        if not _has_column("hub_groups", "dm_pair_key"):
            op.add_column(
                "hub_groups",
                sa.Column("dm_pair_key", sa.String(length=80), nullable=True),
            )
            op.create_index(
                "ix_hub_groups_dm_pair_key",
                "hub_groups",
                ["dm_pair_key"],
                unique=True,
            )

    if not _has_table("group_invites"):
        op.create_table(
            "group_invites",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "group_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("hub_groups.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "invitee_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "invited_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "role",
                sa.String(length=32),
                nullable=False,
                server_default="member",
            ),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "responded_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.create_index("ix_group_invites_group_id", "group_invites", ["group_id"])
        op.create_index(
            "ix_group_invites_invitee_id", "group_invites", ["invitee_id"]
        )
        op.create_index("ix_group_invites_status", "group_invites", ["status"])
        op.create_index(
            "uq_group_invite_pending",
            "group_invites",
            ["group_id", "invitee_id"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
        )


def downgrade() -> None:
    if _has_table("group_invites"):
        op.drop_index("uq_group_invite_pending", table_name="group_invites")
        op.drop_index("ix_group_invites_status", table_name="group_invites")
        op.drop_index("ix_group_invites_invitee_id", table_name="group_invites")
        op.drop_index("ix_group_invites_group_id", table_name="group_invites")
        op.drop_table("group_invites")
    if _has_table("hub_groups"):
        if _has_column("hub_groups", "dm_pair_key"):
            op.drop_index("ix_hub_groups_dm_pair_key", table_name="hub_groups")
            op.drop_column("hub_groups", "dm_pair_key")
        if _has_column("hub_groups", "avatar_url"):
            op.drop_column("hub_groups", "avatar_url")
        if _has_column("hub_groups", "deleted_at"):
            op.drop_index("ix_hub_groups_deleted_at", table_name="hub_groups")
            op.drop_column("hub_groups", "deleted_at")
        if _has_column("hub_groups", "kind"):
            op.drop_index("ix_hub_groups_kind", table_name="hub_groups")
            op.drop_column("hub_groups", "kind")
