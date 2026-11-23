"""External tracker / integration connections and idea ↔ remote work-item links."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TrackerConnection(Base):
    """Encrypted credentials for one integration provider.

    Two-tier ownership via ``scope``:

    - ``user`` — personal override; ``user_id`` is the owner.
    - ``organization`` — admin-set org default; ``user_id`` is null.

    Resolution when linking from an idea: user connection for that provider,
    else org default, else prompt to connect (see Integrations docs).
    """

    __tablename__ = "tracker_connections"
    # Unique constraints are partial indexes (see Alembic integrations_001).

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="user", index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    display_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Fernet-encrypted JSON credentials — never expose via API.
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    external_account_id: Mapped[str] = mapped_column(
        String(255), nullable=False, default=""
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


class IdeaTrackerLink(Base):
    """Link from an IdeaKonnekt idea to a remote tracker work item."""

    __tablename__ = "idea_tracker_links"
    __table_args__ = (
        UniqueConstraint(
            "idea_id",
            "provider_id",
            "external_id",
            name="uq_idea_tracker_link_external",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    idea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracker_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    external_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
