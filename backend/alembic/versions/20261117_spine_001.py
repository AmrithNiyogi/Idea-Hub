"""Spine baseline: users, teams, categories, ideas, engagement, review.

Revision ID: spine_001
Revises: None
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "spine_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("title", sa.String(160), nullable=False, server_default=""),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "roles",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "primary_role", sa.String(32), nullable=False, server_default="contributor"
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("avatar", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_slug", "users", ["slug"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_team_id", "users", ["team_id"])

    op.create_foreign_key(
        "fk_teams_lead_id_users",
        "teams",
        "users",
        ["lead_id"],
        ["id"],
        use_alter=True,
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("color", sa.String(64), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "ideas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("problem", sa.Text(), nullable=False, server_default=""),
        sa.Column("solution", sa.Text(), nullable=False, server_default=""),
        sa.Column("beneficiaries", sa.Text(), nullable=False, server_default=""),
        sa.Column("effort", sa.String(8), nullable=False, server_default="M"),
        sa.Column("success_metrics", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "anonymous", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "co_author_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column(
            "is_draft", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "awaiting_owner",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("hours_recommended", sa.Integer(), nullable=True),
        sa.Column("needs_info_question", sa.Text(), nullable=True),
        sa.Column("withdraw_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ideathon_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revisit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage_entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["merged_into_id"], ["ideas.id"]),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_ideas_slug", "ideas", ["slug"])
    op.create_index("ix_ideas_status", "ideas", ["status"])
    op.create_index("ix_ideas_author_id", "ideas", ["author_id"])
    op.create_index("ix_ideas_owner_id", "ideas", ["owner_id"])
    op.create_index("ix_ideas_category_id", "ideas", ["category_id"])
    op.create_index("ix_ideas_ideathon_id", "ideas", ["ideathon_id"])

    op.create_table(
        "status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
    )
    op.create_index("ix_status_history_idea_id", "status_history", ["idea_id"])

    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="comment"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
    )
    op.create_index("ix_comments_idea_id", "comments", ["idea_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("idea_id", "user_id", name="uq_votes_idea_user"),
    )
    op.create_index("ix_votes_idea_id", "votes", ["idea_id"])
    op.create_index("ix_votes_user_id", "votes", ["user_id"])

    op.create_table(
        "follows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("idea_id", "user_id", name="uq_follows_idea_user"),
    )
    op.create_index("ix_follows_idea_id", "follows", ["idea_id"])
    op.create_index("ix_follows_user_id", "follows", ["user_id"])

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=True),
        sa.Column("effort", sa.Integer(), nullable=True),
        sa.Column("alignment", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.UniqueConstraint(
            "idea_id", "reviewer_id", name="uq_reviews_idea_reviewer"
        ),
    )
    op.create_index("ix_reviews_idea_id", "reviews", ["idea_id"])
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "as_role", sa.String(32), nullable=False, server_default="reviewer"
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "awaiting_owner",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("hours", sa.Integer(), nullable=True),
        sa.Column("revisit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_mind", sa.Text(), nullable=False, server_default=""),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("impact", sa.Integer(), nullable=True),
        sa.Column("effort", sa.Integer(), nullable=True),
        sa.Column("alignment", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decider_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["merged_into_id"], ["ideas.id"]),
    )
    op.create_index("ix_decisions_idea_id", "decisions", ["idea_id"])
    op.create_index("ix_decisions_decider_id", "decisions", ["decider_id"])


def downgrade() -> None:
    op.drop_table("decisions")
    op.drop_table("reviews")
    op.drop_table("follows")
    op.drop_table("votes")
    op.drop_table("comments")
    op.drop_table("status_history")
    op.drop_table("ideas")
    op.drop_table("categories")
    op.drop_constraint("fk_teams_lead_id_users", "teams", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("teams")
