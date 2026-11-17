"""Reopen conditions for parked/declined ideas (Phase 6).

Agents propose; reviewers/admins approve. Approving moves the idea back
to under_review and restarts the review clock using admin timelines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.admin_defaults import DEFAULT_TIMELINES
from app.dependencies.phase23_auth import Actor
from app.models.admin import PlatformSetting, ReviewPanel
from app.models.agent import ProposalDecision
from app.models.engagement import Vote
from app.models.idea import Idea, StatusHistory
from app.models.reopen import ReopenConditionSet
from app.models.review import Decision
from app.schemas.reopen import (
    CondEvalOut,
    MarkManualIn,
    ReopenDecideIn,
    ReopenProposalOut,
    ReopenSetIn,
    ReopenStateOut,
)
from app.services.problem_service import ProblemService

DEP_RANK = {"accepted": 1, "prototype": 2, "implemented": 3}
REOPEN_SNOOZE_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReopenService:
    """Create, evaluate, approve, and dismiss reopen condition sets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _timelines(self) -> dict[str, int]:
        row = await self.session.get(PlatformSetting, "timelines")
        if row and isinstance(row.value, dict):
            return {**DEFAULT_TIMELINES, **row.value}
        return dict(DEFAULT_TIMELINES)

    async def can_approve(self, actor: Actor, idea: Idea) -> bool:
        if actor.has_role("admin"):
            return True
        if not actor.has_role("reviewer"):
            return False
        if not idea.category_id:
            return True
        panel = (
            await self.session.execute(
                select(ReviewPanel).where(
                    ReviewPanel.category_id == idea.category_id
                )
            )
        ).scalar_one_or_none()
        if not panel:
            return True
        members = {str(x) for x in (panel.member_ids or [])}
        return str(actor.id) in members

    async def upsert_set(self, body: ReopenSetIn, actor: Actor) -> ReopenStateOut:
        if not actor.has_role("reviewer", "admin"):
            raise HTTPException(status_code=403, detail="Reviewer required")
        idea = await self.session.get(Idea, body.idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        if idea.status not in ("parked", "declined"):
            raise HTTPException(
                status_code=400,
                detail="Reopen conditions only apply to parked or declined ideas",
            )
        conds: list[dict[str, Any]] = []
        for i, c in enumerate(body.conds[:6]):
            d: dict[str, Any] = {
                "id": f"cond_{i}",
                "type": c.type,
            }
            if c.type == "date":
                if not c.due_at or c.due_at <= _now():
                    raise HTTPException(status_code=400, detail="date must be in the future")
                d["due_at"] = c.due_at.isoformat()
            elif c.type == "raised":
                d["n"] = int(c.n or 1)
            elif c.type == "dependency":
                d["idea_id"] = str(c.idea_id)
                d["status"] = c.status or "accepted"
            elif c.type == "capacity":
                d["hours"] = int(c.hours or 1)
            elif c.type == "demand":
                d["mode"] = c.mode if c.mode in ("problem", "votes") else "votes"
                d["n"] = int(c.n or 1)
            elif c.type == "manual":
                text = (c.text or "").strip()
                if len(text) < 10:
                    raise HTTPException(
                        status_code=400, detail="manual text must be ≥ 10 chars"
                    )
                d["text"] = text
                d["met_at"] = None
                d["met_by"] = None
                d["note"] = ""
            else:
                raise HTTPException(status_code=400, detail=f"Unknown type {c.type}")
            conds.append(d)

        if idea.status == "parked" and body.revisit_at:
            conds.insert(
                0,
                {
                    "id": "cond_revisit",
                    "type": "date",
                    "due_at": body.revisit_at.isoformat(),
                },
            )
            idea.revisit_at = body.revisit_at

        if idea.status == "parked" and not conds:
            raise HTTPException(
                status_code=400, detail="Parked ideas need at least one reopen condition"
            )

        existing = (
            await self.session.execute(
                select(ReopenConditionSet).where(
                    ReopenConditionSet.idea_id == idea.id
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.conds = conds
            existing.rule = "all" if body.rule == "all" else "any"
            existing.decision_id = body.decision_id
            existing.closed_at = None
            existing.closed_by = None
            existing.close_reason = ""
            row = existing
        else:
            row = ReopenConditionSet(
                idea_id=idea.id,
                decision_id=body.decision_id,
                rule="all" if body.rule == "all" else "any",
                conds=conds,
                created_by=actor.id,
            )
            self.session.add(row)
        await self.session.commit()
        return await self.state_for(idea.id)

    async def _eval_cond(
        self, c: dict[str, Any], idea: Idea, dec: Optional[Decision]
    ) -> CondEvalOut:
        now = _now()
        t = c.get("type")
        met = False
        frac = 0.0
        progress = ""
        evidence = ""
        impossible = False
        label = ""

        if t == "date":
            due = datetime.fromisoformat(str(c["due_at"]).replace("Z", "+00:00"))
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            met = due <= now
            frac = 1.0 if met else max(0.0, min(0.95, 1 - (due - now).days / 60))
            label = f"On {due.date().isoformat()}"
            progress = "Date reached" if met else f"Due {due.date().isoformat()}"
            evidence = f"Revisit date {due.date().isoformat()} reached"

        elif t == "raised":
            n = int(c.get("n") or 1)
            label = f"When {n} more idea(s) join the same problem"
            # Approximate: count sibling ideas in same cluster submitted after decision
            at = dec.created_at if dec else idea.updated_at
            joined = 0
            try:
                cluster = await ProblemService(self.session).of_idea(
                    idea.id,
                    Actor(id=idea.author_id, roles=["admin"], active_role="admin"),
                )
                if cluster:
                    joined = sum(
                        1
                        for x in cluster.ideas
                        if x.id != idea.id
                        and x.submitted_at
                        and at
                        and x.submitted_at > at
                    )
            except Exception:  # noqa: BLE001
                joined = 0
            met = joined >= n
            frac = min(1.0, joined / n)
            progress = f"{min(joined, n)} of {n} more ideas"
            evidence = f"{joined} more idea(s) joined the problem"

        elif t == "dependency":
            dep_id = uuid.UUID(str(c["idea_id"]))
            want = c.get("status") or "accepted"
            label = f"Dependency reaches {want}"
            dep = await self.session.get(Idea, dep_id)
            if not dep:
                impossible = True
                progress = "Dependency idea missing"
            else:
                have = DEP_RANK.get(dep.status, 0)
                need = DEP_RANK.get(want, 1)
                met = have >= need
                frac = 1.0 if met else have / max(need, 1) * 0.8
                if not met and dep.status in ("declined", "merged", "withdrawn"):
                    impossible = True
                progress = f"“{dep.title[:50]}” is {dep.status}"
                evidence = progress

        elif t == "capacity":
            hours = int(c.get("hours") or 1)
            label = f"Pool has ≥ {hours} hours left"
            # Best-effort remaining from insights hours
            from app.services.insights_service import InsightsService

            h = await InsightsService(self.session).hours()
            rem = h.remaining
            met = rem >= hours
            frac = min(1.0, rem / hours) if hours else 0
            progress = f"{min(rem, hours)} of {hours} hours"
            evidence = f"Pool remaining {rem} h"

        elif t == "demand":
            mode = c.get("mode") or "votes"
            n = int(c.get("n") or 1)
            if mode == "problem":
                label = f"When {n} people say metoo"
                count = 0
                try:
                    cluster = await ProblemService(self.session).of_idea(
                        idea.id,
                        Actor(id=idea.author_id, roles=["admin"], active_role="admin"),
                    )
                    if cluster:
                        count = cluster.me_too_count
                except Exception:  # noqa: BLE001
                    count = 0
                met = count >= n
                frac = min(1.0, count / n)
                progress = f"{min(count, n)} of {n} people"
                evidence = f"{count} metoo"
            else:
                label = f"When idea reaches {n} upvotes"
                votes = len(
                    (
                        await self.session.execute(
                            select(Vote).where(Vote.idea_id == idea.id)
                        )
                    ).scalars().all()
                )
                met = votes >= n
                frac = min(1.0, votes / n)
                progress = f"{min(votes, n)} of {n} upvotes"
                evidence = f"{votes} upvotes"

        elif t == "manual":
            label = str(c.get("text") or "Manual condition")
            met = bool(c.get("met_at"))
            frac = 1.0 if met else 0.0
            progress = "Confirmed" if met else "Waiting for confirmation"
            evidence = progress

        else:
            label = f"Unknown ({t})"
            progress = "Unknown condition type"

        return CondEvalOut(
            cond=c,
            label=label,
            met=met,
            frac=frac,
            progress=progress,
            evidence=evidence,
            impossible=impossible,
        )

    async def _get_set(self, idea: Idea) -> Optional[tuple[ReopenConditionSet | dict, bool]]:
        """Return (set_or_derived_dict, derived)."""
        if idea.status not in ("parked", "declined"):
            return None
        row = (
            await self.session.execute(
                select(ReopenConditionSet).where(
                    ReopenConditionSet.idea_id == idea.id,
                    ReopenConditionSet.closed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row:
            return row, False
        if idea.status == "parked" and idea.revisit_at:
            return (
                {
                    "rule": "any",
                    "conds": [
                        {
                            "id": "derived_date",
                            "type": "date",
                            "due_at": idea.revisit_at.isoformat(),
                        }
                    ],
                    "closed_at": None,
                },
                True,
            )
        return None

    async def state_for(self, idea_id: uuid.UUID) -> ReopenStateOut:
        idea = await self.session.get(Idea, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        got = await self._get_set(idea)
        if not got:
            raise HTTPException(status_code=404, detail="No reopen conditions")
        aset, derived = got
        rule = aset.rule if isinstance(aset, ReopenConditionSet) else aset["rule"]
        conds = aset.conds if isinstance(aset, ReopenConditionSet) else aset["conds"]
        closed = bool(
            isinstance(aset, ReopenConditionSet) and aset.closed_at
        )
        dec = (
            await self.session.execute(
                select(Decision)
                .where(Decision.idea_id == idea.id)
                .order_by(Decision.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        items = [await self._eval_cond(c, idea, dec) for c in conds]
        met_n = sum(1 for x in items if x.met)
        satisfied = all(x.met for x in items) if rule == "all" else met_n > 0
        close = (
            (sum(x.frac for x in items) / len(items))
            if rule == "all" and items
            else (max((x.frac for x in items), default=0.0))
        )
        key = f"reopen:{idea.id}:{dec.id if dec else 'x'}"
        snooze = None
        pd = (
            await self.session.execute(
                select(ProposalDecision).where(ProposalDecision.proposal_key == key)
            )
        ).scalar_one_or_none()
        if (
            pd
            and pd.state == "rejected"
            and pd.snooze_until
            and pd.snooze_until > _now()
        ):
            snooze = pd.snooze_until
        evidence = [
            x.evidence
            for x in (items if rule == "all" else [x for x in items if x.met])
            if x.evidence
        ]
        return ReopenStateOut(
            idea_id=idea.id,
            rule=rule,
            satisfied=satisfied and not closed,
            met=met_n,
            total=len(items),
            close=round(close, 3),
            derived=derived,
            items=items,
            evidence=evidence,
            snoozed_until=snooze,
            closed=closed,
        )

    async def proposals(self) -> list[ReopenProposalOut]:
        ideas = (
            await self.session.execute(
                select(Idea).where(Idea.status.in_(("parked", "declined")))
            )
        ).scalars().all()
        out: list[ReopenProposalOut] = []
        for idea in ideas:
            try:
                st = await self.state_for(idea.id)
            except HTTPException:
                continue
            if not st.satisfied or st.snoozed_until:
                continue
            dec = (
                await self.session.execute(
                    select(Decision)
                    .where(Decision.idea_id == idea.id)
                    .order_by(Decision.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            key = f"reopen:{idea.id}:{dec.id if dec else 'x'}"
            out.append(
                ReopenProposalOut(
                    proposal_key=key,
                    idea_id=idea.id,
                    idea_title=idea.title,
                    evidence=st.evidence,
                    state=st,
                )
            )
        return out

    async def mark_manual(
        self, idea_id: uuid.UUID, body: MarkManualIn, actor: Actor
    ) -> ReopenStateOut:
        if not actor.has_role("reviewer", "leadership", "admin"):
            raise HTTPException(status_code=403, detail="Not allowed to mark conditions")
        row = (
            await self.session.execute(
                select(ReopenConditionSet).where(
                    ReopenConditionSet.idea_id == idea_id,
                    ReopenConditionSet.closed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="No reopen set")
        conds = list(row.conds or [])
        found = False
        for c in conds:
            if c.get("id") == body.cond_id and c.get("type") == "manual":
                c["met_at"] = _now().isoformat()
                c["met_by"] = str(actor.id)
                c["note"] = body.note
                found = True
        if not found:
            raise HTTPException(status_code=404, detail="Manual condition not found")
        row.conds = conds
        await self.session.commit()
        return await self.state_for(idea_id)

    async def approve(
        self, idea_id: uuid.UUID, body: ReopenDecideIn, actor: Actor
    ) -> dict[str, Any]:
        idea = await self.session.get(Idea, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        if not await self.can_approve(actor, idea):
            raise HTTPException(status_code=403, detail="Not allowed to reopen")
        st = await self.state_for(idea_id)
        if not st.satisfied:
            raise HTTPException(status_code=400, detail="Conditions are not met")
        was = idea.status
        why = body.reason.strip() or "Conditions met"
        tl = await self._timelines()
        idea.status = "under_review"
        idea.revisit_at = None
        idea.picked_up_at = _now()
        idea.reviewer_id = actor.id
        idea.paused_at = None
        idea.stage_entered_at = _now()
        idea.due_at = _now() + timedelta(days=int(tl.get("decision_days", 10)))
        idea.pickup_due_at = _now() + timedelta(days=int(tl.get("pickup_days", 3)))
        self.session.add(
            StatusHistory(
                idea_id=idea.id,
                from_status=was,
                to_status="under_review",
                actor_id=actor.id,
                reason=f"Reopened after being {was}: {why}",
            )
        )
        # mark history with reopened via reason prefix already; close set
        row = (
            await self.session.execute(
                select(ReopenConditionSet).where(
                    ReopenConditionSet.idea_id == idea.id,
                    ReopenConditionSet.closed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row:
            row.closed_at = _now()
            row.closed_by = actor.id
            row.close_reason = why

        dec = (
            await self.session.execute(
                select(Decision)
                .where(Decision.idea_id == idea.id)
                .order_by(Decision.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        key = f"reopen:{idea.id}:{dec.id if dec else 'x'}"
        existing_pd = (
            await self.session.execute(
                select(ProposalDecision).where(ProposalDecision.proposal_key == key)
            )
        ).scalar_one_or_none()
        if existing_pd:
            existing_pd.state = "approved"
            existing_pd.decided_by = actor.id
            existing_pd.reason = why
            existing_pd.snooze_until = None
        else:
            self.session.add(
                ProposalDecision(
                    proposal_key=key,
                    state="approved",
                    decided_by=actor.id,
                    reason=why,
                )
            )
        await self.session.commit()
        return {"ok": True, "idea_id": str(idea.id), "status": idea.status}

    async def dismiss(
        self, idea_id: uuid.UUID, body: ReopenDecideIn, actor: Actor
    ) -> dict[str, Any]:
        idea = await self.session.get(Idea, idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        if not await self.can_approve(actor, idea):
            raise HTTPException(status_code=403, detail="Not allowed to dismiss")
        snooze_days = body.snooze_days or REOPEN_SNOOZE_DAYS
        dec = (
            await self.session.execute(
                select(Decision)
                .where(Decision.idea_id == idea.id)
                .order_by(Decision.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        key = f"reopen:{idea.id}:{dec.id if dec else 'x'}"
        existing = (
            await self.session.execute(
                select(ProposalDecision).where(ProposalDecision.proposal_key == key)
            )
        ).scalar_one_or_none()
        snooze_until = _now() + timedelta(days=snooze_days)
        if existing:
            existing.state = "rejected"
            existing.decided_by = actor.id
            existing.reason = body.reason or "Dismissed"
            existing.snooze_until = snooze_until
        else:
            self.session.add(
                ProposalDecision(
                    proposal_key=key,
                    state="rejected",
                    decided_by=actor.id,
                    reason=body.reason or "Dismissed",
                    snooze_until=snooze_until,
                )
            )
        await self.session.commit()
        return {
            "ok": True,
            "snoozed_until": snooze_until.isoformat(),
            "idea_id": str(idea.id),
        }
