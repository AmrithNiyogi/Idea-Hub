"""AI Newsletter stored stories and per-category state.

Revision ID: news_001
Revises: groups_002
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "news_001"
down_revision: Union[str, None] = "groups_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_relevance", sa.Float(), nullable=False),
        sa.UniqueConstraint("category", "url", name="uq_news_item_category_url"),
    )
    op.create_index("ix_news_items_category", "news_items", ["category"])
    op.create_table(
        "news_category_state",
        sa.Column("category", sa.String(40), primary_key=True),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("news_category_state")
    op.drop_index("ix_news_items_category", table_name="news_items")
    op.drop_table("news_items")
