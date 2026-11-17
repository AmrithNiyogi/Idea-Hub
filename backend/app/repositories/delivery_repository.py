"""Persistence helpers for delivery entities.

SQL strategy: keyed lookups by ``idea_id`` / ``project_id`` with indexes
declared on the models. Pending hour requests use a filtered status scan
scoped to one idea (expected cardinality 0–1).
"""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.delivery import (
    ContributionShare,
    DeliveryContributor,
    DeliveryProject,
    DeliveryTask,
    DeliveryUpdate,
    ImpactEntry,
    InnovationTimePool,
    TimeGrantRequest,
    TimeLog,
)


class DeliveryRepository:
    """Repository for delivery projects, grants, tasks, updates, impact."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_project_by_idea(
        self, idea_id: uuid.UUID, *, with_children: bool = True
    ) -> Optional[DeliveryProject]:
        stmt: Select[tuple[DeliveryProject]] = select(DeliveryProject).where(
            DeliveryProject.idea_id == idea_id
        )
        if with_children:
            stmt = stmt.options(
                selectinload(DeliveryProject.hour_logs),
                selectinload(DeliveryProject.tasks),
                selectinload(DeliveryProject.updates),
                selectinload(DeliveryProject.contributors),
                selectinload(DeliveryProject.impact_entries),
                selectinload(DeliveryProject.shares),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project(
        self, project_id: uuid.UUID
    ) -> Optional[DeliveryProject]:
        result = await self.session.execute(
            select(DeliveryProject)
            .where(DeliveryProject.id == project_id)
            .options(
                selectinload(DeliveryProject.hour_logs),
                selectinload(DeliveryProject.tasks),
                selectinload(DeliveryProject.updates),
                selectinload(DeliveryProject.contributors),
                selectinload(DeliveryProject.impact_entries),
                selectinload(DeliveryProject.shares),
            )
        )
        return result.scalar_one_or_none()

    async def add_project(self, project: DeliveryProject) -> DeliveryProject:
        self.session.add(project)
        await self.session.flush()
        return project

    async def pending_request(
        self, idea_id: uuid.UUID
    ) -> Optional[TimeGrantRequest]:
        result = await self.session.execute(
            select(TimeGrantRequest).where(
                TimeGrantRequest.idea_id == idea_id,
                TimeGrantRequest.state == "pending",
            )
        )
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        *,
        state: str | None = None,
        limit: int = 50,
    ) -> list[TimeGrantRequest]:
        """Return hours requests newest-first, optionally filtered by state."""
        q = select(TimeGrantRequest).order_by(TimeGrantRequest.created_at.desc())
        if state:
            q = q.where(TimeGrantRequest.state == state)
        q = q.limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_request(
        self, request_id: uuid.UUID
    ) -> Optional[TimeGrantRequest]:
        result = await self.session.execute(
            select(TimeGrantRequest).where(TimeGrantRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def add_request(self, req: TimeGrantRequest) -> TimeGrantRequest:
        self.session.add(req)
        await self.session.flush()
        return req

    async def hours_logged_total(self, project_id: uuid.UUID) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(TimeLog.hours), 0.0)).where(
                TimeLog.project_id == project_id
            )
        )
        return float(result.scalar_one())

    async def granted_in_period(self, period_start, period_end) -> int:
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(TimeGrantRequest.granted_hours), 0)
            ).where(
                TimeGrantRequest.state == "approved",
                TimeGrantRequest.decided_at >= period_start,
                TimeGrantRequest.decided_at < period_end,
            )
        )
        return int(result.scalar_one())

    async def get_or_create_pool(
        self, period_key: str, budget: int
    ) -> InnovationTimePool:
        result = await self.session.execute(
            select(InnovationTimePool).where(
                InnovationTimePool.period_key == period_key
            )
        )
        pool = result.scalar_one_or_none()
        if pool:
            return pool
        pool = InnovationTimePool(period_key=period_key, budget_hours=budget)
        self.session.add(pool)
        await self.session.flush()
        return pool

    async def get_task(self, task_id: uuid.UUID) -> Optional[DeliveryTask]:
        result = await self.session.execute(
            select(DeliveryTask).where(DeliveryTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(self, idea_id: uuid.UUID) -> Sequence[DeliveryTask]:
        result = await self.session.execute(
            select(DeliveryTask)
            .where(DeliveryTask.idea_id == idea_id)
            .order_by(DeliveryTask.sort_order, DeliveryTask.created_at)
        )
        return result.scalars().all()

    async def get_impact(
        self, entry_id: uuid.UUID
    ) -> Optional[ImpactEntry]:
        result = await self.session.execute(
            select(ImpactEntry).where(ImpactEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def max_task_order(self, project_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(DeliveryTask.sort_order), 0)).where(
                DeliveryTask.project_id == project_id
            )
        )
        return int(result.scalar_one())
