"""Multi-select polls: per-option vote rows.

Revision ID: group_polls_002
Revises: group_polls_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "group_polls_002"
down_revision: Union[str, None] = "group_polls_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "group_polls",
        sa.Column("multi_select", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_constraint("uq_group_poll_vote_user", "group_poll_votes", type_="unique")
    op.create_unique_constraint(
        "uq_group_poll_vote_user_option",
        "group_poll_votes",
        ["poll_id", "user_id", "option_index"],
    )


def downgrade() -> None:
    # Keep one vote per voter before restoring the single-vote constraint.
    op.execute(
        """
        DELETE FROM group_poll_votes a
        USING group_poll_votes b
        WHERE a.poll_id = b.poll_id AND a.user_id = b.user_id AND a.id > b.id
        """
    )
    op.drop_constraint("uq_group_poll_vote_user_option", "group_poll_votes", type_="unique")
    op.create_unique_constraint(
        "uq_group_poll_vote_user", "group_poll_votes", ["poll_id", "user_id"]
    )
    op.drop_column("group_polls", "multi_select")
