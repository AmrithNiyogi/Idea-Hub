"""Group MCP rows can reference an Integrations MCP connection.

Revision ID: group_mcp_ref_001
Revises: group_polls_002
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "group_mcp_ref_001"
down_revision: Union[str, None] = "group_polls_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "group_mcp_connections",
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracker_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_group_mcp_connections_connection_id",
        "group_mcp_connections",
        ["connection_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_group_mcp_connections_connection_id", table_name="group_mcp_connections")
    op.drop_column("group_mcp_connections", "connection_id")
