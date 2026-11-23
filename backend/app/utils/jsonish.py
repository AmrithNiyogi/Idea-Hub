"""Helpers for narrowing untyped JSON payloads from third-party APIs."""

from __future__ import annotations

from typing import Any


def as_dict(value: object) -> dict[str, Any]:
    """Return ``value`` when it is a JSON object, otherwise an empty dict.

    Args:
        value: Any value taken from a decoded JSON payload.

    Returns:
        The same dict, or ``{}`` when the value is missing or not an object.
    """
    return value if isinstance(value, dict) else {}
