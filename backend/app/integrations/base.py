"""Integration catalog metadata — categories beyond trackers.

Fully wired providers (ClickUp/Jira/custom) implement ``TrackerProvider`` and
are mirrored here as ``available``. Notion is a docs adapter (see
``app.integrations.notion``). Sheets / Teams remain ``coming_soon`` stubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from app.trackers.base import ConnectField

IntegrationCategory = Literal["tracker", "docs", "chat", "sheets"]
IntegrationStatus = Literal["available", "coming_soon"]


@dataclass(frozen=True)
class IntegrationDescriptor:
    """Public catalog entry for Integrations UI + API."""

    id: str
    display_name: str
    description: str
    category: IntegrationCategory
    status: IntegrationStatus = "available"
    auth_mode: str = ""
    connect_fields: list[ConnectField] = field(default_factory=list)
    # When status=available and category=tracker, credentials flow through
    # the TrackerProvider registry under the same id.
    coming_soon_note: str = ""

    def public_dict(self) -> dict[str, Any]:
        fields: list[dict[str, Any]] = []
        for f in self.connect_fields:
            fields.append(
                {
                    "key": f.key,
                    "label": f.label,
                    "secret": bool(getattr(f, "secret", False)),
                    "required": bool(getattr(f, "required", True)),
                    "placeholder": str(getattr(f, "placeholder", "") or ""),
                    "help_text": str(getattr(f, "help_text", "") or ""),
                }
            )
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "auth_mode": self.auth_mode,
            "connect_fields": fields,
            "coming_soon_note": self.coming_soon_note,
            "connectable": self.status == "available" and bool(fields),
        }


# Convenience aliases used by stubs
STUB_SHEETS = IntegrationDescriptor(
    id="google_sheets",
    display_name="Google Sheets",
    description="Export idea metrics and delivery status to a spreadsheet.",
    category="sheets",
    status="coming_soon",
    auth_mode="oauth",
    coming_soon_note="OAuth connect and sheet mapping ship in a later release.",
)

STUB_TEAMS = IntegrationDescriptor(
    id="teams",
    display_name="Microsoft Teams",
    description="Post idea status updates to a Teams channel.",
    category="chat",
    status="coming_soon",
    auth_mode="oauth",
    coming_soon_note="Teams bot / webhook notifications are planned.",
)

FUTURE_STUBS: tuple[IntegrationDescriptor, ...] = (
    STUB_SHEETS,
    STUB_TEAMS,
)
