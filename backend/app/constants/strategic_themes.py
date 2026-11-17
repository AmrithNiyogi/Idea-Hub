"""Strategic theme vocabulary for Insights theme analysis."""

from __future__ import annotations

STRATEGIC_THEMES: list[dict[str, object]] = [
    {
        "id": "reliability",
        "label": "Reliability & quality",
        "words": ["flaky", "test", "regression", "incident", "sla", "uptime", "error"],
    },
    {
        "id": "cost",
        "label": "Cost & efficiency",
        "words": ["cost", "spend", "hours", "waste", "duplicate", "cache", "embed"],
    },
    {
        "id": "observability",
        "label": "Observability",
        "words": ["trace", "log", "metric", "alert", "dashboard", "monitor"],
    },
    {
        "id": "onboarding",
        "label": "Onboarding & docs",
        "words": ["onboard", "docs", "runbook", "handbook", "new joiner", "template"],
    },
    {
        "id": "agents",
        "label": "Agent adoption",
        "words": ["agent", "assistant", "workflow", "kompass", "prompt", "llm"],
    },
    {
        "id": "customer",
        "label": "Customer experience",
        "words": ["customer", "support", "ticket", "nps", "churn", "health"],
    },
    {
        "id": "process",
        "label": "Process & approvals",
        "words": ["approval", "meeting", "handoff", "checklist", "release", "review"],
    },
]
