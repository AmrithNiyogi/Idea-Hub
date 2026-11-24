"""Score every entry of an ideathon or hackathon against the rubric, and save the result.

Responsibilities:
- Gather each entry's text, attached documents and GitHub evidence (author and team name left out).
- Score with the Kompass Rank agent when it is configured; otherwise, or for any entry the agent
  skipped, with the local rubric scorer (deterministic, labelled ``simulated``).
- Rank entries and upsert one ``entry_scores`` row per entry.

Collaborators:
- ``github_repo_service`` for repo evidence, ``entry_document_service`` for document text.
- ``ideathon_rank_service`` for the Kompass call. Rubric: ``docs/IDEATHON_SCORING_RUBRIC.md``.

Side Effects:
- Outbound GitHub and (optionally) Kompass calls. Writes ``entry_scores``.
- Scores are advice. The organiser still approves the shortlist and confirms winners.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.entry_scoring import (
    DOC_TEXT_FOR_SCORING_CHARS,
    EFFORT_FEASIBILITY,
    GITHUB_MAX_PARALLEL,
    GITHUB_STATUS_MISSING,
    GITHUB_STATUS_OK,
    HACKATHON_KIND,
    METRIC_UNIT_WORDS,
    MIN_SCORABLE_TEXT_CHARS,
    RANK_DOC_EXCERPT_CHARS,
    RANK_DOCS_TOTAL_CHARS,
    RANK_README_EXCERPT_CHARS,
    RELEVANCE_GATE_MIN,
    RELEVANCE_GATE_OVERALL_CAP,
    RUBRIC_CRITERIA,
    RUBRIC_VERSION,
    SCORE_MAX,
    SCORE_MIN,
    SCORER_ENGINE_KOMPASS,
    SCORER_ENGINE_LOCAL,
    SCORING_STOPWORDS,
)
from app.constants.ideathon_constants import (
    DEFAULT_AUDIENCE_WEIGHT,
    DEFAULT_PANEL_WEIGHT,
    ORG_ROLES,
    PANEL_SCORE_ROLES,
)
from app.dependencies.phase23_auth import Actor
from app.models.idea import Idea
from app.models.ideathon import EntryScore, Ideathon, IdeathonEntry
from app.schemas.entry_scoring import CriterionScore, EntryScoreOut, EntryScoresOut
from app.services import aistudio_execute_client as studio
from app.services import agent_heuristics as heuristics
from app.services import github_repo_service, ideathon_rank_service
from app.services.agent_entry_service import entry_briefs
from app.services.entry_document_service import document_texts
from app.services.github_repo_service import RepoSnapshot

logger = logging.getLogger(__name__)


@dataclass
class EntryInput:
    """Everything the scorer may read about one entry. No author, no team name."""

    idea_id: uuid.UUID
    title: str
    problem: str
    solution: str
    beneficiaries: str
    success_metrics: str
    tags: list[str]
    effort: str
    has_demo: bool
    theme: str
    challenges: list[str]
    kind: str
    documents: list[tuple[str, str]] = field(default_factory=list)
    repo: RepoSnapshot = field(default_factory=github_repo_service.missing_snapshot)
    max_similarity: float = 0.0


@dataclass
class ScoredEntry:
    """One entry's scores before ranking."""

    idea_id: uuid.UUID
    criteria: dict[str, dict[str, Any]]
    overall: Optional[float]
    rationale: str
    engine: str
    simulated: bool
    evidence: dict[str, Any]
    rank: int = 0


def _clamp(value: float) -> float:
    return round(max(SCORE_MIN, min(SCORE_MAX, value)), 1)


def _terms(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(w) > 2 and w not in SCORING_STOPWORDS
    }


def evidence_for(entry: EntryInput) -> dict[str, Any]:
    """Stored evidence: GitHub summary, document names and readable size, demo flag."""
    return {
        "github": entry.repo.evidence,
        "documents": [{"filename": name, "text_chars": len(text)} for name, text in entry.documents],
        "has_demo": entry.has_demo,
    }


def _doc_text(entry: EntryInput) -> str:
    return " ".join(text for _, text in entry.documents)[:DOC_TEXT_FOR_SCORING_CHARS]


def score_relevance(entry: EntryInput) -> dict[str, Any]:
    """Fit to the challenge statements, from shared terms (rubric: Relevance)."""
    entry_terms = _terms(
        " ".join([entry.title, entry.problem, entry.solution, " ".join(entry.tags),
                  _doc_text(entry), entry.repo.readme])
    )
    challenges = [c for c in entry.challenges if c.strip()] or [entry.theme]
    best, covered, best_shared = 0.0, 0, set()
    for challenge in challenges:
        wanted = _terms(challenge)
        if not wanted:
            continue
        shared = wanted & entry_terms
        overlap = len(shared) / len(wanted)
        if overlap >= 0.25:
            covered += 1
        if overlap > best:
            best, best_shared = overlap, shared
    theme_hit = bool(_terms(entry.theme) & entry_terms)
    score = 2.0 + 6.0 * min(1.0, best / 0.5) + 2.0 * (covered / len(challenges))
    if not theme_hit and best == 0:
        score = 1.0
    shared_txt = ", ".join(sorted(best_shared)[:6]) or "none"
    return {
        "score": _clamp(score),
        "rationale": (
            f"Answers {covered} of {len(challenges)} challenge statement(s). "
            f"Closest challenge shares these terms: {shared_txt}."
        ),
    }


def score_feasibility(entry: EntryInput) -> dict[str, Any]:
    """Can a small team build it, using effort and built evidence (rubric: Feasibility)."""
    score = 3.0 + EFFORT_FEASIBILITY.get(entry.effort, 1.0)
    notes = [f"effort {entry.effort}"]
    gh = entry.repo.evidence
    if entry.repo.status == GITHUB_STATUS_OK:
        score += 1.5
        notes.append(f"repo readable ({gh.get('file_count', 0)} files)")
        if int(gh.get("file_count", 0)) >= 5:
            score += 0.5
        if int(gh.get("recent_commits", 0)) >= 5:
            score += 0.5
            notes.append(f"{gh.get('recent_commits')} recent commits")
        if gh.get("has_tests"):
            score += 0.5
            notes.append("has tests")
        if gh.get("has_ci"):
            score += 0.25
            notes.append("has CI")
        if int(gh.get("readme_chars", 0)) >= 300:
            score += 0.5
            notes.append("README explains the project")
    elif entry.repo.status == GITHUB_STATUS_MISSING:
        notes.append("no GitHub link")
    else:
        notes.append("GitHub link could not be read")
    if entry.has_demo:
        score += 1.0
        notes.append("live demo link")
    if any(text for _, text in entry.documents):
        score += 0.25
        notes.append("documentation attached")
    return {"score": _clamp(score), "rationale": "Evidence: " + "; ".join(notes) + "."}


def score_impact(entry: EntryInput) -> dict[str, Any]:
    """Size of the stated benefit, from the entry's own words only (rubric: Impact)."""
    score, notes = 2.0, []
    ben = entry.beneficiaries.strip()
    if len(ben) >= 60:
        score += 2.5
        notes.append("beneficiaries described in detail")
    elif len(ben) >= 15:
        score += 1.5
        notes.append("beneficiaries named")
    else:
        notes.append("beneficiaries not stated")
    metrics = entry.success_metrics.strip().lower()
    if len(metrics) >= 15:
        score += 2.0
        notes.append("success measure stated")
        if re.search(r"\d", metrics):
            score += 1.5
            notes.append("measure has a number")
        if any(w in metrics for w in METRIC_UNIT_WORDS):
            score += 1.0
            notes.append("measure has a unit")
    else:
        notes.append("no success measure")
    if len(entry.problem.strip()) >= 80:
        score += 1.0
        notes.append("problem explained")
    return {"score": _clamp(score), "rationale": "Based on what the entry states: " + "; ".join(notes) + "."}


def score_originality(entry: EntryInput) -> dict[str, Any]:
    """Newness against earlier ideas in the hub (rubric: Originality)."""
    sim = max(0.0, entry.max_similarity)
    score = 2.0 + 8.0 * (1.0 - min(1.0, sim / 0.6))
    return {
        "score": _clamp(score),
        "rationale": (
            f"Closest earlier idea overlaps about {round(sim * 100)}% in wording and tags."
            if sim
            else "No similar earlier idea found in the hub."
        ),
    }


def gated_overall(criteria: dict[str, dict[str, Any]]) -> tuple[Optional[float], str]:
    """Mean of the four criteria, capped when Relevance is below the gate. Returns (overall, note)."""
    values = [float(c["score"]) for c in criteria.values() if isinstance(c.get("score"), (int, float))]
    if len(values) != len(RUBRIC_CRITERIA):
        return None, ""
    overall = round(sum(values) / len(values), 2)
    relevance = criteria.get("relevance", {}).get("score")
    if isinstance(relevance, (int, float)) and relevance < RELEVANCE_GATE_MIN and overall > RELEVANCE_GATE_OVERALL_CAP:
        return RELEVANCE_GATE_OVERALL_CAP, (
            f" Overall capped at {RELEVANCE_GATE_OVERALL_CAP:g} because Relevance is below "
            f"{RELEVANCE_GATE_MIN:g} (mean was {overall:g})."
        )
    return overall, ""


def score_locally(entry: EntryInput) -> ScoredEntry:
    """Deterministic rubric scores. Same input always gives the same scores."""
    readable = len((entry.problem + entry.solution).strip()) + len(_doc_text(entry))
    if readable < MIN_SCORABLE_TEXT_CHARS:
        empty: dict[str, dict[str, Any]] = {
            c: {"score": None, "rationale": "entry text not available"} for c in RUBRIC_CRITERIA
        }
        return ScoredEntry(entry.idea_id, empty, None, "entry text not available",
                           SCORER_ENGINE_LOCAL, True, evidence_for(entry))
    criteria: dict[str, dict[str, Any]] = {
        "relevance": score_relevance(entry),
        "feasibility": score_feasibility(entry),
        "impact": score_impact(entry),
        "originality": score_originality(entry),
    }
    overall, gate_note = gated_overall(criteria)
    rationale = "Scored by the local rubric scorer from the entry text, documents and GitHub evidence." + gate_note
    if entry.kind == HACKATHON_KIND and entry.repo.status != GITHUB_STATUS_OK:
        rationale += " Hackathon entry without a readable repository."
    return ScoredEntry(entry.idea_id, criteria, overall, rationale, SCORER_ENGINE_LOCAL, True,
                       evidence_for(entry))


def rank_entries(scored: list[ScoredEntry]) -> list[ScoredEntry]:
    """Best overall first; ties go to higher Impact; unscorable entries last."""
    def key(s: ScoredEntry) -> tuple[int, float, float]:
        impact = s.criteria.get("impact", {}).get("score")
        return (
            0 if s.overall is not None else 1,
            -(s.overall or 0.0),
            -(float(impact) if impact is not None else 0.0),
        )

    ordered = sorted(scored, key=key)
    for n, item in enumerate(ordered, start=1):
        item.rank = n
    return ordered


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _clamp(float(value))
    return None


def parse_kompass_scores(parsed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-idea criteria from a Rank agent reply (``shortlistSuggestion``). Unknown shapes give {}.

    Each criterion's score is its ``panelScore`` (the agent's own rubric score; audience votes stay
    out of the saved AI score). A per-criterion ``reason`` is used when the agent gives one.
    Rows with all four scores null are kept as not scorable; rows with only some missing are dropped.
    """
    rows = parsed.get("shortlistSuggestion") or parsed.get("shortlist_suggestion") or []
    out: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("ideaId"):
            continue
        raw = row.get("criteriaScores") or {}
        overall_reason = str(row.get("rationale") or "")
        criteria: dict[str, dict[str, Any]] = {}
        for name in RUBRIC_CRITERIA:
            cell = raw.get(name) if isinstance(raw, dict) else None
            value = cell.get("panelScore") if isinstance(cell, dict) else cell
            reason = cell.get("reason") if isinstance(cell, dict) else None
            criteria[name] = {"score": _num(value), "rationale": str(reason or overall_reason)}
        present = [c["score"] for c in criteria.values() if c["score"] is not None]
        if present and len(present) != len(RUBRIC_CRITERIA):
            continue
        overall, gate_note = gated_overall(criteria)
        out[str(row["ideaId"])] = {
            "criteria": criteria,
            "overall": overall,
            "rationale": overall_reason + gate_note,
        }
    return out


def _doc_excerpts(documents: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Document excerpts for the agent, within a per-entry character budget."""
    out, budget = [], RANK_DOCS_TOTAL_CHARS
    for name, text in documents:
        if budget <= 0:
            break
        excerpt = text[: min(RANK_DOC_EXCERPT_CHARS, budget)]
        out.append({"filename": name, "excerpt": excerpt})
        budget -= len(excerpt)
    return out


def rank_context_payload(
    event: Ideathon, entries: list[EntryInput], signals: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Full context for the Kompass Rank agent. No author, team or repository owner names."""
    return {
        "rubric_version": RUBRIC_VERSION,
        "ideathon": {
            "id": str(event.id),
            "kind": event.kind or "ideathon",
            "theme": event.theme,
            "challenges": [str(c) for c in (event.challenges or [])],
        },
        "entries": [
            {
                "ideaId": str(e.idea_id),
                "title": e.title,
                "problem": e.problem,
                "solution": e.solution,
                "beneficiaries": e.beneficiaries,
                "successMetrics": e.success_metrics,
                "tags": e.tags,
                "effort": e.effort,
                "hasDemo": e.has_demo,
                "documents": _doc_excerpts(e.documents),
                "github": {
                    **{k: v for k, v in e.repo.evidence.items() if k != "full_name"},
                    "readmeExcerpt": e.repo.readme[:RANK_README_EXCERPT_CHARS],
                },
                **signals.get(str(e.idea_id), {"audience_votes": 0, "panel_avg": None, "panel_n": 0}),
            }
            for e in entries
        ],
    }


def _to_out(row: EntryScore) -> EntryScoreOut:
    return EntryScoreOut(
        idea_id=row.idea_id,
        rank=row.rank,
        overall=row.overall,
        criteria={k: CriterionScore(**v) for k, v in (row.criteria or {}).items()},
        rationale=row.rationale,
        engine=row.engine,
        simulated=row.simulated,
        evidence=row.evidence or {},
        scored_at=row.scored_at,
    )


class EntryScoringService:
    """Run and read saved AI rubric scores for an event."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _event(self, ideathon_id: uuid.UUID) -> Ideathon:
        event = await self.session.get(Ideathon, ideathon_id)
        if event is None:
            raise HTTPException(404, "Ideathon not found.")
        return event

    async def _inputs(self, event: Ideathon) -> list[EntryInput]:
        idea_ids = list(
            (
                await self.session.execute(
                    select(IdeathonEntry.idea_id).where(IdeathonEntry.ideathon_id == event.id)
                )
            ).scalars().all()
        )
        if not idea_ids:
            return []
        ideas = (
            await self.session.execute(select(Idea).where(Idea.id.in_(idea_ids)))
        ).scalars().all()
        ideas = [i for i in ideas if i.status != "draft"]
        corpus = (
            await self.session.execute(
                select(Idea).where(Idea.status != "draft", Idea.id.not_in(idea_ids)).limit(500)
            )
        ).scalars().all()
        docs = await document_texts(self.session, [i.id for i in ideas])
        gate = asyncio.Semaphore(GITHUB_MAX_PARALLEL)

        async def snapshot(url: str | None) -> RepoSnapshot:
            async with gate:
                return await github_repo_service.fetch_snapshot(url)

        repos = await asyncio.gather(*(snapshot(i.github_url) for i in ideas))
        out: list[EntryInput] = []
        for idea, repo in zip(ideas, repos):
            similar = heuristics.similar_ideas(idea, corpus, limit=1)
            out.append(
                EntryInput(
                    idea_id=idea.id,
                    title=idea.title,
                    problem=idea.problem or "",
                    solution=idea.solution or "",
                    beneficiaries=idea.beneficiaries or "",
                    success_metrics=idea.success_metrics or "",
                    tags=[str(t) for t in (idea.tags or [])],
                    effort=idea.effort or "M",
                    has_demo=bool(idea.demo_url),
                    theme=event.theme,
                    challenges=[str(c) for c in (event.challenges or [])],
                    kind=event.kind or "ideathon",
                    documents=docs.get(idea.id, []),
                    repo=repo,
                    max_similarity=float(similar[0]["similarity"]) if similar else 0.0,
                )
            )
        return out

    async def _signals(self, event: Ideathon, entries: list[EntryInput]) -> dict[str, dict[str, Any]]:
        """Panel average and audience votes per entry (the same numbers the entries tool returns)."""
        briefs = await entry_briefs(self.session, event.id, [e.idea_id for e in entries])
        return {
            str(b.id): {"audience_votes": b.audience_votes, "panel_avg": b.panel_avg, "panel_n": b.panel_n}
            for b in briefs
        }

    async def rank_context(self, ideathon_id: uuid.UUID) -> dict[str, Any]:
        """Context for a Rank agent run started from the organiser's Agents panel."""
        event = await self._event(ideathon_id)
        entries = await self._inputs(event)
        return rank_context_payload(event, entries, await self._signals(event, entries))

    async def _kompass_scores(
        self, event: Ideathon, entries: list[EntryInput], token: str | None
    ) -> tuple[dict[str, dict[str, Any]], str]:
        """Rank agent scores per idea, plus a note explaining any fallback ("" when none)."""
        if not (studio.use_live_execute() and studio.resolve_kompass_agent_id(ideathon_rank_service.HUB_AGENT_KEY)):
            return {}, ""
        weights = {"panel": DEFAULT_PANEL_WEIGHT / 100, "audience": DEFAULT_AUDIENCE_WEIGHT / 100}
        context = rank_context_payload(event, entries, await self._signals(event, entries))
        result = await ideathon_rank_service.propose_rank(
            event.id, weights, tool_auth_token=token, context=context
        )
        if not result.success:
            note = f"Kompass Rank agent failed ({result.error or 'no reason given'}); scored locally."
            logger.warning("Entry scoring for %s: %s", event.id, note)
            return {}, note
        scores = parse_kompass_scores(studio.parse_structured_result(result.result))
        if not scores:
            note = "Kompass Rank agent returned no usable scores; scored locally."
            logger.warning(
                "Entry scoring for %s: %s Reply starts: %.300s", event.id, note, result.result_text or ""
            )
            return {}, note
        missing = [e for e in entries if str(e.idea_id) not in scores]
        if missing:
            logger.warning(
                "Entry scoring for %s: %d entries missing from the agent reply", event.id, len(missing)
            )
            return scores, "Kompass Rank agent did not score this entry; scored locally."
        return scores, ""

    async def run(self, ideathon_id: uuid.UUID, actor: Actor, token: str | None = None) -> EntryScoresOut:
        """Score every entry now, save, and return all scores."""
        if not any(actor.has_role(r) for r in ORG_ROLES):
            raise HTTPException(403, "Only leadership or admin can run AI scoring.")
        event = await self._event(ideathon_id)
        entries = await self._inputs(event)
        if not entries:
            raise HTTPException(400, "There are no entries to score yet.")
        live, note = await self._kompass_scores(event, entries, token)
        scored: list[ScoredEntry] = []
        for entry in entries:
            hit = live.get(str(entry.idea_id))
            if hit:
                scored.append(ScoredEntry(entry.idea_id, hit["criteria"], hit["overall"],
                                          hit["rationale"], SCORER_ENGINE_KOMPASS, False,
                                          evidence_for(entry)))
                continue
            local = score_locally(entry)
            if note:
                local.rationale = f"{note} {local.rationale}"
                local.evidence["scoring_note"] = note
            scored.append(local)
        ranked = rank_entries(scored)
        existing = {
            row.idea_id: row
            for row in (
                await self.session.execute(select(EntryScore).where(EntryScore.ideathon_id == event.id))
            ).scalars().all()
        }
        now = datetime.now(timezone.utc)
        keep = {s.idea_id for s in ranked}
        for idea_id, row in existing.items():
            if idea_id not in keep:
                await self.session.delete(row)
        for s in ranked:
            row = existing.get(s.idea_id) or EntryScore(ideathon_id=event.id, idea_id=s.idea_id)
            row.rank, row.overall, row.criteria = s.rank, s.overall, s.criteria
            row.rationale, row.evidence = s.rationale, s.evidence
            row.engine, row.simulated = s.engine, s.simulated
            row.rubric_version, row.scored_by, row.scored_at = RUBRIC_VERSION, actor.id, now
            if s.idea_id not in existing:
                self.session.add(row)
        await self.session.commit()
        return await self.list_scores(ideathon_id, actor)

    async def list_scores(self, ideathon_id: uuid.UUID, actor: Actor) -> EntryScoresOut:
        """Saved scores, best first."""
        if not any(actor.has_role(r) for r in (*ORG_ROLES, *PANEL_SCORE_ROLES)):
            raise HTTPException(403, "AI scores are visible to reviewers, leadership and admin.")
        await self._event(ideathon_id)
        rows = (
            await self.session.execute(
                select(EntryScore).where(EntryScore.ideathon_id == ideathon_id).order_by(EntryScore.rank)
            )
        ).scalars().all()
        return EntryScoresOut(
            ideathon_id=ideathon_id, rubric_version=RUBRIC_VERSION, items=[_to_out(r) for r in rows]
        )
