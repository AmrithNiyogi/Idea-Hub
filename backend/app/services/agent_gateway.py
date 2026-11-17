"""AgentGateway — simulated agent seam with run log + approval gates (Phase 5).

Adapter boundary for future Kompass: swap ``_execute_simulated`` for a
Kompass HTTP client without changing routers. MVP never calls live Kompass.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.admin_defaults import DEFAULT_TIMELINES
from app.constants.agent_roster import (
    AGENT_BY_ID,
    AGENT_ROSTER,
    KOMPASS_OPEN_QUESTIONS,
)
from app.dependencies.phase23_auth import Actor
from app.models.admin import PlatformSetting
from app.models.agent import AgentRun, KompassAnswer, ProposalDecision
from app.models.category import Category
from app.models.engagement import Comment, Vote
from app.models.idea import Idea
from app.schemas.agents import (
    AgentInfoOut,
    AgentRunOut,
    AgentRunRequest,
    KompassMapOut,
    PendingProposalOut,
    ProposalDecideIn,
    ProposalDecisionOut,
)
from app.services import agent_heuristics as H


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentGateway:
    """Run simulated agents, persist runs, and gate human approvals."""

    ENGINE = "mock-heuristic-v1"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def roster(self) -> list[AgentInfoOut]:
        return [
            AgentInfoOut(
                id=a["id"],
                prompt_slug=a.get("prompt_slug"),
                form=a["form"],
                purpose=a["purpose"],
                triggers=list(a["triggers"]),
                approval_default=a["approval_default"],
                never=list(a["never"]),
                simulated=True,
            )
            for a in AGENT_ROSTER
        ]

    async def run(self, body: AgentRunRequest, actor: Actor) -> AgentRunOut:
        if body.agent_id not in AGENT_BY_ID:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {body.agent_id}")
        output, summary, approval = await self._execute_simulated(body)
        meta = AGENT_BY_ID[body.agent_id]
        approval_required = bool(approval.get("required"))
        approval_role = approval.get("role") or meta.get("approval_default")
        approval_state = "pending" if approval_required else "none"
        proposal_key = approval.get("proposal_key")

        run = AgentRun(
            agent_id=body.agent_id,
            event=body.event,
            idea_id=body.idea_id,
            summary=summary,
            output=output,
            simulated=True,
            engine=self.ENGINE,
            approval_required=approval_required,
            approval_role=approval_role if approval_required else None,
            approval_state=approval_state,
            proposal_key=proposal_key,
        )
        if body.record:
            self.session.add(run)
            await self.session.commit()
            await self.session.refresh(run)
        else:
            run.id = uuid.uuid4()
            run.created_at = _now()
        return AgentRunOut.model_validate(run)

    async def _timelines(self) -> dict[str, int]:
        row = await self.session.get(PlatformSetting, "timelines")
        if row and isinstance(row.value, dict):
            return {**DEFAULT_TIMELINES, **row.value}
        return dict(DEFAULT_TIMELINES)

    async def _execute_simulated(
        self, body: AgentRunRequest
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        idea: Optional[Idea] = None
        if body.idea_id:
            idea = await self.session.get(Idea, body.idea_id)

        if body.agent_id == "idea-intelligence":
            corpus = (
                await self.session.execute(
                    select(Idea).where(Idea.status != "draft").limit(200)
                )
            ).scalars().all()
            cats = (await self.session.execute(select(Category))).scalars().all()
            draft = idea or body.context.get("draft") or body.context
            out = H.idea_intelligence(draft, corpus, cats)
            return out, "Simulated Idea Intelligence: similar ideas + completeness", {}

        if body.agent_id == "idea-enhancement":
            draft = idea or body.context.get("draft") or body.context
            out = H.enhancement(draft)
            return out, "Simulated Idea Enhancement suggestions", {
                "required": True,
                "role": "author",
                "proposal_key": f"enhance:{body.idea_id or 'draft'}:{uuid.uuid4().hex[:8]}",
            }

        if body.agent_id == "idea-optimizer":
            from app.services import agent_simulate_service as sim

            fields: dict[str, Any]
            if idea is not None:
                fields = {
                    "id": str(idea.id),
                    "title": idea.title,
                    "problem": idea.problem,
                    "solution": idea.solution,
                    "beneficiaries": idea.beneficiaries,
                    "success_metrics": idea.success_metrics,
                    "tags": list(idea.tags or []),
                    "effort": idea.effort,
                    "category_id": str(idea.category_id) if idea.category_id else None,
                }
            else:
                fields = dict(body.context.get("idea") or body.context or {})
            message = str(body.context.get("message") or "")
            out = sim.idea_optimize_turn(idea=fields, message=message)
            return out, "Simulated author Idea Optimizer turn", {}

        if body.agent_id == "review-intelligence":
            if not idea:
                raise HTTPException(status_code=400, detail="idea_id required")
            comments = (
                await self.session.execute(
                    select(Comment).where(Comment.idea_id == idea.id)
                )
            ).scalars().all()
            vote_rows = (
                await self.session.execute(
                    select(Vote).where(Vote.idea_id == idea.id)
                )
            ).scalars().all()
            votes = len(vote_rows)
            corpus = (
                await self.session.execute(select(Idea).limit(100))
            ).scalars().all()
            similar = H.similar_ideas(idea, corpus)
            out = H.review_brief(idea, comments, votes, similar)
            return out, f"Simulated reviewer brief for “{idea.title}”", {}

        if body.agent_id == "innovation-workflow":
            tl = await self._timelines()
            ideas = (
                await self.session.execute(
                    select(Idea).where(
                        Idea.status.in_(
                            (
                                "under_review",
                                "accepted",
                                "prototype",
                                "parked",
                                "needs_info",
                            )
                        )
                    )
                )
            ).scalars().all()
            stuck = H.stuck_detection(
                ideas,
                decision_days=int(tl.get("decision_days", 10)),
                stale_prototype_days=int(tl.get("stale_prototype_days", 14)),
                owner_assign_days=int(tl.get("owner_assign_days", 5)),
            )
            # Filter to idea if provided
            if body.idea_id:
                stuck = [s for s in stuck if s["idea_id"] == str(body.idea_id)]
            approval: dict[str, Any] = {}
            summary = f"Simulated workflow: {len(stuck)} stuck signal(s)"
            if stuck:
                first = stuck[0]
                key = f"workflow:{first['condition']}:{first['idea_id']}"
                approval = {
                    "required": True,
                    "role": "reviewer",
                    "proposal_key": key,
                }
                summary = first["draft_message"]
            return {"stuck": stuck, "simulated": True}, summary, approval

        if body.agent_id == "innovation-analytics":
            from app.services.insights_service import InsightsService

            dash = await InsightsService(self.session).dashboard(
                int(body.context.get("days") or 90)
            )
            out = H.analytics_narrative(dash.model_dump())
            return out, "Simulated analytics narrative", {}

        if body.agent_id == "recognition":
            return (
                {
                    "note": "Recognition points apply under published rules in Hub",
                    "nominations": [],
                    "flags": [],
                    "simulated": True,
                },
                "Simulated recognition scan (no nominations this run)",
                {},
            )

        if body.agent_id == "orchestrator":
            return (
                {
                    "routed": body.event,
                    "note": "Deterministic router only — Kompass adapter seam",
                    "simulated": True,
                },
                f"Orchestrator recorded event {body.event}",
                {},
            )

        return {"simulated": True}, f"No-op for {body.agent_id}", {}

    async def list_runs(
        self,
        *,
        limit: int = 50,
        agent_id: Optional[str] = None,
        pending_only: bool = False,
    ) -> list[AgentRunOut]:
        q = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
        if agent_id:
            q = q.where(AgentRun.agent_id == agent_id)
        if pending_only:
            q = q.where(AgentRun.approval_state == "pending")
        rows = (await self.session.execute(q)).scalars().all()
        return [AgentRunOut.model_validate(r) for r in rows]

    async def pending_proposals(self) -> list[PendingProposalOut]:
        rows = (
            await self.session.execute(
                select(AgentRun)
                .where(
                    AgentRun.approval_required.is_(True),
                    AgentRun.approval_state == "pending",
                )
                .order_by(AgentRun.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        # Filter snoozed
        out: list[PendingProposalOut] = []
        for r in rows:
            if not r.proposal_key:
                continue
            dec = (
                await self.session.execute(
                    select(ProposalDecision).where(
                        ProposalDecision.proposal_key == r.proposal_key
                    )
                )
            ).scalar_one_or_none()
            if dec and dec.snooze_until and dec.snooze_until > _now():
                continue
            if dec and dec.state in ("approved", "rejected") and not (
                dec.snooze_until and dec.snooze_until <= _now()
            ):
                # already decided (non-snooze reject)
                if dec.state == "approved" or not dec.snooze_until:
                    continue
            evidence = []
            stuck = (r.output or {}).get("stuck") or []
            for s in stuck[:3]:
                if isinstance(s, dict) and s.get("draft_message"):
                    evidence.append(s["draft_message"])
            out.append(
                PendingProposalOut(
                    proposal_key=r.proposal_key,
                    run=AgentRunOut.model_validate(r),
                    evidence=evidence,
                )
            )
        return out

    async def decide_proposal(
        self, body: ProposalDecideIn, actor: Actor
    ) -> ProposalDecisionOut:
        if not actor.has_role("reviewer", "admin", "leadership", "author"):
            # author allowed for enhancement; check run role
            pass
        run = (
            await self.session.execute(
                select(AgentRun)
                .where(AgentRun.proposal_key == body.proposal_key)
                .order_by(AgentRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if run:
            needed = (run.approval_role or "reviewer").lower()
            if needed == "author":
                # author of idea or any authenticated for draft enhancements
                if run.idea_id:
                    idea = await self.session.get(Idea, run.idea_id)
                    if idea and idea.author_id != actor.id and not actor.has_role(
                        "admin"
                    ):
                        raise HTTPException(status_code=403, detail="Author approval required")
            elif needed == "leadership":
                if not actor.has_role("leadership", "admin"):
                    raise HTTPException(status_code=403, detail="Leadership approval required")
            elif needed in ("reviewer", "admin"):
                if not actor.has_role("reviewer", "admin"):
                    raise HTTPException(status_code=403, detail="Reviewer approval required")

        state = "approved" if body.approve else "rejected"
        snooze_until = None
        if not body.approve and body.snooze_days:
            snooze_until = _now() + timedelta(days=body.snooze_days)

        existing = (
            await self.session.execute(
                select(ProposalDecision).where(
                    ProposalDecision.proposal_key == body.proposal_key
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.state = state
            existing.decided_by = actor.id
            existing.reason = body.reason
            existing.snooze_until = snooze_until
            existing.created_at = _now()
            dec = existing
        else:
            dec = ProposalDecision(
                proposal_key=body.proposal_key,
                run_id=run.id if run else None,
                state=state,
                decided_by=actor.id,
                reason=body.reason,
                snooze_until=snooze_until,
            )
            self.session.add(dec)

        if run:
            run.approval_state = state
        await self.session.commit()
        await self.session.refresh(dec)
        return ProposalDecisionOut.model_validate(dec)

    async def kompass_map(self) -> KompassMapOut:
        answers = {
            a.question_id: a
            for a in (await self.session.execute(select(KompassAnswer))).scalars().all()
        }
        questions = []
        for q in KOMPASS_OPEN_QUESTIONS:
            ans = answers.get(q["id"])
            questions.append(
                {
                    **q,
                    "answered": bool(ans.answered) if ans else False,
                    "note": ans.note if ans else "",
                }
            )
        return KompassMapOut(
            connected=False,
            notice="Not connected to Kompass",
            questions=questions,
        )

    async def answer_kompass(
        self, question_id: str, answered: bool, note: str, actor: Actor
    ) -> KompassMapOut:
        if not actor.has_role("admin"):
            raise HTTPException(status_code=403, detail="Admin required")
        ids = {q["id"] for q in KOMPASS_OPEN_QUESTIONS}
        if question_id not in ids:
            raise HTTPException(status_code=404, detail="Unknown question")
        row = await self.session.get(KompassAnswer, question_id)
        if row is None:
            row = KompassAnswer(question_id=question_id)
            self.session.add(row)
        row.answered = answered
        row.note = note
        row.answered_by = actor.id
        row.answered_at = _now()
        await self.session.commit()
        return await self.kompass_map()
