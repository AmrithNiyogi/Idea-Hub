"""Persisted notifications inbox.

Revision ID: notifications_001
Revises: user_avatar_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "notifications_001"
down_revision: Union[str, None] = "user_avatar_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("href", sa.String(400), nullable=False, server_default="/"),
        sa.Column(
            "read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["idea_id"], ["ideas.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_kind", "notifications", ["kind"])
    op.create_index("ix_notifications_idea_id", "notifications", ["idea_id"])
    op.create_index("ix_notifications_read", "notifications", ["read"])
    op.create_index(
        "ix_notifications_created_at", "notifications", ["created_at"]
    )
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_read", table_name="notifications")
    op.drop_index("ix_notifications_idea_id", table_name="notifications")
    op.drop_index("ix_notifications_kind", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
