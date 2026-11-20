"""Simulated agent roster aligned with KOMPASS_AGENT_PROMPTS.md.

Every agent is Simulated in MVP. Agents propose; humans decide.
The orchestrator is a deterministic rules engine, not an LLM agent.
"""

from __future__ import annotations

from typing import Any

AGENT_ROSTER: list[dict[str, Any]] = [
    {
        "id": "idea-intelligence",
        "prompt_slug": "ideakonnekt-idea-intelligence",
        "form": "Smart Agent (planned)",
        "purpose": (
            "Classify drafts, suggest tags, find similar ideas, and flag "
            "missing fields. Proposes; the author decides."
        ),
        "triggers": ["idea.draft_changed", "idea.submitted"],
        "approval_default": "author",
        "never": [
            "Choose the final category or tags for the author",
            "Merge, reject, or join ideas",
            "Reveal anonymous authors",
        ],
    },
    {
        "id": "idea-enhancement",
        "prompt_slug": "ideakonnekt-idea-enhancement",
        "form": "Smart Agent (planned)",
        "purpose": (
            "Suggest rewrites, beneficiaries, and metrics. Applied only when "
            "the author accepts each suggestion."
        ),
        "triggers": ["enhancement.requested", "idea.submitted"],
        "approval_default": "author",
        "never": [
            "Overwrite author text silently",
            "Invent facts not in the draft",
        ],
    },
    {
        "id": "idea-optimizer",
        "prompt_slug": "ideakonnekt-wf-idea-optimizer",
        "form": "Chat co-pilot (simulated)",
        "purpose": (
            "After submit, help the author improve clarity, metrics, tags, and "
            "problem framing via chat. Proposes field_patches; human applies. "
            "Not the reviewer scoring agent."
        ),
        "triggers": ["idea.optimize_requested", "idea.submitted"],
        "approval_default": "author",
        "never": [
            "Persist edits without author Apply",
            "Score or decide like Review Intelligence",
            "Invent customers, metrics, or facts not grounded in the idea",
        ],
    },
    {
        "id": "review-intelligence",
        "prompt_slug": "ideakonnekt-wf-review-intelligence",
        "form": "Smart Agent (planned)",
        "purpose": (
            "Prepare a reviewer brief with risks, discussion themes, suggested "
            "scores, decision lean, and merge target_id when similar ideas "
            "warrant merge. Never records a decision."
        ),
        "triggers": [
            "idea.review_started",
            "comment.added",
            "idea.assigned_to_panel",
        ],
        "approval_default": "reviewer",
        "never": [
            "Write the decision of record",
            "Write scores of record",
            "Accept, park, merge, or decline an idea",
        ],
    },
    {
        "id": "coding-agent-build",
        "prompt_slug": "ideakonnekt-wf-coding-agent-build",
        "form": "Smart Agent (Kompass execute or simulated)",
        "purpose": (
            "For accepted ideas: generate the agent-context / skill pack, "
            "kick a Kompass-shaped coding build (or persist a simulated "
            "timeline), and open a human gate before Prototype. Never flips "
            "status without an explicit proposal approve."
        ),
        "triggers": ["idea.agent_build_requested"],
        "approval_default": "owner",
        "never": [
            "Move the idea to Prototype without human approval",
            "Grant innovation hours or write delivery tasks of record",
            "Overwrite idea fields or de-anonymise authors",
        ],
    },
    {
        "id": "innovation-workflow",
        "prompt_slug": "ideakonnekt-innovation-workflow",
        "form": "Smart Agent (planned)",
        "purpose": (
            "Detect stuck ideas, draft reminders, and propose reopen when "
            "conditions are met."
        ),
        "triggers": [
            "review.overdue",
            "prototype.stale",
            "reopen.ready",
            "parked.revisit",
            "decision.recorded",
            "idea.implemented",
        ],
        "approval_default": "reviewer",
        "never": [
            "Send a reminder without human approval for escalations",
            "Change status or reopen without reviewer approval",
            "Escalate to leadership on its own",
        ],
    },
    {
        "id": "recognition",
        "prompt_slug": "ideakonnekt-recognition",
        "form": "Smart Agent (planned)",
        "purpose": (
            "Explain points under published rules, draft award nominations, "
            "and flag reciprocal-vote pairs."
        ),
        "triggers": [
            "idea.decision_recorded",
            "idea.implemented",
            "impact.measured",
            "quarter.closed",
        ],
        "approval_default": "leadership",
        "never": [
            "Override points without admin reason",
            "Confirm awards without leadership",
        ],
    },
    {
        "id": "innovation-analytics",
        "prompt_slug": "ideakonnekt-innovation-analytics",
        "form": "Smart Agent (planned)",
        "purpose": (
            "Narrate participation, funnel, bottlenecks, and impact with "
            "evidence idea ids. Read-only."
        ),
        "triggers": ["analytics.requested", "summary.generated"],
        "approval_default": "none",
        "never": [
            "Change configuration",
            "Invent metrics not present in the snapshot",
        ],
    },
    {
        "id": "orchestrator",
        "prompt_slug": None,
        "form": "Deterministic rules engine",
        "purpose": (
            "Routes events, writes run records, and is the seam where a "
            "Kompass adapter plugs in later."
        ),
        "triggers": ["*"],
        "approval_default": "none",
        "never": [
            "Use a language model",
            "Make a judgement call",
            "Skip a human approval gate",
        ],
    },
]

AGENT_BY_ID = {a["id"]: a for a in AGENT_ROSTER}

# Kompass integration map open questions (admin can mark answered).
KOMPASS_OPEN_QUESTIONS: list[dict[str, str]] = [
    {
        "id": "q1",
        "text": (
            "Hub → Kompass invoke: POST /api/v2/runs/execute with X-Tenant-ID, "
            "project-slug, optional X-Authorization; body agent_id + input + "
            "conversation_id (see AGENT_SIMULATION.md). Confirm staging project-slug "
            "and agent ids in AISTUDIO_* env."
        ),
    },
    {"id": "q2", "text": "Does Kompass support pause-and-resume / human approval nodes?"},
    {"id": "q3", "text": "Structured output / JSON schema enforcement available?"},
    {"id": "q4", "text": "Webhook or callback for run completion?"},
    {"id": "q5", "text": "Human approval: is there any approval or pause-and-resume primitive?"},
    {"id": "q6", "text": "Which LLM models are available in the tenant catalog?"},
    {"id": "q7", "text": "Tool auth: how do custom tools authenticate to Idea Hub?"},
    {"id": "q8", "text": "Multi-tenant isolation for agent runs?"},
    {"id": "q9", "text": "Rate limits / cost budgets per agent?"},
    {"id": "q10", "text": "Prompt versioning / inherit semantics confirmed?"},
    {"id": "q11", "text": "Can teams run sequentially with shared state?"},
]
