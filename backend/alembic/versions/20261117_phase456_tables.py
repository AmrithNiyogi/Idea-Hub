"""Phase 4+5+6 tables: admin, agents, problems, reopen, collab.

Revision ID: phase456_001
Revises: phase23_001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "phase456_001"
down_revision: Union[str, None] = "phase23_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column(
            "value",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
    )

    op.create_table(
        "review_panels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column(
            "member_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("chair_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chair_id"], ["users.id"]),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("category_id"),
    )
    op.create_index("ix_review_panels_category_id", "review_panels", ["category_id"])

    op.create_table(
        "admin_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("section", sa.String(80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "changes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("event", sa.String(80), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "output",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "engine", sa.String(64), nullable=False, server_default="mock-heuristic-v1"
        ),
        sa.Column(
            "approval_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("approval_role", sa.String(32), nullable=True),
        sa.Column(
            "approval_state", sa.String(20), nullable=False, server_default="none"
        ),
        sa.Column("proposal_key", sa.String(160), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_agent_runs_agent_id", "agent_runs", ["agent_id"])
    op.create_index("ix_agent_runs_event", "agent_runs", ["event"])
    op.create_index("ix_agent_runs_idea_id", "agent_runs", ["idea_id"])
    op.create_index("ix_agent_runs_proposal_key", "agent_runs", ["proposal_key"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])

    op.create_table(
        "proposal_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("proposal_key", sa.String(160), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("snooze_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.UniqueConstraint("proposal_key"),
    )
    op.create_index(
        "ix_proposal_decisions_proposal_key", "proposal_decisions", ["proposal_key"]
    )

    op.create_table(
        "kompass_answers",
        sa.Column("question_id", sa.String(16), primary_key=True),
        sa.Column(
            "answered", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("answered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["answered_by"], ["users.id"]),
    )

    op.create_table(
        "problem_me_too",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cluster_key", sa.String(80), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cluster_key", "user_id", name="uq_problem_me_user"),
    )
    op.create_index("ix_problem_me_too_cluster_key", "problem_me_too", ["cluster_key"])
    op.create_index("ix_problem_me_too_user_id", "problem_me_too", ["user_id"])

    op.create_table(
        "problem_meta",
        sa.Column("cluster_key", sa.String(80), primary_key=True),
        sa.Column("custom_label", sa.String(200), nullable=False, server_default=""),
        sa.Column("sponsor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sponsor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"]),
    )

    op.create_table(
        "reopen_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule", sa.String(8), nullable=False, server_default="any"),
        sa.Column(
            "conds",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.UniqueConstraint("idea_id"),
    )
    op.create_index("ix_reopen_conditions_idea_id", "reopen_conditions", ["idea_id"])

    op.create_table(
        "collab_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("role", sa.String(80), nullable=False, server_default=""),
        sa.Column("hours", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(40), nullable=False, server_default=""),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
    )
    op.create_index("ix_collab_requests_idea_id", "collab_requests", ["idea_id"])
    op.create_index(
        "ix_collab_requests_from_user_id", "collab_requests", ["from_user_id"]
    )
    op.create_index("ix_collab_requests_status", "collab_requests", ["status"])

    op.create_table(
        "tracker_milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="not_started"
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocker", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_tracker_milestones_idea_id", "tracker_milestones", ["idea_id"])

    op.create_table(
        "tracker_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("percent_complete", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
    )
    op.create_index("ix_tracker_checkins_idea_id", "tracker_checkins", ["idea_id"])


def downgrade() -> None:
    op.drop_table("tracker_checkins")
    op.drop_table("tracker_milestones")
    op.drop_table("collab_requests")
    op.drop_table("reopen_conditions")
    op.drop_table("problem_meta")
    op.drop_table("problem_me_too")
    op.drop_table("kompass_answers")
    op.drop_table("proposal_decisions")
    op.drop_table("agent_runs")
    op.drop_table("admin_audit")
    op.drop_table("review_panels")
    op.drop_table("platform_settings")
