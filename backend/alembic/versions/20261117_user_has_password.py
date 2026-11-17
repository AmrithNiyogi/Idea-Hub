"""Add users.has_password for password-login vs SSO-only MFA policy.

Revision ID: user_has_pw_001
Revises: user_totp_001

SSO-created accounts store a random unusable bcrypt hash; ``has_password``
distinguishes those from seed / password-linked accounts that may enroll TOTP.
Existing rows default to true (seed users and any pre-flag password accounts).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "user_has_pw_001"
down_revision: Union[str, None] = "user_totp_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "has_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "has_password")
