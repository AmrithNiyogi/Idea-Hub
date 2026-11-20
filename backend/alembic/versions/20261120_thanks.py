"""Written thanks between teammates (capped per giver per month).

Revision ID: thanks_001
Revises: news_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "thanks_001"
down_revision: Union[str, None] = "news_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recognition_thanks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "from_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_recognition_thanks_from_user_id", "recognition_thanks", ["from_user_id"])
    op.create_index("ix_recognition_thanks_to_user_id", "recognition_thanks", ["to_user_id"])


def downgrade() -> None:
    op.drop_index("ix_recognition_thanks_to_user_id", table_name="recognition_thanks")
    op.drop_index("ix_recognition_thanks_from_user_id", table_name="recognition_thanks")
    op.drop_table("recognition_thanks")
