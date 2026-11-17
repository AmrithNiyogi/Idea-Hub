"""Add users.avatar_url for profile image / URL.

Revision ID: user_avatar_001
Revises: phase456_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "user_avatar_001"
down_revision: Union[str, None] = "phase456_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
