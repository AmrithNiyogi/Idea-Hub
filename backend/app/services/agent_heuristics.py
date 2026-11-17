"""Deterministic simulated agent heuristics (Phase 5).

No network, no LLM. Every result is labelled Simulated by the gateway.
Heuristics approximate Idea Intelligence, Enhancement, Review brief,
stuck detection, and analytics narration.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from app.models.idea import Idea

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "is",
    "are",
    "we",
    "our",
    "that",
    "this",
    "it",
    "as",
    "by",
    "from",
    "be",
    "at",
    "have",
    "has",
}


def _words(text: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(w) > 2 and w not in _STOP
    ]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similar_ideas(
    draft: Idea | dict[str, Any],
    corpus: Sequence[Idea],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Rank corpus ideas by tag + problem-word Jaccard similarity."""
    if isinstance(draft, dict):
        title = str(draft.get("title") or "")
        problem = str(draft.get("problem") or "")
        tags = set(str(t) for t in (draft.get("tags") or []))
        draft_id = draft.get("id")
    else:
        title = draft.title
        problem = draft.problem
        tags = set(str(t) for t in (draft.tags or []))
        draft_id = draft.id

    base = set(_words(f"{title} {problem}")) | tags
    scored: list[tuple[float, Idea]] = []
    for idea in corpus:
        if draft_id and idea.id == draft_id:
            continue
        if idea.status in ("draft", "withdrawn"):
            continue
        other = set(_words(f"{idea.title} {idea.problem}")) | set(
            str(t) for t in (idea.tags or [])
        )
        sim = _jaccard(base, other)
        if sim >= 0.12:
            scored.append((sim, idea))
    scored.sort(key=lambda x: -x[0])
    out = []
    for sim, idea in scored[:limit]:
        shared = sorted(
            (
                set(_words(f"{title} {problem}"))
                | tags
            )
            & (
                set(_words(f"{idea.title} {idea.problem}"))
                | set(str(t) for t in (idea.tags or []))
            )
        )[:6]
        out.append(
            {
                "idea_id": str(idea.id),
                "title": idea.title,
                "status": idea.status,
                "similarity": round(sim, 3),
                "shared_terms": shared,
                "can_join": idea.status
                not in ("declined", "merged", "withdrawn", "implemented"),
            }
        )
    return out


def completeness(draft: Idea | dict[str, Any]) -> list[dict[str, str]]:
    fields = {
        "title": "Add a clear title",
        "problem": "Describe who feels the pain and how often",
        "solution": "Say what would change",
        "beneficiaries": "Name who benefits",
        "success_metrics": "Add a measurable success metric",
    }
    missing = []
    for key, reason in fields.items():
        if isinstance(draft, dict):
            val = draft.get(key) or draft.get(
                "success" if key == "success_metrics" else key
            )
        else:
            val = getattr(draft, key, "")
        if not str(val or "").strip() or len(str(val).strip()) < 12:
            missing.append({"field": key, "reason": reason})
    return missing


def idea_intelligence(
    draft: Idea | dict[str, Any],
    corpus: Sequence[Idea],
    categories: Sequence[Any],
) -> dict[str, Any]:
    similar = similar_ideas(draft, corpus)
    missing = completeness(draft)
    text = ""
    tags: list[str] = []
    if isinstance(draft, dict):
        text = f"{draft.get('title','')} {draft.get('problem','')} {draft.get('solution','')}"
        tags = list(draft.get("tags") or [])
        cat_hint = draft.get("category_slug") or draft.get("category_id")
    else:
        text = f"{draft.title} {draft.problem} {draft.solution}"
        tags = list(draft.tags or [])
        cat_hint = draft.category_id

    suggested_cat = None
    best = 0.0
    for c in categories:
        label = getattr(c, "label", "") or getattr(c, "slug", "")
        blob = f"{label} {getattr(c, 'description', '')}".lower()
        score = _jaccard(set(_words(text)), set(_words(blob)))
        if score > best:
            best = score
            suggested_cat = {
                "value": getattr(c, "slug", str(getattr(c, "id", ""))),
                "confidence": round(min(0.95, best + 0.2), 2),
                "evidence": _words(text)[:5],
            }

    dup = "low"
    if similar and similar[0]["similarity"] >= 0.45:
        dup = "high"
    elif similar and similar[0]["similarity"] >= 0.25:
        dup = "medium"

    tag_suggestions = []
    for t, n in Counter(_words(text)).most_common(8):
        if t not in tags:
            tag_suggestions.append(
                {"tag": t, "score": round(0.4 + min(0.5, n * 0.1), 2), "evidence_terms": [t]}
            )
        if len(tag_suggestions) >= 5:
            break

    return {
        "suggested_category": suggested_cat,
        "suggested_tags": tag_suggestions,
        "similar_ideas": similar,
        "missing_fields": missing,
        "duplicate_risk": dup,
        "category_hint": str(cat_hint) if cat_hint else None,
        "simulated": True,
    }


def enhancement(draft: Idea | dict[str, Any]) -> dict[str, Any]:
    problem = (
        draft.get("problem")
        if isinstance(draft, dict)
        else draft.problem
    ) or ""
    suggestions = []
    if len(problem) < 80:
        suggestions.append(
            {
                "kind": "problem_expand",
                "text": (
                    problem.rstrip(".")
                    + ". Quantify how often this happens and who feels it today."
                ),
                "rationale": "Short problem statements are hard to score for impact.",
            }
        )
    suggestions.append(
        {
            "kind": "metric",
            "text": "Median time from request to done (days)",
            "rationale": "Cycle-time metrics travel well across categories.",
        }
    )
    return {
        "suggestions": suggestions,
        "suggested_beneficiaries": ["Teams who run this weekly", "New joiners"],
        "suggested_metrics": [
            {
                "metric": "Hours per week spent on the task today",
                "unit": "hours/week",
                "baseline_prompt": "What is the current weekly effort?",
            }
        ],
        "impact_estimate": {
            "band": "M",
            "assumptions": ["Assumes one team adopts first"],
        },
        "simulated": True,
    }


def review_brief(
    idea: Idea,
    comments: Sequence[Any],
    votes: int,
    similar: list[dict[str, Any]],
) -> dict[str, Any]:
    pros, concerns, questions = [], [], []
    for c in comments[:12]:
        body = getattr(c, "body", None) or getattr(c, "text", "") or ""
        low = body.lower()
        if any(w in low for w in ("risk", "concern", "worry", "block")):
            concerns.append(body[:160])
        elif "?" in body:
            questions.append(body[:160])
        else:
            pros.append(body[:160])
    risks = [{"risk": c, "source": "discussion"} for c in concerns[:3]]
    if not idea.success_metrics or len(idea.success_metrics) < 10:
        risks.append(
            {
                "risk": "Success metrics are thin — hard to verify impact later",
                "source": "template",
            }
        )
    lean = "accept"
    if similar and similar[0].get("similarity", 0) >= 0.4:
        lean = "merge"
    elif len(concerns) >= 3:
        lean = "needs_info"

    return {
        "summary": (
            f"“{idea.title}” ({idea.status}). {votes} upvote(s), "
            f"{len(comments)} comment(s). "
            f"{len(similar)} similar idea(s) in the corpus."
        ),
        "discussion_summary": {
            "pros": pros[:4],
            "concerns": concerns[:4],
            "open_questions": questions[:4],
        },
        "risks": risks,
        "dependencies": [],
        "suggested_scores": {
            "impact": {"value": 3, "confidence": 0.4, "evidence": ["Heuristic default"]},
            "effort": {"value": 3, "confidence": 0.35, "evidence": [f"Effort field: {idea.effort}"]},
            "alignment": {
                "value": 3,
                "confidence": 0.35,
                "evidence": ["Category routing"],
            },
        },
        "decision_lean": {
            "option": lean,
            "rationale": "Heuristic lean only — reviewer must decide.",
            "caveats": ["Simulated; anchoring mitigation applies"],
        },
        "integrity_flags": [],
        "simulated": True,
    }


def stuck_detection(
    ideas: Sequence[Idea],
    *,
    decision_days: int = 10,
    stale_prototype_days: int = 14,
    owner_assign_days: int = 5,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    out = []
    for i in ideas:
        if i.status == "under_review" and i.due_at and i.due_at < now:
            days = max(1, int((now - i.due_at).total_seconds() / 86400))
            out.append(
                {
                    "idea_id": str(i.id),
                    "title": i.title,
                    "condition": "review.overdue",
                    "days_in_stage": days,
                    "sla_days": decision_days,
                    "recommended_action": "remind_reviewers",
                    "draft_message": (
                        f"Reminder: “{i.title}” is {days} day(s) past its "
                        f"decision SLA."
                    ),
                }
            )
        if (
            i.status == "accepted"
            and not i.owner_id
            and i.stage_entered_at
            and (now - i.stage_entered_at).days >= owner_assign_days
        ):
            out.append(
                {
                    "idea_id": str(i.id),
                    "title": i.title,
                    "condition": "owner.missing",
                    "days_in_stage": (now - i.stage_entered_at).days,
                    "sla_days": owner_assign_days,
                    "recommended_action": "remind_owner",
                    "draft_message": (
                        f"“{i.title}” is accepted without an owner for "
                        f"{(now - i.stage_entered_at).days} days."
                    ),
                }
            )
        if (
            i.status == "prototype"
            and i.stage_entered_at
            and (now - i.stage_entered_at).days >= stale_prototype_days
        ):
            out.append(
                {
                    "idea_id": str(i.id),
                    "title": i.title,
                    "condition": "prototype.stale",
                    "days_in_stage": (now - i.stage_entered_at).days,
                    "sla_days": stale_prototype_days,
                    "recommended_action": "remind_owner",
                    "draft_message": (
                        f"“{i.title}” has had no progress signal for "
                        f"{(now - i.stage_entered_at).days} days."
                    ),
                }
            )
        if i.status == "parked" and i.revisit_at and i.revisit_at <= now:
            out.append(
                {
                    "idea_id": str(i.id),
                    "title": i.title,
                    "condition": "parked.revisit",
                    "days_in_stage": 0,
                    "sla_days": 0,
                    "recommended_action": "revisit_parked",
                    "draft_message": (
                        f"Revisit date reached for “{i.title}”. Propose return to review."
                    ),
                }
            )
    return out


def analytics_narrative(snapshot: dict[str, Any]) -> dict[str, Any]:
    cards = snapshot.get("cards") or []
    statements = [c.get("text") if isinstance(c, dict) else str(c) for c in cards[:5]]
    return {
        "period": snapshot.get("days"),
        "insights": [
            {
                "id": f"sim-{i}",
                "type": "narrative",
                "statement": s,
                "evidence_idea_ids": [],
            }
            for i, s in enumerate(statements)
            if s
        ],
        "recommended_actions": [
            "Open Insights for evidence tables",
            "Clear overdue review queue if bottleneck card is present",
        ],
        "simulated": True,
    }
