"""Add org/user scope to tracker_connections for Integrations two-tier config.

Revision ID: integrations_001
Revises: trackers_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "integrations_001"
down_revision: Union[str, None] = "trackers_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracker_connections",
        sa.Column(
            "scope",
            sa.String(32),
            nullable=False,
            server_default="user",
        ),
    )
    op.add_column(
        "tracker_connections",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    # Backfill created_by from user_id for existing personal connections.
    op.execute(
        sa.text(
            "UPDATE tracker_connections SET created_by = user_id "
            "WHERE created_by IS NULL"
        )
    )
    op.alter_column(
        "tracker_connections",
        "created_by",
        nullable=False,
    )
    op.create_foreign_key(
        "fk_tracker_connections_created_by",
        "tracker_connections",
        "users",
        ["created_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    # Org defaults have no owning user — make user_id nullable.
    op.alter_column(
        "tracker_connections",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.drop_constraint(
        "uq_tracker_connection_user_provider_label",
        "tracker_connections",
        type_="unique",
    )
    # One personal connection per (user, provider, label).
    op.create_index(
        "uq_tracker_conn_user_provider_label",
        "tracker_connections",
        ["user_id", "provider_id", "label"],
        unique=True,
        postgresql_where=sa.text("scope = 'user'"),
    )
    # One org-default connection per (provider, label).
    op.create_index(
        "uq_tracker_conn_org_provider_label",
        "tracker_connections",
        ["provider_id", "label"],
        unique=True,
        postgresql_where=sa.text("scope = 'organization'"),
    )
    op.create_index(
        "ix_tracker_connections_scope",
        "tracker_connections",
        ["scope"],
    )


def downgrade() -> None:
    op.drop_index("ix_tracker_connections_scope", table_name="tracker_connections")
    op.drop_index(
        "uq_tracker_conn_org_provider_label",
        table_name="tracker_connections",
    )
    op.drop_index(
        "uq_tracker_conn_user_provider_label",
        table_name="tracker_connections",
    )
    # Org rows cannot survive a restore of NOT NULL user_id — delete them first.
    op.execute(
        sa.text(
            "DELETE FROM tracker_connections WHERE scope = 'organization'"
        )
    )
    op.alter_column(
        "tracker_connections",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint(
        "fk_tracker_connections_created_by",
        "tracker_connections",
        type_="foreignkey",
    )
    op.drop_column("tracker_connections", "created_by")
    op.drop_column("tracker_connections", "scope")
    op.create_unique_constraint(
        "uq_tracker_connection_user_provider_label",
        "tracker_connections",
        ["user_id", "provider_id", "label"],
    )
