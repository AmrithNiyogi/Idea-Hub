"""Pydantic contracts for the notifications inbox API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    """Single inbox row returned to the topbar drawer."""

    id: uuid.UUID = Field(..., description="Notification id.")
    kind: str = Field(
        ...,
        description="Event class (decision, needs_info, collab, hours, routed, …).",
        examples=["decision"],
    )
    idea_id: Optional[uuid.UUID] = Field(
        None, description="Related idea when the event is idea-scoped."
    )
    text: str = Field(..., description="Human-readable inbox copy.")
    href: str = Field(
        ...,
        description="App-relative deep link (e.g. /ideas/{id}).",
        examples=["/ideas/…"],
    )
    read: bool = Field(..., description="True after the recipient opened it.")
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured extras (role, outcome, …).",
    )
    created_at: datetime = Field(..., description="When the notification was created.")

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    """Inbox page plus unread badge count."""

    items: list[NotificationOut] = Field(
        ..., description="Newest-first notifications for the caller."
    )
    unread_count: int = Field(
        ..., ge=0, description="Total unread for the caller (not limited to page)."
    )


class UnreadCountOut(BaseModel):
    """Lightweight unread badge payload."""

    unread_count: int = Field(..., ge=0, description="Unread notifications for the caller.")


class MarkReadOut(BaseModel):
    """Result of mark-read / mark-all-read."""

    ok: bool = True
    updated: int = Field(
        0, ge=0, description="Number of rows flipped from unread to read."
    )
