"""Default admin configuration values (timelines, scoring, recognition overrides).

These are the Phase 4 starting values. Admins may override via platform_settings;
changes to point values apply to *future* ledger rows only.
"""

from __future__ import annotations

from typing import Any

DEFAULT_TIMELINES: dict[str, int] = {
    "pickup_days": 3,
    "decision_days": 10,
    "stale_prototype_days": 14,
    "needs_info_days": 10,
    "owner_assign_days": 5,
}

DEFAULT_SCORING: list[dict[str, Any]] = [
    {
        "key": "impact",
        "label": "Impact",
        "low": "Minor, few people",
        "high": "Transformative, many people",
        "weight": 40,
    },
    {
        "key": "effort",
        "label": "Effort",
        "low": "Very small",
        "high": "Very large",
        "weight": 20,
    },
    {
        "key": "alignment",
        "label": "Strategic alignment",
        "low": "Not aligned",
        "high": "Directly supports a theme",
        "weight": 40,
    },
]

# Thin editable overlay over recognition_rules.REC_RULES point amounts.
DEFAULT_POINT_OVERRIDES: dict[str, int] = {
    "submit": 5,
    "accepted": 30,
    "prototype": 40,
    "implemented": 100,
    "dedupe": 10,
    "helpful": 3,
    "volunteer": 20,
    "review_ontime": 8,
    "pitch_finalist": 15,
    "pitch_winner": 60,
    "ioq": 150,
}

SETTING_KEYS = (
    "timelines",
    "scoring",
    "point_overrides",
    "pool",
)

DEFAULT_POOL: dict[str, Any] = {
    "quarterly_hours": 450,
    "label": "Innovation time pool",
}
