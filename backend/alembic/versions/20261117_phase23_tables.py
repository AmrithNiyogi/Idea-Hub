"""Phase 2+3 tables: delivery, ideathons, recognition.

Revision ID: phase23_001
Revises: None (attach after spine baseline — set ``down_revision`` to spine head)

Apply AFTER spine users/ideas tables exist. If spine Alembic head id is known,
set::

    down_revision = "<spine_head_revision>"

Until then this revision is standalone; merge with spine history carefully.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "phase23_001"
down_revision: Union[str, None] = "spine_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- delivery ----
    op.create_table(
        "delivery_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hours_granted", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False, server_default=""),
        sa.Column("announcement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idea_id"),
    )
    op.create_index("ix_delivery_projects_idea_id", "delivery_projects", ["idea_id"])

    op.create_table(
        "time_grant_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_hours", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("override", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
    )
    op.create_index("ix_time_grant_requests_idea_id", "time_grant_requests", ["idea_id"])
    op.create_index("ix_time_grant_requests_state", "time_grant_requests", ["state"])

    op.create_table(
        "time_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["delivery_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_time_logs_project_id", "time_logs", ["project_id"])

    op.create_table(
        "delivery_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_started"),
        sa.Column("blocker", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["delivery_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
    )
    op.create_index("ix_delivery_tasks_project_id", "delivery_tasks", ["project_id"])
    op.create_index("ix_delivery_tasks_idea_id", "delivery_tasks", ["idea_id"])

    op.create_table(
        "delivery_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["delivery_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["delivery_tasks.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_delivery_updates_project_id", "delivery_updates", ["project_id"])
    op.create_index("ix_delivery_updates_idea_id", "delivery_updates", ["idea_id"])

    op.create_table(
        "delivery_contributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="Builder"),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["delivery_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
        sa.UniqueConstraint("project_id", "user_id", name="uq_delivery_contributor"),
    )
    op.create_index("ix_delivery_contributors_project_id", "delivery_contributors", ["project_id"])

    op.create_table(
        "impact_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impact_type", sa.String(40), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False, server_default=""),
        sa.Column("baseline", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="low"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verify_note", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["project_id"], ["delivery_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"]),
    )
    op.create_index("ix_impact_entries_project_id", "impact_entries", ["project_id"])
    op.create_index("ix_impact_entries_idea_id", "impact_entries", ["idea_id"])

    op.create_table(
        "contribution_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("roles", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pct", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["delivery_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_contribution_share"),
    )
    op.create_index("ix_contribution_shares_project_id", "contribution_shares", ["project_id"])
    op.create_index("ix_contribution_shares_idea_id", "contribution_shares", ["idea_id"])

    op.create_table(
        "innovation_time_pools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("period_key", sa.String(16), nullable=False),
        sa.Column("budget_hours", sa.Integer(), nullable=False, server_default="400"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("period_key", name="uq_innovation_pool_period"),
    )

    # ---- ideathons ----
    op.create_table(
        "ideathons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("theme", sa.String(60), nullable=False),
        sa.Column("challenges", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sponsor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organiser_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phase", sa.String(20), nullable=False, server_default="open"),
        sa.Column("phase_log", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("shortlist", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("shortlisted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shortlist_edited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("voting_closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winners", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("results_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winner_override", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tally", postgresql.JSONB(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sponsor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organiser_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
    )
    op.create_index("ix_ideathons_phase", "ideathons", ["phase"])

    op.create_table(
        "ideathon_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ideathon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("linked_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ideathon_id"], ["ideathons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"]),
        sa.UniqueConstraint("idea_id", name="uq_ideathon_entry_idea"),
    )
    op.create_index("ix_ideathon_entries_ideathon_id", "ideathon_entries", ["ideathon_id"])
    op.create_index("ix_ideathon_entries_idea_id", "ideathon_entries", ["idea_id"])

    op.create_table(
        "pitch_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ideathon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ideathon_id"], ["ideathons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ideathon_id", "idea_id", "user_id", name="uq_pitch_score"),
    )
    op.create_index("ix_pitch_scores_ideathon_id", "pitch_scores", ["ideathon_id"])

    op.create_table(
        "audience_votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ideathon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ideathon_id"], ["ideathons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ideathon_id", "user_id", name="uq_audience_vote"),
    )
    op.create_index("ix_audience_votes_ideathon_id", "audience_votes", ["ideathon_id"])

    op.create_table(
        "ideathon_handoffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ideathon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(60), nullable=False, server_default="Backlog (simulated)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ideathon_id"], ["ideathons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sent_by"], ["users.id"]),
        sa.UniqueConstraint("ideathon_id", "idea_id", name="uq_ideathon_handoff"),
    )
    op.create_index("ix_ideathon_handoffs_ideathon_id", "ideathon_handoffs", ["ideathon_id"])

    # ---- recognition ----
    op.create_table(
        "points_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(40), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ref_id", sa.String(80), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("escrow", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("dedupe_key", name="uq_points_ledger_dedupe"),
    )
    op.create_index("ix_points_ledger_user_id", "points_ledger", ["user_id"])
    op.create_index("ix_points_ledger_rule_id", "points_ledger", ["rule_id"])
    op.create_index("ix_points_ledger_idea_id", "points_ledger", ["idea_id"])

    op.create_table(
        "badges",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("icon", sa.String(40), nullable=False, server_default=""),
        sa.Column("rule_text", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "badge_awards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("badge_id", sa.String(40), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_badge_award"),
    )
    op.create_index("ix_badge_awards_user_id", "badge_awards", ["user_id"])

    op.create_table(
        "recognition_awards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("nominee_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
    )
    op.create_index("ix_recognition_awards_kind", "recognition_awards", ["kind"])
    op.create_index("ix_recognition_awards_period", "recognition_awards", ["period"])


def downgrade() -> None:
    for table in (
        "recognition_awards",
        "badge_awards",
        "badges",
        "points_ledger",
        "ideathon_handoffs",
        "audience_votes",
        "pitch_scores",
        "ideathon_entries",
        "ideathons",
        "innovation_time_pools",
        "contribution_shares",
        "impact_entries",
        "delivery_contributors",
        "delivery_updates",
        "delivery_tasks",
        "time_logs",
        "time_grant_requests",
        "delivery_projects",
    ):
        op.drop_table(table)
