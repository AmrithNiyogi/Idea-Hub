"""Delivery-domain constants lifted from idea-hub.html Phase 4 behaviour."""

from __future__ import annotations

CONTRIB_ROLES: tuple[str, ...] = (
    "Builder",
    "Reviewer",
    "Tester",
    "Designer",
    "Advisor",
)

IMPACT_TYPES: dict[str, dict[str, str]] = {
    "hours_saved": {
        "label": "Hours saved per month",
        "unit": "hours per month",
    },
    "revenue": {
        "label": "Revenue influenced per month",
        "unit": "USD per month",
    },
    "cost_avoided": {
        "label": "Cost avoided per month",
        "unit": "USD per month",
    },
    "other": {
        "label": "Other measured impact",
        "unit": "",
    },
}

IMPACT_CONFIDENCE: tuple[str, ...] = ("low", "medium", "high")

TASK_STATUSES: tuple[str, ...] = (
    "not_started",
    "in_progress",
    "blocked",
    "done",
)

HOUR_REQUEST_STATES: tuple[str, ...] = ("pending", "approved", "declined")

# Quarterly innovation-time pool (hours). Proposal from product docs.
DEFAULT_QUARTER_POOL_HOURS: int = 400

MIN_HOURS_REQUEST: int = 1
MAX_HOURS_REQUEST: int = 400
MAX_HOURS_LOG_ENTRY: float = 80.0
HOURS_LOG_STEP: float = 0.25
MIN_JUSTIFICATION_LEN: int = 10
MIN_VERIFY_NOTE_LEN: int = 10
MIN_OUTCOME_LEN: int = 20
