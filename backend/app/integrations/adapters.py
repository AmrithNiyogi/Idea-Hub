"""Non-tracker integration adapters (docs / chat / sheets).

These implement the same connect/create/link surface as ``TrackerProvider``
so ``TrackerService`` can encrypt credentials and store idea links without a
second persistence path. They stay out of ``app.trackers.registry`` so
``GET /trackers/providers`` remains tracker-only.
"""

from __future__ import annotations

from typing import Any

from app.trackers.base import TrackerProvider
from app.trackers.registry import get_provider as get_tracker_provider
from app.trackers.registry import provider_public_dict

_ADAPTERS: dict[str, TrackerProvider] = {}
_BUILTINS_LOADED = False


def register_adapter(provider: TrackerProvider, *, replace: bool = False) -> None:
    pid = getattr(provider, "id", None)
    if not pid or not isinstance(pid, str):
        raise ValueError("Adapter.id must be a non-empty string")
    if pid in _ADAPTERS and not replace:
        raise ValueError(f"Integration adapter already registered: {pid}")
    _ADAPTERS[pid] = provider


def get_adapter(provider_id: str) -> TrackerProvider:
    _ensure_builtins()
    try:
        return _ADAPTERS[provider_id]
    except KeyError as exc:
        raise KeyError(f"Unknown integration adapter: {provider_id}") from exc


def list_adapters() -> list[TrackerProvider]:
    _ensure_builtins()
    return [_ADAPTERS[k] for k in sorted(_ADAPTERS.keys())]


def resolve_provider(provider_id: str) -> TrackerProvider:
    """Tracker registry first, then docs/chat/sheets adapters."""
    try:
        return get_tracker_provider(provider_id)
    except KeyError:
        return get_adapter(provider_id)


def adapter_public_dict(provider: TrackerProvider) -> dict[str, Any]:
    return provider_public_dict(provider)


def _ensure_builtins() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    from app.integrations.notion import NotionProvider

    for cls in (NotionProvider,):
        inst = cls()
        if inst.id not in _ADAPTERS:
            _ADAPTERS[inst.id] = inst
    _BUILTINS_LOADED = True
