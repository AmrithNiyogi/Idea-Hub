"""Poll end time (auto-close).

Revision ID: group_polls_003
Revises: group_mcp_ref_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "group_polls_003"
down_revision: Union[str, None] = "group_mcp_ref_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "group_polls",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("group_polls", "ends_at")
