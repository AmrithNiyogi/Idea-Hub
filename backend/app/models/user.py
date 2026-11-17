"""User and Team ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Team(Base):
    """Organizational team owning a lead and member users."""

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", use_alter=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list["User"]] = relationship(
        "User",
        back_populates="team",
        foreign_keys="User.team_id",
    )


class User(Base):
    """Authenticated Idea Hub person with multi-role membership.

    Responsibilities:
    - Persist credentials and profile fields used by auth and UI.
    - Hold the full role set; active role lives on the JWT for the session.

    Collaborators:
    - Team (optional membership)
    - Auth / OTP services (read-only for login)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    has_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc=(
            "True when the user can authenticate with a known password "
            "(seed / password change). False for Microsoft SSO-only accounts "
            "created with a random unusable hash."
        ),
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True
    )
    roles: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    primary_role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="contributor"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )
    avatar: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, default=None
    )
    slug: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    totp_secret: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Fernet-encrypted TOTP shared secret; null when MFA is not enrolled.",
    )
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="True after the user confirms enrollment with a valid authenticator code.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    team: Mapped[Optional[Team]] = relationship(
        "Team",
        back_populates="members",
        foreign_keys=[team_id],
    )
