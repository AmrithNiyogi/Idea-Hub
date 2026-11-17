"""Provider registry — single place to plug in new trackers.

How to add a custom tracker you build later
-------------------------------------------
1. Implement ``TrackerProvider`` (see ``app.trackers.base``) in a new module,
   e.g. ``app/trackers/my_tracker.py``.
2. Call ``register_provider(MyTrackerProvider())`` here (or from your package
   ``__init__`` imported by ``_ensure_builtins``).
3. Restart the API. ``GET /api/v1/trackers/providers``, Integrations, and Delivery
   list it automatically — no core flow rewrite. See ``docs/INTEGRATIONS.md``.

Until a dedicated class exists, use the built-in ``custom_webhook`` provider
with your create-task HTTPS endpoint.
"""

from __future__ import annotations

from typing import Any

from app.trackers.base import TrackerProvider

_REGISTRY: dict[str, TrackerProvider] = {}
_BUILTINS_LOADED = False


def register_provider(provider: TrackerProvider, *, replace: bool = False) -> None:
    """Register (or replace) a provider instance by ``provider.id``."""
    pid = getattr(provider, "id", None)
    if not pid or not isinstance(pid, str):
        raise ValueError("TrackerProvider.id must be a non-empty string")
    if pid in _REGISTRY and not replace:
        raise ValueError(f"Tracker provider already registered: {pid}")
    _REGISTRY[pid] = provider


def get_provider(provider_id: str) -> TrackerProvider:
    _ensure_builtins()
    try:
        return _REGISTRY[provider_id]
    except KeyError as exc:
        raise KeyError(f"Unknown tracker provider: {provider_id}") from exc


def list_providers() -> list[TrackerProvider]:
    _ensure_builtins()
    return [_REGISTRY[k] for k in sorted(_REGISTRY.keys())]


def provider_public_dict(provider: TrackerProvider) -> dict[str, Any]:
    """JSON-serializable provider descriptor for the API / UI."""
    normalized: list[dict[str, Any]] = []
    for f in list(getattr(provider, "connect_fields", []) or []):
        normalized.append(
            {
                "key": f.key,
                "label": f.label,
                "secret": bool(getattr(f, "secret", False)),
                "required": bool(getattr(f, "required", True)),
                "placeholder": str(getattr(f, "placeholder", "") or ""),
                "help_text": str(getattr(f, "help_text", "") or ""),
                "advanced": bool(getattr(f, "advanced", False)),
            }
        )
    return {
        "id": provider.id,
        "display_name": provider.display_name,
        "description": getattr(provider, "description", "") or "",
        "auth_mode": getattr(provider, "auth_mode", "") or "",
        "connect_fields": normalized,
    }


def _ensure_builtins() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    from app.trackers.clickup import ClickUpProvider
    from app.trackers.custom_webhook import CustomWebhookProvider
    from app.trackers.jira import JiraProvider

    for cls in (ClickUpProvider, JiraProvider, CustomWebhookProvider):
        inst = cls()
        if inst.id not in _REGISTRY:
            _REGISTRY[inst.id] = inst
    _BUILTINS_LOADED = True
