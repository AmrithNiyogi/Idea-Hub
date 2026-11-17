"""Seed delivery projects, tasks, updates, and impact for demo ideas.

Call after spine seed has created users + ideas in prototype/implemented::

    from app.seed.delivery import seed_delivery
    await seed_delivery(session, user_ids=..., idea_ids=...)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.delivery_constants import DEFAULT_QUARTER_POOL_HOURS
from app.models.delivery import (
    ContributionShare,
    DeliveryContributor,
    DeliveryProject,
    DeliveryTask,
    DeliveryUpdate,
    ImpactEntry,
    InnovationTimePool,
    TimeLog,
)
from app.repositories.delivery_repository import DeliveryRepository


def _quarter_key(ts: datetime | None = None) -> str:
    d = ts or datetime.now(timezone.utc)
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


async def seed_delivery(
    session: AsyncSession,
    *,
    user_ids: Mapping[str, uuid.UUID],
    idea_ids: Mapping[str, uuid.UUID],
) -> dict:
    """Create sample delivery state for a couple of keyed ideas.

    Expected optional idea keys: ``embeddings`` (implemented), ``sleepenv``
    (prototype). Missing keys are skipped.
    """
    repo = DeliveryRepository(session)
    await repo.get_or_create_pool(_quarter_key(), DEFAULT_QUARTER_POOL_HOURS)
    now = datetime.now(timezone.utc)
    created = 0

    # Implemented example
    emb = idea_ids.get("embeddings")
    tomas = user_ids.get("tomas")
    wen = user_ids.get("wen") or user_ids.get("priya")
    if emb and tomas and not await repo.get_project_by_idea(emb, with_children=False):
        project = DeliveryProject(
            idea_id=emb,
            hours_granted=40,
            started_at=now - timedelta(days=40),
            implemented_at=now - timedelta(days=10),
            outcome="Cache prototype cuts duplicate embedding calls; rolled out to staging.",
        )
        session.add(project)
        await session.flush()
        if wen and wen != tomas:
            session.add(
                DeliveryContributor(
                    project_id=project.id,
                    user_id=wen,
                    role="Builder",
                    added_by=tomas,
                    added_at=now - timedelta(days=38),
                )
            )
        for i, (title, done) in enumerate(
            [
                ("Profile duplicate embedding calls", True),
                ("Build content-hash cache", True),
                ("Roll out to CI and staging", True),
            ]
        ):
            session.add(
                DeliveryTask(
                    project_id=project.id,
                    idea_id=emb,
                    title=title,
                    status="done" if done else "not_started",
                    sort_order=i + 1,
                    created_by=tomas,
                    updated_by=tomas,
                    done_at=now - timedelta(days=20 - i) if done else None,
                    assignee_id=tomas,
                )
            )
        session.add(
            DeliveryUpdate(
                project_id=project.id,
                idea_id=emb,
                user_id=tomas,
                body="Shipped to staging and production. Hit rate holding at 78 percent.",
                created_at=now - timedelta(days=12),
            )
        )
        session.add(
            TimeLog(
                project_id=project.id,
                user_id=tomas,
                work_date=(now - timedelta(days=20)).date(),
                hours=8.0,
                note="Build and review",
            )
        )
        imp = ImpactEntry(
            project_id=project.id,
            idea_id=emb,
            impact_type="hours_saved",
            value=35,
            unit="hours per month",
            baseline=70,
            evidence="Measured from the billing export for 60 days before/after.",
            confidence="high",
            created_by=tomas,
            created_at=now - timedelta(days=10),
        )
        dana = user_ids.get("dana")
        if dana:
            imp.verified_by = dana
            imp.verified_at = now - timedelta(days=4)
            imp.verify_note = "Checked the figure against the source data export."
        session.add(imp)
        session.add(
            ContributionShare(
                project_id=project.id,
                idea_id=emb,
                user_id=tomas,
                roles=["Owner"],
                pct=60,
            )
        )
        if wen and wen != tomas:
            session.add(
                ContributionShare(
                    project_id=project.id,
                    idea_id=emb,
                    user_id=wen,
                    roles=["Builder"],
                    pct=40,
                )
            )
        created += 1

    # Live prototype example
    proto = idea_ids.get("sleepenv") or idea_ids.get("harness")
    if proto and tomas and not await repo.get_project_by_idea(proto, with_children=False):
        project = DeliveryProject(
            idea_id=proto,
            hours_granted=30,
            started_at=now - timedelta(days=14),
        )
        session.add(project)
        await session.flush()
        session.add(
            DeliveryTask(
                project_id=project.id,
                idea_id=proto,
                title="Inventory environments and usage",
                status="done",
                sort_order=1,
                created_by=tomas,
                updated_by=tomas,
                done_at=now - timedelta(days=10),
                assignee_id=tomas,
            )
        )
        session.add(
            DeliveryTask(
                project_id=project.id,
                idea_id=proto,
                title="Scheduler for sleep and wake",
                status="in_progress",
                sort_order=2,
                created_by=tomas,
                updated_by=tomas,
                assignee_id=tomas,
            )
        )
        session.add(
            DeliveryUpdate(
                project_id=project.id,
                idea_id=proto,
                user_id=tomas,
                body="Sleep schedule live on 4 of 11 environments.",
            )
        )
        created += 1

    await session.flush()
    return {"projects": created}
