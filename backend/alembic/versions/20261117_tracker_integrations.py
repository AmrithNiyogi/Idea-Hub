"""External tracker connections and idea links (ClickUp / Jira / custom).

Revision ID: trackers_001
Revises: user_has_pw_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "trackers_001"
down_revision: Union[str, None] = "user_has_pw_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tracker_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("label", sa.String(120), nullable=False, server_default="default"),
        sa.Column("display_label", sa.String(255), nullable=False, server_default=""),
        sa.Column("credentials_encrypted", sa.Text(), nullable=False),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "external_account_id", sa.String(255), nullable=False, server_default=""
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "provider_id",
            "label",
            name="uq_tracker_connection_user_provider_label",
        ),
    )
    op.create_index(
        "ix_tracker_connections_user_id", "tracker_connections", ["user_id"]
    )
    op.create_index(
        "ix_tracker_connections_provider_id",
        "tracker_connections",
        ["provider_id"],
    )

    op.create_table(
        "idea_tracker_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column(
            "external_key", sa.String(255), nullable=False, server_default=""
        ),
        sa.Column(
            "external_url", sa.String(1024), nullable=False, server_default=""
        ),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["tracker_connections.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "idea_id",
            "provider_id",
            "external_id",
            name="uq_idea_tracker_link_external",
        ),
    )
    op.create_index(
        "ix_idea_tracker_links_idea_id", "idea_tracker_links", ["idea_id"]
    )
    op.create_index(
        "ix_idea_tracker_links_connection_id",
        "idea_tracker_links",
        ["connection_id"],
    )
    op.create_index(
        "ix_idea_tracker_links_provider_id",
        "idea_tracker_links",
        ["provider_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_idea_tracker_links_provider_id", table_name="idea_tracker_links")
    op.drop_index(
        "ix_idea_tracker_links_connection_id", table_name="idea_tracker_links"
    )
    op.drop_index("ix_idea_tracker_links_idea_id", table_name="idea_tracker_links")
    op.drop_table("idea_tracker_links")
    op.drop_index(
        "ix_tracker_connections_provider_id", table_name="tracker_connections"
    )
    op.drop_index("ix_tracker_connections_user_id", table_name="tracker_connections")
    op.drop_table("tracker_connections")
