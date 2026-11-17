"""Delivery domain service (Phase 2).

Implements innovation-hours request/approve, hours log, tasks, updates,
mark-implemented + impact verify — mirroring idea-hub.html ``api.delivery.*``.

Side effects:
- Creates ``DeliveryProject`` and moves idea to ``prototype`` on approve.
- Moves idea to ``implemented`` on mark-implemented.
- Invokes recognition hooks for prototype / implemented / verify events.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.delivery_constants import (
    CONTRIB_ROLES,
    DEFAULT_QUARTER_POOL_HOURS,
    IMPACT_TYPES,
    MIN_JUSTIFICATION_LEN,
    TASK_STATUSES,
)
from app.dependencies.phase23_auth import Actor
from app.models.delivery import (
    ContributionShare,
    DeliveryContributor,
    DeliveryProject,
    DeliveryTask,
    DeliveryUpdate,
    ImpactEntry,
    TimeGrantRequest,
    TimeLog,
)
from app.repositories.delivery_repository import DeliveryRepository
from app.schemas.delivery import (
    ContributorAdd,
    ContributorOut,
    DeliveryDetailOut,
    DeliveryUpdateCreate,
    DeliveryUpdateOut,
    HoursDecideRequest,
    HoursLogCreate,
    HoursRequestCreate,
    HoursRequestOut,
    ImpactEntryOut,
    MarkImplementedRequest,
    PoolOut,
    ShareOut,
    TaskCreate,
    TaskOut,
    TaskStatusUpdate,
    TaskUpdate,
    TimeLogOut,
    VerifyImpactRequest,
)
from app.models.user import User
from app.services.notification_service import notify_idea, notify_users
from app.services.spine_bridge import SpineBridge


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _quarter_key(ts: datetime | None = None) -> str:
    d = ts or _now()
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def _quarter_bounds(key: str) -> tuple[datetime, datetime]:
    year_s, q_s = key.split("-Q")
    year, q = int(year_s), int(q_s)
    start = datetime(year, (q - 1) * 3 + 1, 1, tzinfo=timezone.utc)
    if q == 4:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, q * 3 + 1, 1, tzinfo=timezone.utc)
    return start, end


class DeliveryService:
    """Application service for the Delivery tab on an idea."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DeliveryRepository(session)
        self.spine = SpineBridge(session)

    async def get_delivery(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> DeliveryDetailOut:
        idea = await self._require_idea(idea_id)
        project = await self.repo.get_project_by_idea(idea_id)
        pending = await self.repo.pending_request(idea_id)
        pool = await self._pool_out()
        if not project:
            return DeliveryDetailOut(
                idea_id=idea_id,
                pending_request=(
                    HoursRequestOut.model_validate(pending) if pending else None
                ),
                pool=pool,
            )
        logged = await self.repo.hours_logged_total(project.id)
        return DeliveryDetailOut(
            idea_id=idea_id,
            project_id=project.id,
            hours_granted=project.hours_granted,
            hours_logged=logged,
            started_at=project.started_at,
            implemented_at=project.implemented_at,
            outcome=project.outcome or "",
            pending_request=(
                HoursRequestOut.model_validate(pending) if pending else None
            ),
            hour_logs=[TimeLogOut.model_validate(x) for x in project.hour_logs],
            tasks=[
                TaskOut.model_validate(x)
                for x in sorted(project.tasks, key=lambda t: t.sort_order)
            ],
            updates=[
                DeliveryUpdateOut.model_validate(x)
                for x in sorted(
                    project.updates, key=lambda u: u.created_at, reverse=True
                )
            ],
            contributors=[
                ContributorOut.model_validate(x) for x in project.contributors
            ],
            impact=[ImpactEntryOut.model_validate(x) for x in project.impact_entries],
            shares=[ShareOut.model_validate(x) for x in project.shares],
            pool=pool,
        )

    async def request_hours(
        self, idea_id: uuid.UUID, body: HoursRequestCreate, actor: Actor
    ) -> HoursRequestOut:
        idea = await self._require_idea(idea_id)
        if idea.status != "accepted":
            raise HTTPException(400, "Hours can be requested only for an accepted idea.")
        if not idea.owner_id:
            raise HTTPException(400, "Assign an owner before requesting hours.")
        if not (
            idea.owner_id == actor.id
            or actor.has_role("lead", "admin", "leadership")
        ):
            raise HTTPException(
                403, "Only the owner, a team lead or an administrator can request hours."
            )
        if await self.repo.pending_request(idea_id):
            raise HTTPException(409, "A request for this idea is already waiting for leadership.")
        if len(body.justification.strip()) < MIN_JUSTIFICATION_LEN:
            raise HTTPException(400, "Give a short justification (at least 10 characters).")
        req = TimeGrantRequest(
            idea_id=idea_id,
            requested_by=actor.id,
            hours=body.hours,
            justification=body.justification.strip(),
            state="pending",
        )
        await self.repo.add_request(req)
        leaders = (
            await self.session.execute(
                select(User.id).where(
                    User.roles.contains(["leadership"])
                    | User.roles.contains(["admin"])
                )
            )
        ).scalars().all()
        await notify_users(
            self.session,
            list(leaders),
            kind="hours",
            text=(
                f'{actor.name} requested {body.hours} innovation hours for '
                f'“{idea.title}”. Your decision is needed.'
            ),
            href="/approvals",
            idea_id=idea_id,
            idea_title=idea.title,
            exclude=actor.id,
            meta={"event": "hours_request"},
        )
        await self.session.commit()
        return HoursRequestOut.model_validate(req)

    async def list_hours_requests(
        self, actor: Actor, *, state: str | None = None, limit: int = 50
    ) -> list[HoursRequestOut]:
        """Inbox of innovation-hour requests for leadership Approvals."""
        if not actor.has_role("leadership", "admin"):
            raise HTTPException(
                403, "Only leadership or admin can list hours requests."
            )
        rows = await self.repo.list_requests(state=state, limit=limit)
        return [HoursRequestOut.model_validate(r) for r in rows]

    async def decide_hours(
        self, request_id: uuid.UUID, body: HoursDecideRequest, actor: Actor
    ) -> dict:
        if not actor.has_role("leadership", "admin"):
            raise HTTPException(403, "Only leadership or admin can decide hours.")
        req = await self.repo.get_request(request_id)
        if not req or req.state != "pending":
            raise HTTPException(404, "This request is no longer pending.")
        if req.requested_by == actor.id:
            raise HTTPException(
                403, "You made this request, so another leader must decide it."
            )
        idea = await self._require_idea(req.idea_id)
        if idea.status != "accepted" or not idea.owner_id:
            raise HTTPException(400, "This idea is no longer waiting for hours.")

        if not body.approve:
            if len((body.reason or "").strip()) < 10:
                raise HTTPException(400, "A reason is required when declining.")
            req.state = "declined"
            req.decided_by = actor.id
            req.decided_at = _now()
            req.reason = body.reason.strip()
            parties = [req.requested_by]
            if idea.owner_id:
                parties.append(idea.owner_id)
            await notify_users(
                self.session,
                parties,
                kind="hours",
                text=(
                    f'{actor.name} declined the {req.hours} hour request for '
                    f'“{idea.title}”: {req.reason[:160]}'
                ),
                href=f"/ideas/{idea.id}?tab=delivery",
                idea_id=idea.id,
                idea_title=idea.title,
                exclude=actor.id,
                meta={"event": "hours_declined"},
            )
            await notify_idea(
                self.session,
                idea,
                kind="hours",
                text=f'Innovation hours for “{idea.title}” were declined.',
                href=f"/ideas/{idea.id}?tab=delivery",
                exclude=[actor.id, req.requested_by, idea.owner_id],
                send_email=False,
            )
            await self.session.commit()
            return {"state": "declined"}

        hours = body.hours if body.hours is not None else req.hours
        pool = await self._pool_out()
        if hours > pool.remaining and not body.override:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        f"This is {hours - pool.remaining} hours more than the "
                        f"pool has left ({max(0, pool.remaining)} remaining)."
                    ),
                    "needs_override": True,
                    "remaining": pool.remaining,
                },
            )

        req.state = "approved"
        req.decided_by = actor.id
        req.decided_at = _now()
        req.granted_hours = hours
        req.override = hours > pool.remaining
        req.reason = (body.reason or "").strip()

        existing = await self.repo.get_project_by_idea(req.idea_id, with_children=False)
        if existing:
            raise HTTPException(409, "Delivery project already exists for this idea.")

        project = DeliveryProject(
            idea_id=req.idea_id,
            hours_granted=hours,
            started_at=_now(),
        )
        await self.repo.add_project(project)
        await self.spine.set_idea_status(
            req.idea_id,
            "prototype",
            actor_id=actor.id,
            reason=f"Innovation hours granted ({hours} h).",
        )
        await self._recog().on_prototype(req.idea_id, idea.owner_id, [])
        await notify_idea(
            self.session,
            idea,
            kind="hours",
            text=(
                f'“{idea.title}” moved to Prototype: {hours} innovation hours '
                "granted."
            ),
            href=f"/ideas/{idea.id}?tab=delivery",
            exclude=actor.id,
            extra=[req.requested_by],
            meta={"event": "hours_approved", "hours": hours},
        )
        await self.session.commit()
        return {
            "state": "approved",
            "hours": hours,
            "overrode": req.override,
            "project_id": str(project.id),
        }

    async def log_hours(
        self, idea_id: uuid.UUID, body: HoursLogCreate, actor: Actor
    ) -> dict:
        project = await self._require_active_project(idea_id)
        await self._require_edit_access(idea_id, actor, manage=False)
        if body.work_date > date.today():
            raise HTTPException(400, "The date cannot be in the future.")
        started = project.started_at.date() if project.started_at else date.min
        if body.work_date < started:
            raise HTTPException(
                400, f"This is before the prototype started on {started.isoformat()}."
            )
        entry = TimeLog(
            project_id=project.id,
            user_id=actor.id,
            work_date=body.work_date,
            hours=body.hours,
            note=body.note.strip()[:200],
        )
        self.session.add(entry)
        await self.session.flush()
        logged = await self.repo.hours_logged_total(project.id)
        await self.session.commit()
        return {
            "logged": logged,
            "granted": project.hours_granted,
            "over": logged > project.hours_granted,
            "over_by": max(0.0, logged - project.hours_granted),
        }

    async def add_contributor(
        self, idea_id: uuid.UUID, body: ContributorAdd, actor: Actor
    ) -> dict:
        project = await self._require_active_project(idea_id)
        await self._require_edit_access(idea_id, actor, manage=True)
        if body.role not in CONTRIB_ROLES:
            raise HTTPException(400, f"Role must be one of {', '.join(CONTRIB_ROLES)}.")
        idea = await self._require_idea(idea_id)
        if body.user_id in {idea.author_id, idea.owner_id, *idea.co_author_ids}:
            raise HTTPException(400, "This person is already credited on this idea.")
        if any(c.user_id == body.user_id for c in project.contributors):
            raise HTTPException(400, "Already a contributor.")
        self.session.add(
            DeliveryContributor(
                project_id=project.id,
                user_id=body.user_id,
                role=body.role,
                added_by=actor.id,
            )
        )
        await notify_users(
            self.session,
            [body.user_id],
            kind="collab",
            text=(
                f'{actor.name} added you as {body.role} on “{idea.title}”. '
                "You can use the Team and progress tab."
            ),
            href=f"/ideas/{idea.id}?tab=team",
            idea_id=idea_id,
            idea_title=idea.title,
            exclude=actor.id,
            meta={"event": "contributor_added"},
        )
        await self.session.commit()
        return {"ok": True}

    async def remove_contributor(
        self, idea_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
    ) -> dict:
        project = await self._require_active_project(idea_id)
        await self._require_edit_access(idea_id, actor, manage=True)
        match = next((c for c in project.contributors if c.user_id == user_id), None)
        if not match:
            raise HTTPException(404, "That person is not a contributor.")
        idea = await self._require_idea(idea_id)
        await self.session.delete(match)
        await notify_users(
            self.session,
            [user_id],
            kind="collab",
            text=(
                f'{actor.name} removed you from the delivery team on '
                f'“{idea.title}”.'
            ),
            href=f"/ideas/{idea.id}",
            idea_id=idea_id,
            idea_title=idea.title,
            exclude=actor.id,
            meta={"event": "contributor_removed"},
        )
        await self.session.commit()
        return {"ok": True}

    async def add_task(
        self, idea_id: uuid.UUID, body: TaskCreate, actor: Actor
    ) -> TaskOut:
        project = await self._require_active_project(idea_id)
        await self._require_edit_access(idea_id, actor, manage=False)
        if body.status not in TASK_STATUSES:
            raise HTTPException(400, f"Invalid status. Use one of {TASK_STATUSES}.")
        order = await self.repo.max_task_order(project.id) + 1
        task = DeliveryTask(
            project_id=project.id,
            idea_id=idea_id,
            title=body.title.strip(),
            description=body.description or "",
            assignee_id=body.assignee_id,
            due_at=body.due_at,
            status=body.status,
            sort_order=order,
            created_by=actor.id,
            updated_by=actor.id,
            done_at=_now() if body.status == "done" else None,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return TaskOut.model_validate(task)

    async def update_task(
        self, task_id: uuid.UUID, body: TaskUpdate, actor: Actor
    ) -> TaskOut:
        task = await self.repo.get_task(task_id)
        if not task:
            raise HTTPException(404, "Task not found.")
        await self._require_edit_access(task.idea_id, actor, manage=False)
        if body.title is not None:
            task.title = body.title.strip()
        if body.description is not None:
            task.description = body.description
        if body.assignee_id is not None:
            task.assignee_id = body.assignee_id
        if body.due_at is not None:
            task.due_at = body.due_at
        if body.status is not None:
            await self._apply_task_status(task, body.status, body.blocker or "", actor)
        elif body.blocker is not None:
            task.blocker = body.blocker
        task.updated_by = actor.id
        await self.session.commit()
        await self.session.refresh(task)
        return TaskOut.model_validate(task)

    async def set_task_status(
        self, task_id: uuid.UUID, body: TaskStatusUpdate, actor: Actor
    ) -> TaskOut:
        task = await self.repo.get_task(task_id)
        if not task:
            raise HTTPException(404, "Task not found.")
        await self._require_edit_access(task.idea_id, actor, manage=False)
        await self._apply_task_status(task, body.status, body.blocker, actor)
        task.updated_by = actor.id
        await self.session.commit()
        await self.session.refresh(task)
        return TaskOut.model_validate(task)

    async def post_update(
        self, idea_id: uuid.UUID, body: DeliveryUpdateCreate, actor: Actor
    ) -> dict:
        project = await self._require_active_project(idea_id)
        await self._require_edit_access(idea_id, actor, manage=False)
        upd = DeliveryUpdate(
            project_id=project.id,
            idea_id=idea_id,
            user_id=actor.id,
            body=body.body.strip(),
            task_id=body.task_id,
        )
        self.session.add(upd)
        await self.session.commit()
        return {"id": str(upd.id)}

    async def mark_implemented(
        self, idea_id: uuid.UUID, body: MarkImplementedRequest, actor: Actor
    ) -> dict:
        project = await self._require_active_project(idea_id)
        await self._require_edit_access(idea_id, actor, manage=True)
        if project.implemented_at:
            raise HTTPException(409, "Already marked implemented.")
        for e in body.impact:
            if e.impact_type not in IMPACT_TYPES:
                raise HTTPException(400, f"Unknown impact type: {e.impact_type}")
            unit = e.unit or IMPACT_TYPES[e.impact_type]["unit"]
            self.session.add(
                ImpactEntry(
                    project_id=project.id,
                    idea_id=idea_id,
                    impact_type=e.impact_type,
                    value=e.value,
                    unit=unit,
                    baseline=e.baseline,
                    evidence=e.evidence.strip(),
                    confidence=e.confidence,
                    created_by=actor.id,
                )
            )
        for s in body.shares:
            self.session.add(
                ContributionShare(
                    project_id=project.id,
                    idea_id=idea_id,
                    user_id=s.user_id,
                    roles=s.roles,
                    pct=s.pct,
                )
            )
        project.outcome = body.outcome.strip()
        project.implemented_at = _now()
        await self.spine.set_idea_status(
            idea_id,
            "implemented",
            actor_id=actor.id,
            reason=f"Marked implemented. {body.outcome.strip()[:160]}",
        )
        await self._recog().on_implemented(
            idea_id, [(s.user_id, s.pct) for s in body.shares]
        )
        idea = await self._require_idea(idea_id)
        credited = [s.user_id for s in body.shares]
        await notify_users(
            self.session,
            credited,
            kind="implemented",
            text=(
                f'“{idea.title}” was marked implemented. '
                "You are credited on this contribution."
            ),
            href=f"/ideas/{idea.id}?tab=delivery",
            idea_id=idea_id,
            idea_title=idea.title,
            exclude=actor.id,
            send_email=False,
        )
        await notify_idea(
            self.session,
            idea,
            kind="implemented",
            text=f'“{idea.title}” was marked implemented.',
            href=f"/ideas/{idea.id}?tab=delivery",
            exclude=[actor.id, *credited],
            send_email=False,
        )
        await self.session.commit()
        return {"ok": True, "credits": len(body.shares)}

    async def verify_impact(
        self,
        idea_id: uuid.UUID,
        entry_id: uuid.UUID,
        body: VerifyImpactRequest,
        actor: Actor,
    ) -> dict:
        idea = await self._require_idea(idea_id)
        project = await self.repo.get_project_by_idea(idea_id)
        if not project:
            raise HTTPException(404, "This idea has no delivery record.")
        entry = await self.repo.get_impact(entry_id)
        if not entry or entry.idea_id != idea_id:
            raise HTTPException(404, "That impact entry no longer exists.")
        if entry.verified_at:
            raise HTTPException(409, "Already verified.")
        if entry.created_by == actor.id:
            raise HTTPException(403, "A second person must verify impact.")
        if not actor.has_role("lead", "leadership", "admin", "reviewer"):
            # owner of another idea / leadership preferred; allow lead+
            if idea.owner_id == actor.id:
                raise HTTPException(403, "Owner cannot verify their own impact.")
        entry.verified_by = actor.id
        entry.verified_at = _now()
        entry.verify_note = body.note.strip()[:300]
        shares = [(s.user_id, s.pct) for s in project.shares]
        await self._recog().on_verified(
            idea_id,
            entry.impact_type,
            entry.value,
            entry.confidence,
            str(entry.id),
            shares,
        )
        impact_label = IMPACT_TYPES.get(entry.impact_type, {}).get(
            "label", entry.impact_type
        )
        await notify_idea(
            self.session,
            idea,
            kind="impact",
            text=(
                f'Impact on “{idea.title}” was verified by {actor.name}: '
                f"{str(impact_label).lower()}."
            ),
            href=f"/ideas/{idea.id}?tab=delivery",
            exclude=actor.id,
            send_email=False,
        )
        await self.session.commit()
        return {"entry_id": str(entry.id), "idea_id": str(idea_id)}

    # ---- internals ----

    async def _pool_out(self) -> PoolOut:
        key = _quarter_key()
        pool = await self.repo.get_or_create_pool(key, DEFAULT_QUARTER_POOL_HOURS)
        start, end = _quarter_bounds(key)
        granted = await self.repo.granted_in_period(start, end)
        return PoolOut(
            period_key=key,
            budget_hours=pool.budget_hours,
            granted_hours=granted,
            remaining=max(0, pool.budget_hours - granted),
        )

    async def _require_idea(self, idea_id: uuid.UUID) -> Any:
        idea = await self.spine.get_idea(idea_id)
        if not idea:
            raise HTTPException(
                404,
                "Idea not found (spine ideas table missing or id unknown).",
            )
        return idea

    async def _require_active_project(self, idea_id: uuid.UUID) -> DeliveryProject:
        project = await self.repo.get_project_by_idea(idea_id)
        if not project:
            raise HTTPException(404, "No delivery project — hours not granted yet.")
        if project.implemented_at:
            # allow read/verify paths separately; mutate paths check explicitly
            pass
        return project

    async def _require_edit_access(
        self, idea_id: uuid.UUID, actor: Actor, *, manage: bool
    ) -> None:
        idea = await self._require_idea(idea_id)
        project = await self.repo.get_project_by_idea(idea_id)
        is_owner = idea.owner_id == actor.id
        is_contrib = bool(
            project
            and any(c.user_id == actor.id for c in project.contributors)
        )
        if manage:
            if not (
                is_owner or actor.has_role("lead", "admin", "leadership")
            ):
                raise HTTPException(
                    403,
                    "Only the owner, a team lead or an administrator can do this.",
                )
        else:
            if not (
                is_owner
                or is_contrib
                or actor.has_role("lead", "admin", "leadership")
            ):
                raise HTTPException(
                    403,
                    "Only accepted team members, a team lead or an administrator can edit delivery.",
                )

    async def _apply_task_status(
        self, task: DeliveryTask, status_value: str, blocker: str, actor: Actor
    ) -> None:
        if status_value not in TASK_STATUSES:
            raise HTTPException(400, f"Invalid status. Use one of {TASK_STATUSES}.")
        task.status = status_value
        task.blocker = blocker if status_value == "blocked" else ""
        task.done_at = _now() if status_value == "done" else None
        task.blocked_at = _now() if status_value == "blocked" else None

    def _recog(self) -> Any:
        from app.services.recognition_service import RecognitionService

        return RecognitionService(self.session)
