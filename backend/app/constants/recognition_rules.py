"""Recognition points rules, levels, and badges (product §7 / HTML REC_DEFAULTS).

All point values are PROPOSALS from discovery — not contractual Dotkonnekt facts.
"""

from __future__ import annotations

from typing import Any

REC_DIMS: dict[str, str] = {
    "quality": "Quality",
    "collab": "Collaboration",
    "delivery": "Delivery",
    "impact": "Impact",
}

REC_RULES: dict[str, dict[str, Any]] = {
    "submit": {
        "label": "Submit a complete idea",
        "points": 5,
        "dim": "quality",
        "cap_per_month": 3,
        "when": (
            "Idea submitted and the template check passes. "
            "At most 3 awards a month."
        ),
    },
    "accepted": {
        "label": "Idea reaches Accepted",
        "points": 30,
        "dim": "quality",
        "when": "Author and co-authors share the points equally.",
    },
    "prototype": {
        "label": "Idea reaches Prototype",
        "points": 40,
        "dim": "delivery",
        "when": "Owner and current contributors share the points.",
    },
    "implemented": {
        "label": "Idea Implemented",
        "points": 100,
        "dim": "delivery",
        "when": "Split by contribution shares agreed at mark-implemented.",
    },
    "impact_verified": {
        "label": "Verified impact bonus",
        "points": 25,
        "max_points": 150,
        "dim": "impact",
        "when": (
            "Second-person verification. Points = confidence base "
            "(low 25 / medium 40 / high 60) × size band (1 / 1.5 / 2), "
            "clamped 25–150, split by contribution share."
        ),
    },
    "dedupe": {
        "label": "Join or merge instead of duplicating",
        "points": 10,
        "dim": "collab",
        "when": "Join as co-author or merge into another idea.",
    },
    "helpful": {
        "label": "Comment marked helpful",
        "points": 3,
        "dim": "collab",
        "max_per_idea": 5,
        "when": "Author marks a non-author comment helpful. Max 5 per idea.",
    },
    "volunteer": {
        "label": "Volunteer contribution delivered",
        "points": 20,
        "dim": "collab",
        "when": "Help request accepted and idea reached Implemented.",
    },
    "ontime_review": {
        "label": "Reviewer decision on time",
        "points": 8,
        "dim": "quality",
        "when": "Decision with written reason on or before due date.",
    },
    "pitch_finalist": {
        "label": "Pitch day finalist",
        "points": 15,
        "dim": "quality",
        "when": "Shortlisted and pitched; results confirmed. Authors share.",
    },
    "pitch_winner": {
        "label": "Pitch day winner",
        "points": 60,
        "dim": "quality",
        "when": "Confirmed winner. Replaces finalist points. Authors share.",
    },
    "ioq": {
        "label": "Idea of the Quarter",
        "points": 150,
        "dim": "impact",
        "when": "Leadership confirms after nominations. Authors share.",
    },
    "annual_award": {
        "label": "Annual Innovation Award",
        "points": 300,
        "dim": "impact",
        "when": "Leadership confirms a person from the year’s shortlist.",
    },
}

REC_RULES["thanks"] = {
    "label": "A teammate says thank you",
    "points": 4,
    "dim": "collab",
    "when": "A teammate writes what they valued in your work. Each person can send 3 a month, and only one to the same teammate.",
}

THANKS_PER_GIVER_MONTH: int = 3
THANKS_MIN_LEN: int = 20
THANKS_MAX_LEN: int = 280

LEVELS: tuple[dict[str, Any], ...] = (
    {"id": "spark", "name": "Spark", "min": 0},
    {"id": "contributor", "name": "Contributor", "min": 50},
    {"id": "builder", "name": "Builder", "min": 200},
    {"id": "catalyst", "name": "Catalyst", "min": 500},
    {"id": "pioneer", "name": "Pioneer", "min": 1000},
)

IMPACT_BASE: dict[str, int] = {"low": 25, "medium": 40, "high": 60}

BADGE_DEFS: tuple[dict[str, str], ...] = (
    {
        "id": "first_reply",
        "name": "First Reply",
        "icon": "message",
        "rule": "An idea you wrote received its first reviewer decision.",
    },
    {
        "id": "team_player",
        "name": "Team Player",
        "icon": "users",
        "rule": "Author or co-author on 3 multi-author ideas.",
    },
    {
        "id": "deduplicator",
        "name": "Deduplicator",
        "icon": "merge",
        "rule": "Joined or merged into an existing idea instead of duplicating.",
    },
    {
        "id": "builder",
        "name": "Builder",
        "icon": "hand",
        "rule": "A volunteer contribution of yours was delivered.",
    },
    {
        "id": "closer",
        "name": "Closer",
        "icon": "checkcircle",
        "rule": "You hold credit on an idea that reached Implemented.",
    },
    {
        "id": "impact_100",
        "name": "Impact 100",
        "icon": "chart",
        "rule": "Credited on ideas with 100+ verified hours saved / month.",
    },
    {
        "id": "sharp_reviewer",
        "name": "Sharp Reviewer",
        "icon": "shield",
        "rule": "10 reviewer decisions recorded on time.",
    },
    {
        "id": "pitch_winner",
        "name": "Pitch Winner",
        "icon": "trophy",
        "rule": "An idea you wrote won an ideathon.",
    },
    {
        "id": "comeback",
        "name": "Comeback",
        "icon": "refresh",
        "rule": "Idea accepted after parked, declined+reopened, or needs_info.",
    },
    {
        "id": "quarter_champion",
        "name": "Quarter Champion",
        "icon": "award",
        "rule": "An idea you wrote was named Idea of the Quarter.",
    },
)


def level_for_points(points: int) -> dict[str, Any]:
    """Return the highest level whose ``min`` threshold is <= ``points``."""
    current = LEVELS[0]
    for level in LEVELS:
        if points >= int(level["min"]):
            current = level
    return current


def impact_bonus_points(
    *,
    impact_type: str,
    value: float,
    confidence: str,
) -> int:
    """Compute verified-impact bonus (HTML RECOG.impactPoints).

    Args:
        impact_type: One of hours_saved / revenue / cost_avoided / other.
        value: Reported impact magnitude.
        confidence: low | medium | high.

    Returns:
        Integer points clamped to [25, 150].
    """
    rule = REC_RULES["impact_verified"]
    base = IMPACT_BASE.get(confidence, IMPACT_BASE["low"])
    v = float(value or 0)
    if impact_type == "hours_saved":
        band = 2.0 if v >= 60 else 1.5 if v >= 20 else 1.0
    elif impact_type in {"cost_avoided", "revenue"}:
        band = 2.0 if v >= 8000 else 1.5 if v >= 2000 else 1.0
    else:
        band = 1.0
    raw = round(base * band)
    lo = int(rule["points"])
    hi = int(rule.get("max_points", 150))
    return max(lo, min(hi, raw))
