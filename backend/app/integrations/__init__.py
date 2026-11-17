"""Broader Integrations surface (trackers today; docs/chat/sheets later).

Tracker providers remain in ``app.trackers``. This package adds categories,
coming-soon stubs, and a unified catalog for the Integrations settings UI.
See ``docs/INTEGRATIONS.md``.
"""

from __future__ import annotations

from app.integrations.registry import (
    get_integration,
    list_integrations,
    register_integration,
)

__all__ = ["get_integration", "list_integrations", "register_integration"]
