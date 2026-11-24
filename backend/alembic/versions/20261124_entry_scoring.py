"""Event kind, entry documents, saved AI entry scores, and idea AI review.

Revision ID: entry_scoring_001
Revises: group_polls_003
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "entry_scoring_001"
down_revision: Union[str, None] = "group_polls_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ideathons",
        sa.Column("kind", sa.String(16), nullable=False, server_default="ideathon"),
    )
    op.add_column("ideas", sa.Column("ai_review", postgresql.JSONB(), nullable=True))
    op.create_table(
        "entry_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_entry_documents_idea_id", "entry_documents", ["idea_id"])
    op.create_table(
        "entry_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ideathon_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideathons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ideas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("overall", sa.Float(), nullable=True),
        sa.Column("criteria", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("engine", sa.String(80), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rubric_version", sa.String(20), nullable=False),
        sa.Column(
            "scored_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "scored_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("ideathon_id", "idea_id", name="uq_entry_score"),
    )
    op.create_index("ix_entry_scores_ideathon_id", "entry_scores", ["ideathon_id"])


def downgrade() -> None:
    op.drop_index("ix_entry_scores_ideathon_id", table_name="entry_scores")
    op.drop_table("entry_scores")
    op.drop_index("ix_entry_documents_idea_id", table_name="entry_documents")
    op.drop_table("entry_documents")
    op.drop_column("ideas", "ai_review")
    op.drop_column("ideathons", "kind")
