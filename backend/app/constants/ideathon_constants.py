"""Ideathon campaign phases and scoring weights from idea-hub.html."""

from __future__ import annotations

ITH_PHASES: tuple[dict[str, str], ...] = (
    {"id": "open", "label": "Open", "blurb": "Submissions are open"},
    {
        "id": "shortlist",
        "label": "Shortlist",
        "blurb": "Agent proposes, organiser approves",
    },
    {
        "id": "pitch",
        "label": "Pitch day",
        "blurb": "Pitches, panel scores and audience votes",
    },
    {
        "id": "results",
        "label": "Results",
        "blurb": "Ranking proposed, winners confirmed",
    },
    {
        "id": "handoff",
        "label": "Handoff",
        "blurb": "Problem statements go to the hackathon backlog",
    },
)

PHASE_ORDER: tuple[str, ...] = tuple(p["id"] for p in ITH_PHASES)

IT_NEXT: dict[str, str] = {
    "open": "shortlist",
    "shortlist": "pitch",
    "pitch": "results",
    "results": "handoff",
}

DEFAULT_PANEL_WEIGHT: int = 70
DEFAULT_AUDIENCE_WEIGHT: int = 30
DEFAULT_SHORTLIST_SIZE: int = 4
MIN_SHORTLIST: int = 2
MAX_SHORTLIST: int = 6
MAX_WINNERS: int = 2
PITCH_SCORE_MIN: int = 1
PITCH_SCORE_MAX: int = 10
MIN_HANDOFF_STATEMENT_LEN: int = 80

# Idea statuses that may still join an open ideathon (HTML SEL.ithLinkable).
LINKABLE_IDEA_STATUSES: frozenset[str] = frozenset(
    {
        "submitted",
        "under_review",
        "needs_info",
        "accepted",
        "parked",
        "prototype",
    }
)

ORG_ROLES: frozenset[str] = frozenset({"leadership", "admin"})
PANEL_SCORE_ROLES: frozenset[str] = frozenset(
    {"reviewer", "leadership", "admin"}
)
