"""Idea lifecycle constants lifted from the HTML prototype.

Transitions are enforced in services; status labels are for API responses.
"""

from __future__ import annotations

STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "submitted": "Submitted",
    "under_review": "Under review",
    "needs_info": "Needs info",
    "accepted": "Accepted",
    "parked": "Parked",
    "merged": "Merged",
    "declined": "Declined",
    "prototype": "Prototype",
    "implemented": "Implemented",
    "withdrawn": "Withdrawn",
}

DECISION_STATUSES: frozenset[str] = frozenset(
    {"accepted", "parked", "merged", "declined"}
)

TRANSITIONS: dict[str, list[str]] = {
    "draft": ["submitted"],
    "submitted": ["under_review", "withdrawn"],
    "under_review": [
        "needs_info",
        "accepted",
        "parked",
        "merged",
        "declined",
        "withdrawn",
    ],
    "needs_info": ["under_review", "withdrawn"],
    "accepted": ["prototype", "declined"],
    "parked": ["under_review"],
    "prototype": ["implemented", "parked", "declined"],
    "merged": [],
    "declined": [],
    "implemented": [],
    "withdrawn": [],
}

ROLE_ORDER: list[str] = [
    "contributor",
    "reviewer",
    "lead",
    "leadership",
    "admin",
]

VALID_ROLES: frozenset[str] = frozenset(ROLE_ORDER)

EFFORTS: dict[str, str] = {
    "S": "Small (days)",
    "M": "Medium (weeks)",
    "L": "Large (a quarter)",
    "XL": "Extra large (multi-quarter)",
}

DECISION_OUTCOME_MAP: dict[str, str] = {
    "accept": "accepted",
    "park": "parked",
    "merge": "merged",
    "decline": "declined",
    "info": "needs_info",
}

WITHDRAWABLE_STATUSES: frozenset[str] = frozenset(
    {"submitted", "under_review", "needs_info"}
)

LIVE_STATUSES: frozenset[str] = frozenset(
    {
        "submitted",
        "under_review",
        "needs_info",
        "accepted",
        "parked",
        "prototype",
        "implemented",
    }
)


def can_transition(from_status: str, to_status: str) -> bool:
    """Return True when ``to_status`` is a legal next state from ``from_status``."""
    return to_status in TRANSITIONS.get(from_status, [])
