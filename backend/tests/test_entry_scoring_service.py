"""Local rubric scorer, ranking, Kompass reply parsing, and score permissions."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.constants.entry_scoring import SCORER_ENGINE_LOCAL
from app.services import entry_scoring_service as scoring
from app.services.github_repo_service import RepoSnapshot

CHALLENGE = "Reduce the time support agents spend triaging customer tickets every week."


def _entry(**overrides: object) -> scoring.EntryInput:
    base: dict[str, object] = {
        "idea_id": uuid.uuid4(),
        "title": "Ticket triage assistant",
        "problem": "Support agents spend hours every week triaging customer tickets by hand before answering.",
        "solution": "An assistant that tags and routes customer tickets so agents start on the right queue.",
        "beneficiaries": "Support agents and the customers waiting on replies across all regions.",
        "success_metrics": "Cut median triage time from 20 minutes to 5 minutes per ticket.",
        "tags": ["support", "tickets"],
        "effort": "S",
        "has_demo": True,
        "theme": "Customer support",
        "challenges": [CHALLENGE],
        "kind": "hackathon",
    }
    base.update(overrides)
    return scoring.EntryInput(**base)  # type: ignore[arg-type]


def _repo() -> RepoSnapshot:
    return RepoSnapshot(
        status="ok",
        readme="Triage assistant for support tickets. " * 20,
        paths=["src/app.py", "tests/test_app.py"],
        evidence={
            "status": "ok", "file_count": 12, "recent_commits": 9, "has_tests": True,
            "has_ci": True, "readme_chars": 800,
        },
    )


def test_strong_entry_scores_well_on_every_criterion() -> None:
    result = scoring.score_locally(_entry(repo=_repo()))
    assert result.simulated is True
    assert result.engine == SCORER_ENGINE_LOCAL
    for name in ("relevance", "feasibility", "impact", "originality"):
        assert result.criteria[name]["score"] >= 7.0, name
        assert result.criteria[name]["rationale"]
    assert result.overall is not None and result.overall >= 7.5


def test_scores_are_deterministic() -> None:
    entry = _entry(repo=_repo())
    assert scoring.score_locally(entry).criteria == scoring.score_locally(entry).criteria


def test_readable_repo_raises_feasibility() -> None:
    without = scoring.score_feasibility(_entry())
    with_repo = scoring.score_feasibility(_entry(repo=_repo()))
    assert with_repo["score"] > without["score"]
    assert "no GitHub link" in without["rationale"]


def test_off_topic_entry_scores_low_relevance() -> None:
    entry = _entry(title="Office plants", problem="The office has too few plants on the third floor.",
                   solution="Buy more plants and water them on Fridays.", tags=["plants"])
    assert scoring.score_relevance(entry)["score"] <= 3.0


def test_documents_count_toward_relevance() -> None:
    bare = _entry(title="Helper", problem="Things are slow for our team today in general.",
                  solution="Build a helper tool that speeds things up.", tags=[])
    documented = _entry(title="Helper", problem=bare.problem, solution=bare.solution, tags=[],
                        documents=[("design.md", "Support agents triaging customer tickets each week.")])
    assert scoring.score_relevance(documented)["score"] > scoring.score_relevance(bare)["score"]


def test_similar_earlier_idea_lowers_originality() -> None:
    assert scoring.score_originality(_entry(max_similarity=0.6))["score"] == 2.0
    assert scoring.score_originality(_entry(max_similarity=0.0))["score"] == 10.0


def test_entry_without_text_is_not_scored_and_ranks_last() -> None:
    empty = scoring.score_locally(_entry(problem="", solution=""))
    assert empty.overall is None
    assert all(c["score"] is None for c in empty.criteria.values())
    good = scoring.score_locally(_entry(repo=_repo()))
    ranked = scoring.rank_entries([empty, good])
    assert [r.rank for r in ranked] == [1, 2]
    assert ranked[0] is good


def test_ties_go_to_higher_impact() -> None:
    a = scoring.ScoredEntry(uuid.uuid4(), {"impact": {"score": 5.0}}, 7.0, "", "x", True, {})
    b = scoring.ScoredEntry(uuid.uuid4(), {"impact": {"score": 8.0}}, 7.0, "", "x", True, {})
    assert scoring.rank_entries([a, b])[0] is b


def test_evidence_lists_documents_without_their_text() -> None:
    ev = scoring.evidence_for(_entry(documents=[("spec.pdf", "abc")]))
    assert ev["documents"] == [{"filename": "spec.pdf", "text_chars": 3}]
    assert ev["has_demo"] is True


def test_parse_kompass_scores_reads_panel_scores() -> None:
    idea = str(uuid.uuid4())
    parsed = {
        "shortlistSuggestion": [
            {
                "ideaId": idea,
                "rationale": "Clear fit.",
                "criteriaScores": {
                    "relevance": {"panelScore": 8},
                    "feasibility": {"panelScore": 7},
                    "impact": {"panelScore": 9},
                    "originality": {"panelScore": 6},
                },
            },
            {"ideaId": str(uuid.uuid4()), "criteriaScores": {"relevance": {"panelScore": 5}}},
        ]
    }
    out = scoring.parse_kompass_scores(parsed)
    assert list(out) == [idea]
    assert out[idea]["overall"] == 7.5
    assert out[idea]["criteria"]["impact"]["score"] == 9.0


def test_parse_kompass_scores_ignores_unknown_shapes() -> None:
    assert not scoring.parse_kompass_scores({"foo": 1})
    assert not scoring.parse_kompass_scores({"shortlistSuggestion": "nope"})


def _event() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), kind="hackathon", theme="Customer support", challenges=[CHALLENGE])


def test_rank_context_carries_text_docs_github_and_signals() -> None:
    entry = _entry(repo=_repo(), documents=[("design.md", "Triage design " * 10)])
    signals = {str(entry.idea_id): {"audience_votes": 3, "panel_avg": 7.5, "panel_n": 2}}
    payload = scoring.rank_context_payload(_event(), [entry], signals)  # type: ignore[arg-type]
    assert payload["ideathon"]["challenges"] == [CHALLENGE]
    assert payload["rubric_version"]
    row = payload["entries"][0]
    assert row["ideaId"] == str(entry.idea_id)
    assert row["problem"] == entry.problem and row["successMetrics"] == entry.success_metrics
    assert row["documents"][0]["filename"] == "design.md"
    assert row["github"]["has_tests"] is True and row["github"]["readmeExcerpt"]
    assert row["audience_votes"] == 3 and row["panel_avg"] == 7.5


def test_rank_context_has_no_author_team_or_repo_owner() -> None:
    repo = _repo()
    repo.evidence["full_name"] = "secret-owner/repo"
    payload = scoring.rank_context_payload(_event(), [_entry(repo=repo)], {})  # type: ignore[arg-type]
    blob = str(payload)
    assert "author" not in blob and "team" not in blob and "secret-owner" not in blob


def test_document_excerpts_respect_the_budget() -> None:
    docs = [(f"d{i}.md", "x" * 5000) for i in range(4)]
    excerpts = scoring._doc_excerpts(docs)  # pylint: disable=protected-access
    assert sum(len(d["excerpt"]) for d in excerpts) <= 6000
    assert len(excerpts) == 2


def test_parse_uses_per_criterion_reason_and_keeps_unscorable_rows() -> None:
    a, b, c = (str(uuid.uuid4()) for _ in range(3))
    parsed = {"shortlistSuggestion": [
        {"ideaId": a, "rationale": "Overall.", "criteriaScores": {
            "relevance": {"panelScore": 8, "reason": "Answers challenge 1."},
            "feasibility": {"panelScore": 7}, "impact": {"panelScore": 7}, "originality": {"panelScore": 6}}},
        {"ideaId": b, "rationale": "entry text not available", "criteriaScores": {
            n: {"panelScore": None} for n in ("relevance", "feasibility", "impact", "originality")}},
        {"ideaId": c, "criteriaScores": {"relevance": {"panelScore": 5}}},
    ]}
    out = scoring.parse_kompass_scores(parsed)
    assert out[a]["criteria"]["relevance"]["rationale"] == "Answers challenge 1."
    assert out[a]["criteria"]["impact"]["rationale"] == "Overall."
    assert out[b]["overall"] is None
    assert c not in out


async def test_kompass_failure_reason_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = scoring.EntryScoringService(session=SimpleNamespace())  # type: ignore[arg-type]
    monkeypatch.setattr(scoring.studio, "use_live_execute", lambda: True)
    monkeypatch.setattr(scoring.studio, "resolve_kompass_agent_id", lambda _k: "agent-1")
    monkeypatch.setattr(svc, "_signals", AsyncMock(return_value={}))
    monkeypatch.setattr(scoring.ideathon_rank_service, "propose_rank", AsyncMock(
        return_value=scoring.studio.ExecuteResult(success=False, error="gateway timeout")))
    scores, note = await svc._kompass_scores(_event(), [_entry()], None)  # pylint: disable=protected-access
    assert not scores
    assert "gateway timeout" in note


async def test_kompass_partial_reply_marks_missing_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = scoring.EntryScoringService(session=SimpleNamespace())  # type: ignore[arg-type]
    first, second = _entry(), _entry()
    reply = {"shortlistSuggestion": [{"ideaId": str(first.idea_id), "criteriaScores": {
        n: {"panelScore": 7} for n in ("relevance", "feasibility", "impact", "originality")}}]}
    monkeypatch.setattr(scoring.studio, "use_live_execute", lambda: True)
    monkeypatch.setattr(scoring.studio, "resolve_kompass_agent_id", lambda _k: "agent-1")
    monkeypatch.setattr(svc, "_signals", AsyncMock(return_value={}))
    monkeypatch.setattr(scoring.ideathon_rank_service, "propose_rank", AsyncMock(
        return_value=scoring.studio.ExecuteResult(success=True, result=reply)))
    scores, note = await svc._kompass_scores(_event(), [first, second], None)  # pylint: disable=protected-access
    assert list(scores) == [str(first.idea_id)]
    assert "did not score this entry" in note


def _actor(*roles: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), has_role=lambda r: r in roles)


async def test_only_organisers_can_run_scoring() -> None:
    svc = scoring.EntryScoringService(session=SimpleNamespace())  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await svc.run(uuid.uuid4(), _actor("reviewer"))  # type: ignore[arg-type]
    assert exc.value.status_code == 403


async def test_contributors_cannot_read_scores() -> None:
    svc = scoring.EntryScoringService(session=SimpleNamespace())  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await svc.list_scores(uuid.uuid4(), _actor("contributor"))  # type: ignore[arg-type]
    assert exc.value.status_code == 403


def test_off_topic_entry_overall_is_capped_by_relevance_gate() -> None:
    entry = _entry(title="Office plants", problem="The office has too few plants on the third floor today.",
                   solution="Buy more plants and water them on Fridays with a rota.", tags=["plants"],
                   max_similarity=0.0)
    result = scoring.score_locally(entry)
    assert result.criteria["relevance"]["score"] < 3.0
    assert result.overall == 4.0
    assert "capped" in result.rationale


def test_relevant_entry_is_not_capped() -> None:
    overall, note = scoring.gated_overall(
        {c: {"score": 8.0} for c in ("relevance", "feasibility", "impact", "originality")}
    )
    assert overall == 8.0 and note == ""


def test_kompass_scores_get_the_same_gate() -> None:
    idea = str(uuid.uuid4())
    parsed = {"shortlistSuggestion": [{"ideaId": idea, "criteriaScores": {
        "relevance": {"panelScore": 1}, "feasibility": {"panelScore": 9},
        "impact": {"panelScore": 9}, "originality": {"panelScore": 10}}}]}
    assert scoring.parse_kompass_scores(parsed)[idea]["overall"] == 4.0
