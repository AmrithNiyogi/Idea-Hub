"""Pluggable third-party tracker integrations (ClickUp, Jira, custom, …).

Register new providers in ``app.trackers.registry`` — see
``docs/TRACKER_PROVIDERS.md``.
"""

from __future__ import annotations

from app.trackers.registry import get_provider, list_providers, register_provider

__all__ = ["get_provider", "list_providers", "register_provider"]
