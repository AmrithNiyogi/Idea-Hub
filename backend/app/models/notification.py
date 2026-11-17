"""Persisted in-app notification rows.

Responsibilities:
- Store per-user inbox items created by domain event fan-out.
- Track unread state for the topbar bell / drawer.

Collaborators:
- ``User`` (recipient)
- ``Idea`` (optional deep-link subject)
- ``NotificationService`` (only writer besides mark-read)

Must never:
- Send email (email adapter owns SMTP).
- Encode business rules about who should be notified.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Notification(Base):
    """One inbox row for a single recipient.

    ``kind`` is a stable event class used by the UI and by email gating
    (e.g. ``decision``, ``needs_info``, ``collab``, ``hours``, ``routed``).
    ``href`` is an app-relative path such as ``/ideas/{id}``.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ideas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    href: Mapped[str] = mapped_column(String(400), nullable=False, default="/")
    read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
