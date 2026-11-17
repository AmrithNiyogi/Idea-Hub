"""Broader Integrations surface (trackers + Notion docs; Sheets/Teams stubs).

Tracker providers remain in ``app.trackers``. Docs adapters live in
``app.integrations.adapters`` (Notion today). See ``docs/INTEGRATIONS.md``.
"""

from __future__ import annotations

from app.integrations.registry import (
    get_integration,
    list_integrations,
    register_integration,
)

__all__ = ["get_integration", "list_integrations", "register_integration"]
