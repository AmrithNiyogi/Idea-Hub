"""Collaboration requests + team progress tracker (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.phase23_auth import Actor
from app.models.collab import CollabRequest, TrackerCheckin, TrackerMilestone
from app.models.idea import Idea
from app.schemas.collab import (
    CheckinCreateIn,
    CheckinOut,
    CollabCreateIn,
    CollabDecideIn,
    CollabRequestOut,
    MilestoneCreateIn,
    MilestoneOut,
    MilestoneUpdateIn,
    TrackerOut,
)
from app.services.notification_service import notify_idea, notify_users

TRACKABLE = {"accepted", "prototype", "implemented"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CollabService:
    """Co-author / help-build requests and lightweight tracker."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_idea(self, idea_id: uuid.UUID) -> list[CollabRequestOut]:
        rows = (
            await self.session.execute(
                select(CollabRequest)
                .where(CollabRequest.idea_id == idea_id)
                .order_by(CollabRequest.created_at.asc())
            )
        ).scalars().all()
        return [CollabRequestOut.model_validate(r) for r in rows]

    async def list_mine(self, actor: Actor) -> list[CollabRequestOut]:
        rows = (
            await self.session.execute(
                select(CollabRequest)
                .where(CollabRequest.from_user_id == actor.id)
                .order_by(CollabRequest.created_at.desc())
            )
        ).scalars().all()
        return [CollabRequestOut.model_validate(r) for r in rows]

    async def list_incoming(self, actor: Actor) -> list[CollabRequestOut]:
        """Pending requests on ideas the actor owns or authored."""
        ideas = (
            await self.session.execute(
                select(Idea).where(
                    (Idea.author_id == actor.id) | (Idea.owner_id == actor.id)
                )
            )
        ).scalars().all()
        ids = [i.id for i in ideas]
        if not ids:
            return []
        rows = (
            await self.session.execute(
                select(CollabRequest)
                .where(
                    CollabRequest.idea_id.in_(ids),
                    CollabRequest.status == "pending",
                )
                .order_by(CollabRequest.created_at.desc())
            )
        ).scalars().all()
        return [CollabRequestOut.model_validate(r) for r in rows]

    async def create(
        self, body: CollabCreateIn, actor: Actor
    ) -> CollabRequestOut:
        idea = await self.session.get(Idea, body.idea_id)
        if not idea or idea.status in ("draft", "withdrawn"):
            raise HTTPException(status_code=404, detail="Idea not found")
        if idea.author_id == actor.id:
            raise HTTPException(
                status_code=400, detail="You already own this idea as author"
            )
        existing = (
            await self.session.execute(
                select(CollabRequest).where(
                    CollabRequest.idea_id == idea.id,
                    CollabRequest.from_user_id == actor.id,
                    CollabRequest.status == "pending",
                    CollabRequest.type == body.type,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Pending request already exists")
        row = CollabRequest(
            idea_id=idea.id,
            from_user_id=actor.id,
            type=body.type,
            message=body.message.strip(),
            role=body.role.strip(),
            hours=body.hours,
            status="pending",
            source=body.source,
        )
        self.session.add(row)
        parties = [idea.author_id]
        if idea.owner_id:
            parties.append(idea.owner_id)
        await notify_users(
            self.session,
            parties,
            kind="collab",
            text=(
                f'{actor.name} requested to {body.type} on “{idea.title}”.'
            ),
            href=f"/ideas/{idea.id}?tab=collab",
            idea_id=idea.id,
            idea_title=idea.title,
            exclude=actor.id,
            meta={"event": "collab_request", "type": body.type},
        )
        await self.session.commit()
        await self.session.refresh(row)
        return CollabRequestOut.model_validate(row)

    async def withdraw(
        self, request_id: uuid.UUID, actor: Actor
    ) -> CollabRequestOut:
        row = await self.session.get(CollabRequest, request_id)
        if not row or row.from_user_id != actor.id or row.status != "pending":
            raise HTTPException(status_code=400, detail="No pending request to withdraw")
        row.status = "withdrawn"
        row.decided_at = _now()
        row.decided_by = actor.id
        await self.session.commit()
        await self.session.refresh(row)
        return CollabRequestOut.model_validate(row)

    async def decide(
        self, request_id: uuid.UUID, body: CollabDecideIn, actor: Actor
    ) -> CollabRequestOut:
        row = await self.session.get(CollabRequest, request_id)
        if not row or row.status != "pending":
            raise HTTPException(status_code=400, detail="Request already answered")
        idea = await self.session.get(Idea, row.idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        can = (
            idea.author_id == actor.id
            or idea.owner_id == actor.id
            or actor.has_role("admin")
        )
        if not can:
            raise HTTPException(
                status_code=403, detail="Only author/owner can decide"
            )
        row.status = "accepted" if body.accept else "declined"
        row.note = body.note
        row.decided_at = _now()
        row.decided_by = actor.id
        if body.accept and row.type == "coauthor":
            cos = list(idea.co_author_ids or [])
            uid = str(row.from_user_id)
            if uid not in [str(x) for x in cos]:
                cos.append(uid)
                idea.co_author_ids = cos
                # Soft update via raw SQL if JSONB assignment quirks
                try:
                    await self.session.execute(
                        text(
                            "UPDATE ideas SET co_author_ids = CAST(:c AS jsonb) "
                            "WHERE id = :id"
                        ),
                        {"c": __import__("json").dumps(cos), "id": idea.id},
                    )
                except Exception:  # noqa: BLE001
                    pass
        verb = "accepted" if body.accept else "declined"
        await notify_users(
            self.session,
            [row.from_user_id],
            kind="collab",
            text=(
                f'{actor.name} {verb} your {row.type} request on “{idea.title}”.'
            ),
            href=f"/ideas/{idea.id}",
            idea_id=idea.id,
            idea_title=idea.title,
            exclude=actor.id,
            meta={"event": "collab_decision", "accepted": body.accept},
        )
        # Followers also see collab outcomes (subscription); skip parties already emailed
        await notify_idea(
            self.session,
            idea,
            kind="collab",
            text=f'A {row.type} request on “{idea.title}” was {verb}.',
            href=f"/ideas/{idea.id}",
            exclude=[actor.id, row.from_user_id],
            send_email=False,
            meta={"event": "collab_decision_broadcast"},
        )
        await self.session.commit()
        await self.session.refresh(row)
        return CollabRequestOut.model_validate(row)

    async def tracker(self, idea_id: uuid.UUID) -> TrackerOut:
        milestones = (
            await self.session.execute(
                select(TrackerMilestone)
                .where(TrackerMilestone.idea_id == idea_id)
                .order_by(
                    TrackerMilestone.sort_order.asc(),
                    TrackerMilestone.created_at.asc(),
                )
            )
        ).scalars().all()
        checkins = (
            await self.session.execute(
                select(TrackerCheckin)
                .where(TrackerCheckin.idea_id == idea_id)
                .order_by(TrackerCheckin.created_at.desc())
                .limit(40)
            )
        ).scalars().all()
        now = _now()
        blocked = sum(1 for m in milestones if m.status == "blocked")
        overdue = sum(
            1
            for m in milestones
            if m.due_at
            and m.due_at < now
            and m.status not in ("done",)
        )
        return TrackerOut(
            idea_id=idea_id,
            milestones=[MilestoneOut.model_validate(m) for m in milestones],
            checkins=[CheckinOut.model_validate(c) for c in checkins],
            blocked_count=blocked,
            overdue_count=overdue,
        )

    async def add_milestone(
        self, idea_id: uuid.UUID, body: MilestoneCreateIn, actor: Actor
    ) -> MilestoneOut:
        idea = await self.session.get(Idea, idea_id)
        if not idea or idea.status not in TRACKABLE:
            raise HTTPException(
                status_code=400,
                detail="Tracker only for accepted/prototype/implemented ideas",
            )
        if not (
            idea.owner_id == actor.id
            or idea.author_id == actor.id
            or actor.has_role("lead", "admin")
        ):
            raise HTTPException(status_code=403, detail="Not allowed")
        row = TrackerMilestone(
            idea_id=idea_id,
            title=body.title.strip(),
            owner_id=body.owner_id,
            due_at=body.due_at,
            sort_order=body.sort_order,
            created_by=actor.id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return MilestoneOut.model_validate(row)

    async def update_milestone(
        self,
        milestone_id: uuid.UUID,
        body: MilestoneUpdateIn,
        actor: Actor,
    ) -> MilestoneOut:
        row = await self.session.get(TrackerMilestone, milestone_id)
        if not row:
            raise HTTPException(status_code=404, detail="Milestone not found")
        idea = await self.session.get(Idea, row.idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        if not (
            idea.owner_id == actor.id
            or idea.author_id == actor.id
            or row.owner_id == actor.id
            or actor.has_role("lead", "admin")
        ):
            raise HTTPException(status_code=403, detail="Not allowed")
        for field in ("title", "status", "owner_id", "due_at", "blocker", "sort_order"):
            val = getattr(body, field)
            if val is not None:
                setattr(row, field, val)
        if body.status == "done":
            row.done_at = _now()
        await self.session.commit()
        await self.session.refresh(row)
        return MilestoneOut.model_validate(row)

    async def add_checkin(
        self, idea_id: uuid.UUID, body: CheckinCreateIn, actor: Actor
    ) -> CheckinOut:
        idea = await self.session.get(Idea, idea_id)
        if not idea or idea.status not in TRACKABLE:
            raise HTTPException(status_code=400, detail="Idea not trackable")
        row = TrackerCheckin(
            idea_id=idea_id,
            author_id=actor.id,
            body=body.body.strip(),
            percent_complete=body.percent_complete,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return CheckinOut.model_validate(row)
