"""Statuses where external tracker create/link is allowed."""

from __future__ import annotations

# Accepted = ready for development; prototype/implemented = delivery underway.
TRACKER_LINKABLE_STATUSES: frozenset[str] = frozenset(
    {"accepted", "prototype", "implemented"}
)

# Create remote tasks only while work is still open (not after ship).
TRACKER_CREATABLE_STATUSES: frozenset[str] = frozenset(
    {"accepted", "prototype"}
)
