"""Stable notification kind strings and email gating.

Kinds that email (high signal):
- decision, needs_info, collab, hours, routed, overdue, owner

Kinds that stay in-app only (low noise):
- pickup, status, answered, comment, impact, implemented, nudge, coauthor
  (coauthor still in-app; owner/assignment emails use ``owner``)

Followers of an idea subscribe to idea-scoped kinds via the follow table.
Mandatory roles (author / owner / assignee / requester) always receive
regardless of follow state.
"""

from __future__ import annotations

# High-signal kinds that also trigger SMTP when NOTIFY_EMAIL_ENABLED.
EMAIL_KINDS: frozenset[str] = frozenset(
    {
        "decision",
        "needs_info",
        "collab",
        "hours",
        "routed",
        "overdue",
        "owner",
    }
)

# Human labels for email subjects.
KIND_LABELS: dict[str, str] = {
    "decision": "Review decision",
    "needs_info": "More information needed",
    "collab": "Collaboration update",
    "hours": "Innovation hours",
    "routed": "New idea in your review queue",
    "overdue": "Review overdue",
    "owner": "Ownership assigned",
    "pickup": "Review started",
    "status": "Status update",
    "answered": "Author answered",
    "comment": "New comment",
    "impact": "Impact update",
    "implemented": "Idea implemented",
    "nudge": "Delivery nudge",
    "coauthor": "Co-author update",
}
