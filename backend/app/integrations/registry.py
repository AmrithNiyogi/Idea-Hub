"""Unified Integrations catalog: live trackers + docs/chat adapters + stubs.

Adding a new *tracker* still goes through ``app.trackers.registry``.
Adding a non-tracker (Notion docs, Teams chat; Sheets later):

1. Implement its adapter (same connect/create/link surface as TrackerProvider).
2. Register it in ``app.integrations.adapters``.
3. It appears in this catalog with ``status=available`` and its
   ``integration_category`` (default ``docs``).
"""

from __future__ import annotations

from typing import Optional

from app.integrations.adapters import list_adapters, adapter_public_dict
from app.integrations.base import FUTURE_STUBS, IntegrationDescriptor
from app.trackers.base import ConnectField
from app.trackers.registry import list_providers as list_tracker_providers
from app.trackers.registry import provider_public_dict

_EXTRA: dict[str, IntegrationDescriptor] = {}


def register_integration(
    descriptor: IntegrationDescriptor, *, replace: bool = False
) -> None:
    if not descriptor.id:
        raise ValueError("IntegrationDescriptor.id must be non-empty")
    if descriptor.id in _EXTRA and not replace:
        raise ValueError(f"Integration already registered: {descriptor.id}")
    _EXTRA[descriptor.id] = descriptor


def get_integration(integration_id: str) -> IntegrationDescriptor:
    catalog = {d.id: d for d in list_integrations()}
    try:
        return catalog[integration_id]
    except KeyError as exc:
        raise KeyError(f"Unknown integration: {integration_id}") from exc


def list_integrations(
    *, category: Optional[str] = None
) -> list[IntegrationDescriptor]:
    """Merge trackers, docs/chat adapters, stubs, and extras."""
    items: dict[str, IntegrationDescriptor] = {}

    for p in list_tracker_providers():
        pub = provider_public_dict(p)
        fields = [
            ConnectField(
                key=f["key"],
                label=f["label"],
                secret=bool(f.get("secret")),
                required=bool(f.get("required", True)),
                placeholder=str(f.get("placeholder") or ""),
                help_text=str(f.get("help_text") or ""),
                advanced=bool(f.get("advanced")),
            )
            for f in pub.get("connect_fields") or []
        ]
        items[p.id] = IntegrationDescriptor(
            id=p.id,
            display_name=p.display_name,
            description=getattr(p, "description", "") or "",
            category="tracker",
            status="available",
            auth_mode=getattr(p, "auth_mode", "") or "",
            connect_fields=fields,
        )

    for p in list_adapters():
        pub = adapter_public_dict(p)
        fields = [
            ConnectField(
                key=f["key"],
                label=f["label"],
                secret=bool(f.get("secret")),
                required=bool(f.get("required", True)),
                placeholder=str(f.get("placeholder") or ""),
                help_text=str(f.get("help_text") or ""),
                advanced=bool(f.get("advanced")),
            )
            for f in pub.get("connect_fields") or []
        ]
        cat = getattr(p, "integration_category", None) or "docs"
        items[p.id] = IntegrationDescriptor(
            id=p.id,
            display_name=p.display_name,
            description=getattr(p, "description", "") or "",
            category=cat,  # type: ignore[arg-type]
            status="available",
            auth_mode=getattr(p, "auth_mode", "") or "",
            connect_fields=fields,
        )

    for stub in FUTURE_STUBS:
        items.setdefault(stub.id, stub)

    items.update(_EXTRA)

    out = sorted(items.values(), key=lambda d: (d.category, d.display_name.lower()))
    if category:
        out = [d for d in out if d.category == category]
    return out
