"""Idea team name and GitHub repository link.

Revision ID: idea_team_github_001
Revises: service_tokens_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "idea_team_github_001"
down_revision: Union[str, None] = "service_tokens_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("team_name", sa.String(120), nullable=True))
    op.add_column("ideas", sa.Column("github_url", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("ideas", "github_url")
    op.drop_column("ideas", "team_name")
