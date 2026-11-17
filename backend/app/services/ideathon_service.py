"""Ideathon campaign service (Phase 3).

Phases: open → shortlist → pitch → results → handoff → complete.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ideathon_constants import (
    DEFAULT_AUDIENCE_WEIGHT,
    DEFAULT_PANEL_WEIGHT,
    IT_NEXT,
    LINKABLE_IDEA_STATUSES,
    MAX_SHORTLIST,
    MAX_WINNERS,
    MIN_HANDOFF_STATEMENT_LEN,
    MIN_SHORTLIST,
    ORG_ROLES,
    PANEL_SCORE_ROLES,
)
from app.dependencies.phase23_auth import Actor
from app.models.ideathon import (
    AudienceVote,
    Ideathon,
    IdeathonEntry,
    IdeathonHandoff,
    PitchScore,
)
from app.repositories.ideathon_repository import IdeathonRepository
from app.schemas.ideathon import (
    AudienceVoteRequest,
    ConfirmWinnersRequest,
    HandoffOut,
    HandoffRequest,
    IdeathonCreate,
    IdeathonDetailOut,
    IdeathonSummaryOut,
    LinkIdeaRequest,
    MovePitchRequest,
    PitchScoreRequest,
    ShortlistApprove,
    TallyRowOut,
)
from app.services.recognition_service import RecognitionService
from app.services.spine_bridge import SpineBridge


def _now() -> datetime:
    return datetime.now(timezone.utc)


class IdeathonService:
    """Application service for ideathon campaigns."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IdeathonRepository(session)
        self.spine = SpineBridge(session)
        self.recog = RecognitionService(session)

    def _require_org(self, actor: Actor) -> None:
        if not any(actor.has_role(r) for r in ORG_ROLES):
            raise HTTPException(403, "Organiser action requires leadership or admin.")

    async def list_ideathons(self) -> list[IdeathonSummaryOut]:
        items = await self.repo.list_all()
        out: list[IdeathonSummaryOut] = []
        for it in items:
            entries = await self.repo.entries_for(it.id)
            out.append(
                IdeathonSummaryOut(
                    id=it.id,
                    title=it.title,
                    theme=it.theme,
                    phase=it.phase,
                    start_at=it.start_at,
                    end_at=it.end_at,
                    sponsor_id=it.sponsor_id,
                    organiser_id=it.organiser_id,
                    entry_count=len(entries),
                    shortlist_count=len(it.shortlist or []),
                    completed_at=it.completed_at,
                )
            )
        return out

    async def get(self, ideathon_id: uuid.UUID) -> IdeathonDetailOut:
        it = await self.repo.get(ideathon_id)
        if not it:
            raise HTTPException(404, "Ideathon not found.")
        return IdeathonDetailOut(
            id=it.id,
            title=it.title,
            theme=it.theme,
            challenges=list(it.challenges or []),
            phase=it.phase,
            phase_log=list(it.phase_log or []),
            start_at=it.start_at,
            end_at=it.end_at,
            sponsor_id=it.sponsor_id,
            organiser_id=it.organiser_id,
            shortlist=list(it.shortlist or []),
            shortlisted_at=it.shortlisted_at,
            shortlist_edited=it.shortlist_edited,
            voting_closed_at=it.voting_closed_at,
            winners=list(it.winners or []),
            results_at=it.results_at,
            tally=it.tally,
            completed_at=it.completed_at,
            entry_idea_ids=[e.idea_id for e in it.entries],
        )

    async def create(self, body: IdeathonCreate, actor: Actor) -> dict:
        self._require_org(actor)
        if body.end_at <= body.start_at:
            raise HTTPException(400, "The end date must be after the start date.")
        it = Ideathon(
            title=body.title.strip(),
            theme=body.theme.strip(),
            challenges=body.challenges,
            sponsor_id=body.sponsor_id,
            organiser_id=actor.id,
            start_at=body.start_at,
            end_at=body.end_at,
            phase="open",
            phase_log=[{"phase": "open", "at": _now().isoformat(), "by": str(actor.id)}],
            shortlist=[],
            winners=[],
        )
        await self.repo.add(it)
        await self.session.commit()
        return {"id": str(it.id)}

    async def advance(self, ideathon_id: uuid.UUID, actor: Actor) -> dict:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.completed_at:
            raise HTTPException(400, "This ideathon is complete.")
        nxt = IT_NEXT.get(it.phase)
        if not nxt:
            raise HTTPException(
                400,
                "Handoff is the last phase. Use Mark complete once winners are handed off.",
            )
        entries = await self.repo.entries_for(it.id)
        if it.phase == "open" and len(entries) < 2:
            raise HTTPException(400, "At least 2 entries are needed before shortlisting.")
        if it.phase == "shortlist" and len(it.shortlist or []) < MIN_SHORTLIST:
            raise HTTPException(
                400, "Approve a shortlist of at least 2 entries before Pitch day."
            )
        if it.phase == "pitch" and not it.voting_closed_at:
            raise HTTPException(400, "Close voting before moving to Results.")
        if it.phase == "results" and not (it.winners or []):
            raise HTTPException(400, "Confirm at least one winner before Handoff.")
        it.phase = nxt
        log = list(it.phase_log or [])
        log.append({"phase": nxt, "at": _now().isoformat(), "by": str(actor.id)})
        it.phase_log = log
        await self.session.commit()
        return {"phase": nxt}

    async def link_idea(
        self, ideathon_id: uuid.UUID, body: LinkIdeaRequest, actor: Actor
    ) -> dict:
        it = await self._require(ideathon_id)
        if it.phase != "open":
            raise HTTPException(400, "This ideathon is no longer accepting submissions.")
        idea = await self.spine.get_idea(body.idea_id)
        if not idea:
            raise HTTPException(404, "Idea not found.")
        if idea.author_id != actor.id and actor.id not in idea.co_author_ids:
            raise HTTPException(403, "You can link only ideas you wrote or co-wrote.")
        if idea.status not in LINKABLE_IDEA_STATUSES:
            raise HTTPException(400, "Only active ideas can join an ideathon.")
        if await self.repo.entry_for_idea(body.idea_id):
            raise HTTPException(409, "This idea is already part of an ideathon.")
        self.session.add(
            IdeathonEntry(
                ideathon_id=it.id,
                idea_id=body.idea_id,
                linked_by=actor.id,
            )
        )
        await self.spine.set_idea_ideathon(body.idea_id, it.id)
        await self.session.commit()
        return {"title": idea.title}

    async def unlink_idea(
        self, ideathon_id: uuid.UUID, idea_id: uuid.UUID, actor: Actor
    ) -> dict:
        it = await self._require(ideathon_id)
        if it.phase != "open":
            raise HTTPException(400, "Entries are locked once submissions close.")
        entry = await self.repo.entry_for_idea(idea_id)
        if not entry or entry.ideathon_id != it.id:
            raise HTTPException(404, "This idea is not an entry.")
        idea = await self.spine.get_idea(idea_id)
        if not idea or (
            idea.author_id != actor.id and not actor.has_role("admin")
        ):
            raise HTTPException(403, "Only the author can remove an entry.")
        await self.session.delete(entry)
        await self.spine.set_idea_ideathon(idea_id, None)
        await self.session.commit()
        return {"ok": True}

    async def approve_shortlist(
        self, ideathon_id: uuid.UUID, body: ShortlistApprove, actor: Actor
    ) -> dict:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.phase != "shortlist":
            raise HTTPException(400, "Shortlist can be approved only during Shortlist phase.")
        entries = {e.idea_id for e in await self.repo.entries_for(it.id)}
        ids = [i for i in body.idea_ids if i in entries]
        ids = list(dict.fromkeys(ids))
        if len(ids) < MIN_SHORTLIST:
            raise HTTPException(400, f"Shortlist at least {MIN_SHORTLIST} entries.")
        if len(ids) > MAX_SHORTLIST:
            raise HTTPException(400, f"Shortlist at most {MAX_SHORTLIST} entries.")
        it.shortlist = ids
        it.shortlisted_at = _now()
        it.shortlist_edited = True
        await self.session.commit()
        return {"count": len(ids), "edited": it.shortlist_edited}

    async def move_pitch(
        self, ideathon_id: uuid.UUID, body: MovePitchRequest, actor: Actor
    ) -> dict:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.phase not in {"shortlist", "pitch"} or it.voting_closed_at:
            raise HTTPException(400, "Pitch order can no longer be changed.")
        sl = list(it.shortlist or [])
        try:
            k = sl.index(body.idea_id)
        except ValueError as exc:
            raise HTTPException(400, "Idea not on shortlist.") from exc
        to = k - 1 if body.direction == "up" else k + 1
        if to < 0 or to >= len(sl):
            raise HTTPException(400, "It cannot move further.")
        sl[k], sl[to] = sl[to], sl[k]
        it.shortlist = sl
        await self.session.commit()
        return {"ok": True}

    async def score_pitch(
        self, ideathon_id: uuid.UUID, body: PitchScoreRequest, actor: Actor
    ) -> dict:
        if not any(actor.has_role(r) for r in PANEL_SCORE_ROLES):
            raise HTTPException(403, "Panel scoring is for reviewers, leadership, admin.")
        it = await self._require(ideathon_id)
        if it.phase != "pitch" or it.voting_closed_at:
            raise HTTPException(400, "Panel scoring is open only on pitch day.")
        if body.idea_id not in (it.shortlist or []):
            raise HTTPException(400, "That entry is not on the shortlist.")
        idea = await self.spine.get_idea(body.idea_id)
        if idea and (
            idea.author_id == actor.id or actor.id in idea.co_author_ids
        ):
            raise HTTPException(403, "You wrote this idea, so you cannot score it.")
        existing = await self.repo.get_pitch_score(it.id, body.idea_id, actor.id)
        if existing:
            existing.score = body.score
        else:
            self.session.add(
                PitchScore(
                    ideathon_id=it.id,
                    idea_id=body.idea_id,
                    user_id=actor.id,
                    score=body.score,
                )
            )
        await self.session.commit()
        return {"score": body.score}

    async def audience_vote(
        self, ideathon_id: uuid.UUID, body: AudienceVoteRequest, actor: Actor
    ) -> dict:
        it = await self._require(ideathon_id)
        if it.phase != "pitch" or it.voting_closed_at:
            raise HTTPException(400, "Audience voting is open only on pitch day.")
        if body.idea_id not in (it.shortlist or []):
            raise HTTPException(400, "That entry is not on the shortlist.")
        idea = await self.spine.get_idea(body.idea_id)
        if idea and (
            idea.author_id == actor.id or actor.id in idea.co_author_ids
        ):
            raise HTTPException(403, "You wrote this idea, so you cannot vote for it.")
        cur = await self.repo.get_audience_vote(it.id, actor.id)
        if cur and cur.idea_id == body.idea_id:
            await self.session.delete(cur)
            await self.session.commit()
            return {"voted": False}
        if cur:
            cur.idea_id = body.idea_id
            await self.session.commit()
            return {"voted": True, "changed": True}
        self.session.add(
            AudienceVote(
                ideathon_id=it.id, idea_id=body.idea_id, user_id=actor.id
            )
        )
        await self.session.commit()
        return {"voted": True, "changed": False}

    async def close_voting(self, ideathon_id: uuid.UUID, actor: Actor) -> dict:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.phase != "pitch":
            raise HTTPException(400, "Voting can be closed only on pitch day.")
        if it.voting_closed_at:
            raise HTTPException(400, "Voting is already closed.")
        scored_ideas = {s.idea_id for s in it.pitch_scores}
        missing = [i for i in (it.shortlist or []) if i not in scored_ideas]
        if missing:
            raise HTTPException(
                400,
                f"Every pitched entry needs at least one panel score. Missing {len(missing)}.",
            )
        it.voting_closed_at = _now()
        await self.session.commit()
        return {
            "audience": len(it.audience_votes),
            "panel": len(it.pitch_scores),
        }

    async def tally(self, ideathon_id: uuid.UUID) -> list[TallyRowOut]:
        it = await self._require(ideathon_id)
        return self._compute_tally(it)

    def _compute_tally(self, it: Ideathon) -> list[TallyRowOut]:
        pw, aw = DEFAULT_PANEL_WEIGHT, DEFAULT_AUDIENCE_WEIGHT
        shortlist = list(it.shortlist or [])
        scores_by_idea: dict[uuid.UUID, list[int]] = {i: [] for i in shortlist}
        for s in it.pitch_scores:
            if s.idea_id in scores_by_idea:
                scores_by_idea[s.idea_id].append(s.score)
        aud_by_idea: dict[uuid.UUID, int] = {i: 0 for i in shortlist}
        for v in it.audience_votes:
            if v.idea_id in aud_by_idea:
                aud_by_idea[v.idea_id] += 1
        panel_avgs = {
            i: (sum(sc) / len(sc) if sc else 0.0)
            for i, sc in scores_by_idea.items()
        }
        max_panel = max(panel_avgs.values()) if panel_avgs else 1.0
        max_aud = max(aud_by_idea.values()) if aud_by_idea else 1
        rows: list[TallyRowOut] = []
        for i in shortlist:
            pavg = panel_avgs[i]
            pn = len(scores_by_idea[i])
            ppct = (pavg / max_panel * 100) if max_panel else 0.0
            av = aud_by_idea[i]
            apct = (av / max_aud * 100) if max_aud else 0.0
            combined = (ppct * pw + apct * aw) / 100.0
            rows.append(
                TallyRowOut(
                    idea_id=i,
                    panel_avg=round(pavg, 2),
                    panel_n=pn,
                    panel_pct=round(ppct, 2),
                    audience_votes=av,
                    aud_pct=round(apct, 2),
                    combined=round(combined, 2),
                )
            )
        rows.sort(key=lambda r: r.combined, reverse=True)
        return rows

    async def confirm_winners(
        self, ideathon_id: uuid.UUID, body: ConfirmWinnersRequest, actor: Actor
    ) -> dict:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.phase != "results":
            raise HTTPException(400, "Winners are confirmed during the Results phase.")
        if it.winners:
            raise HTTPException(409, "Winners are already confirmed.")
        ids = [i for i in body.idea_ids if i in (it.shortlist or [])]
        ids = list(dict.fromkeys(ids))
        if not ids or len(ids) > MAX_WINNERS:
            raise HTTPException(400, "Choose 1 or 2 winners.")
        rank = self._compute_tally(it)
        it.tally = [r.model_dump(mode="json") for r in rank]
        it.winners = ids
        it.results_at = _now()
        it.confirmed_by = actor.id
        it.winner_override = bool(rank and rank[0].idea_id not in ids)

        async def authors(idea_id: uuid.UUID) -> list[uuid.UUID]:
            idea = await self.spine.get_idea(idea_id)
            if not idea:
                return []
            return [idea.author_id, *idea.co_author_ids]

        await self.recog.on_pitch_results(
            it.id, ids, list(it.shortlist or []), it.title, authors
        )
        await self.session.commit()
        return {
            "winners": len(ids),
            "finalists": len(it.shortlist or []) - len(ids),
        }

    async def list_handoffs(self, ideathon_id: uuid.UUID) -> list[HandoffOut]:
        it = await self._require(ideathon_id)
        rows = sorted(it.handoffs or [], key=lambda h: h.created_at)
        return [HandoffOut.model_validate(h) for h in rows]

    async def send_handoff(
        self, ideathon_id: uuid.UUID, body: HandoffRequest, actor: Actor
    ) -> HandoffOut:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.phase != "handoff":
            raise HTTPException(400, "Handoff is available in the Handoff phase.")
        if body.idea_id not in (it.winners or []):
            raise HTTPException(400, "Only winning entries are handed off.")
        if await self.repo.handoff_exists(it.id, body.idea_id):
            raise HTTPException(409, "This winner has already been sent to the backlog.")
        if len(body.statement.strip()) < MIN_HANDOFF_STATEMENT_LEN:
            raise HTTPException(400, "Problem statement needs at least 80 characters.")
        ho = IdeathonHandoff(
            ideathon_id=it.id,
            idea_id=body.idea_id,
            statement=body.statement.strip()[:3000],
            sent_by=actor.id,
            edited=body.edited,
        )
        self.session.add(ho)
        await self.session.commit()
        await self.session.refresh(ho)
        return HandoffOut.model_validate(ho)

    async def complete(self, ideathon_id: uuid.UUID, actor: Actor) -> dict:
        self._require_org(actor)
        it = await self._require(ideathon_id)
        if it.phase != "handoff":
            raise HTTPException(400, "Only an ideathon in Handoff can be completed.")
        if it.completed_at:
            raise HTTPException(409, "Already complete.")
        miss = [
            wid
            for wid in (it.winners or [])
            if not await self.repo.handoff_exists(it.id, wid)
        ]
        if miss:
            raise HTTPException(
                400, f"Send every winner to the backlog first ({len(miss)} remaining)."
            )
        it.completed_at = _now()
        await self.session.commit()
        return {"ok": True}

    async def _require(self, ideathon_id: uuid.UUID) -> Ideathon:
        it = await self.repo.get(ideathon_id)
        if not it:
            raise HTTPException(404, "Ideathon not found.")
        return it
