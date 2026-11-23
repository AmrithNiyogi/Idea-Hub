"""Idea live project (demo) link.

Revision ID: idea_demo_url_001
Revises: idea_team_github_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "idea_demo_url_001"
down_revision: Union[str, None] = "idea_team_github_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("demo_url", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("ideas", "demo_url")
