"""AI review of a submitted idea: DotKonnekt fit plus suggestions, saved on the idea for the reviewer.

Responsibilities:
- Read the company context (admin setting ``company_context``, else the strategic themes in code).
- Build the review: fit band, matched themes, optional angles, field suggestions, metric scaffolds.
- Use the Kompass Idea Enhancement workflow when configured; otherwise the local rules (``simulated``).
- Run after submit in the background and save to ``ideas.ai_review``.

Side Effects:
- Optional outbound Kompass call. Writes ``ideas.ai_review`` only. Never edits the idea's own fields.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.entry_scoring import (
    AI_REVIEW_ENGINE_LOCAL,
    AI_REVIEW_FIELD_HINTS,
    COMPANY_CONTEXT_SETTING_KEY,
    FIT_PARTIAL_MIN_THEMES,
    FIT_STRONG_MIN_THEMES,
    MIN_FIELD_CHARS,
)
from app.constants.strategic_themes import STRATEGIC_THEMES
from app.db.session import AsyncSessionLocal
from app.models.admin import PlatformSetting
from app.models.idea import Idea
from app.services import agent_heuristics as heuristics
from app.services import idea_enhancement_flow

logger = logging.getLogger(__name__)

def idea_fields(idea: Idea) -> dict[str, Any]:
    """The idea's own text, as the review reads it."""
    return {
        "id": str(idea.id),
        "title": idea.title or "",
        "problem": idea.problem or "",
        "solution": idea.solution or "",
        "beneficiaries": idea.beneficiaries or "",
        "success_metrics": idea.success_metrics or "",
        "tags": [str(t) for t in (idea.tags or [])],
    }


async def company_themes(session: AsyncSession) -> list[dict[str, Any]]:
    """Company priorities from the admin setting, falling back to the strategic themes in code."""
    row = await session.get(PlatformSetting, COMPANY_CONTEXT_SETTING_KEY)
    themes = row.value.get("themes") if row and isinstance(row.value, dict) else None
    if isinstance(themes, list) and themes:
        return [t for t in themes if isinstance(t, dict) and t.get("label")]
    return [dict(t) for t in STRATEGIC_THEMES]


def match_themes(fields: dict[str, Any], themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Themes whose words appear in the idea, with the words that matched."""
    text = " ".join(
        [str(fields.get(k) or "") for k in ("title", "problem", "solution", "beneficiaries", "success_metrics")]
        + [str(t) for t in fields.get("tags") or []]
    ).lower()
    hits = []
    for theme in themes:
        words = [str(w).lower() for w in theme.get("words") or []]
        matched = [w for w in words if w and re.search(rf"\b{re.escape(w)}", text)]
        if matched:
            hits.append({"id": str(theme.get("id") or ""), "label": str(theme["label"]), "matched_terms": matched})
    hits.sort(key=lambda h: -len(h["matched_terms"]))
    return hits


def fit_band(matched: list[dict[str, Any]]) -> str:
    """strong / partial / exploratory. Exploratory is never a judgement on the idea."""
    if len(matched) >= FIT_STRONG_MIN_THEMES:
        return "strong"
    if len(matched) >= FIT_PARTIAL_MIN_THEMES:
        return "partial"
    return "exploratory"


def fit_angles(matched: list[dict[str, Any]], themes: list[dict[str, Any]]) -> list[str]:
    """Optional ways to link the idea to company priorities. The author may ignore them."""
    if matched:
        return [
            f"You touch on {m['label'].lower()} ({', '.join(m['matched_terms'][:3])}). "
            "Consider saying what changes for that priority and how you would see it."
            for m in matched[:3]
        ]
    angles = []
    for theme in themes[:3]:
        words = [str(w) for w in theme.get("words") or []][:2]
        hint = f" (for example {' or '.join(words)})" if words else ""
        angles.append(
            f"If this could help {str(theme['label']).lower()}{hint}, a sentence on how would strengthen it."
        )
    return angles


def missing_fields(fields: dict[str, Any]) -> list[str]:
    """Fields that are empty or too short to review well."""
    return [
        name for name, minimum in MIN_FIELD_CHARS.items()
        if len(str(fields.get(name) or "").strip()) < minimum
    ]


def local_suggestions(fields: dict[str, Any], missing: list[str]) -> list[dict[str, str]]:
    """Field suggestions from the local rules (questions and scaffolds, never invented facts)."""
    out = [
        {
            "field": name,
            "kind": "clarifying_question",
            "text": f"{AI_REVIEW_FIELD_HINTS[name][0]} is thin. {AI_REVIEW_FIELD_HINTS[name][1]}.",
            "rationale": "Reviewers score what is written; short fields are hard to judge.",
        }
        for name in missing
        if name in AI_REVIEW_FIELD_HINTS
    ]
    for item in heuristics.enhancement(fields).get("suggestions") or []:
        is_metric = item.get("kind") != "problem_expand"
        if is_metric and "success_metrics" not in missing:
            continue
        out.append(
            {
                "field": "problem" if item.get("kind") == "problem_expand" else "success_metrics",
                "kind": "rewrite" if item.get("kind") == "problem_expand" else "metric",
                "text": str(item.get("text") or ""),
                "rationale": str(item.get("rationale") or ""),
            }
        )
    return out


def build_local_review(fields: dict[str, Any], themes: list[dict[str, Any]]) -> dict[str, Any]:
    """Full review from local rules. Deterministic."""
    matched = match_themes(fields, themes)
    band = fit_band(matched)
    missing = missing_fields(fields)
    metrics = (
        heuristics.enhancement(fields).get("suggested_metrics") or []
        if "success_metrics" in missing
        else []
    )
    summary = {
        "strong": "Links clearly to several company priorities.",
        "partial": "Links to one company priority; the link could be made more explicit.",
        "exploratory": "No clear link to a listed company priority yet. Treated as exploratory, not marked down.",
    }[band]
    if missing:
        summary += f" {len(missing)} field(s) need more detail before review."
    return {
        "engine": AI_REVIEW_ENGINE_LOCAL,
        "simulated": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "dotkonnekt_fit": {"band": band, "themes": matched, "angles": fit_angles(matched, themes)},
        "suggestions": local_suggestions(fields, missing),
        "suggested_metrics": [
            {
                "metric": str(m.get("metric") or ""),
                "unit": str(m.get("unit") or ""),
                "baseline_prompt": str(m.get("baseline_prompt") or ""),
            }
            for m in metrics
        ],
        "suggested_beneficiaries": [],
        "missing_fields": missing,
    }


def merge_live(local: dict[str, Any], enhancement: dict[str, Any]) -> dict[str, Any]:
    """Replace local suggestions with the Kompass workflow's, keeping the fit and checklist."""
    suggestions = [
        {
            "field": str(s.get("field") or enhancement.get("field") or "all"),
            "kind": str(s.get("kind") or "rewrite"),
            "text": str(s.get("text") or ""),
            "rationale": str(s.get("rationale") or ""),
        }
        for s in enhancement.get("suggestions") or []
        if isinstance(s, dict) and s.get("text")
    ]
    metrics = [
        {
            "metric": str(m.get("metric") or ""),
            "unit": str(m.get("unit") or ""),
            "baseline_prompt": str(m.get("baselinePrompt") or m.get("baseline_prompt") or ""),
        }
        for m in enhancement.get("suggestedMetrics") or enhancement.get("suggested_metrics") or []
        if isinstance(m, dict)
    ]
    beneficiaries = enhancement.get("suggestedBeneficiaries") or enhancement.get("suggested_beneficiaries") or []
    return {
        **local,
        "engine": idea_enhancement_flow.ENGINE_LABEL,
        "simulated": False,
        "suggestions": suggestions or local["suggestions"],
        "suggested_metrics": metrics or local["suggested_metrics"],
        "suggested_beneficiaries": [str(b) for b in beneficiaries if b],
    }


async def build_review(session: AsyncSession, idea: Idea) -> dict[str, Any]:
    """Live review when the Kompass workflow is configured and answers; otherwise local."""
    fields = idea_fields(idea)
    local = build_local_review(fields, await company_themes(session))
    if idea_enhancement_flow.flow_configured():
        enhancement, error = await idea_enhancement_flow.run(fields, "all")
        if enhancement is not None:
            return merge_live(local, enhancement)
        local["summary"] += f" (Live workflow unavailable: {error}.)"
    return local


async def generate_and_store(idea_id: uuid.UUID) -> None:
    """Background task after submit: build the review and save it. Failures are logged, not raised."""
    async with AsyncSessionLocal() as session:
        try:
            idea = await session.get(Idea, idea_id)
            if idea is None or idea.status == "draft":
                return
            idea.ai_review = await build_review(session, idea)
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            logger.exception("AI review for idea %s could not be saved", idea_id)
