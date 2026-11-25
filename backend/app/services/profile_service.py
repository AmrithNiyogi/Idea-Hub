"""Profile views (Phase 3) — thin projections over ideas + recognition data."""

from __future__ import annotations

import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.recognition_rules import REC_RULES
from app.dependencies.phase23_auth import Actor
from app.models.delivery import (
    ContributionShare,
    DeliveryContributor,
    DeliveryProject,
    ImpactEntry,
)
from app.models.review import Decision
from app.repositories.recognition_repository import RecognitionRepository
from app.schemas.profiles import (
    ContributionEventOut,
    ImpactSummaryOut,
    ProfileIdeaRef,
    ProfileOut,
)
from app.services.recognition_service import RecognitionService
from app.services.spine_bridge import SpineBridge


class ProfileService:
    """Assemble a person profile from shared domain tables."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.spine = SpineBridge(session)
        self.recog = RecognitionService(session)
        self.recog_repo = RecognitionRepository(session)

    async def get_profile(self, user_id: uuid.UUID, actor: Actor) -> ProfileOut:
        user = await self.spine.get_user(user_id)
        if not user and actor.id != user_id:
            raise HTTPException(404, "User not found.")

        level = await self.recog.level(user_id)
        badges = await self.recog.user_badges(user_id)
        is_self = actor.id == user_id
        ledger = await self.recog.ledger(user_id, actor)

        dims = {"quality": 0, "collab": 0, "delivery": 0, "impact": 0}
        for row in ledger:
            if row.escrow and not is_self:
                continue
            dim = row.dimension or REC_RULES.get(row.rule_id, {}).get("dim")
            if dim in dims:
                dims[dim] += row.points

        idea_rows = await self.spine.ideas_for_author(user_id)
        submitted: list[ProfileIdeaRef] = []
        co_authored: list[ProfileIdeaRef] = []
        implemented: list[ProfileIdeaRef] = []
        history: list[ContributionEventOut] = []

        for row in idea_rows:
            iid = row["id"]
            title = row.get("title") or ""
            status = row.get("status") or ""
            author_id = row.get("author_id")
            owner_id = row.get("owner_id")
            co = row.get("co_author_ids") or []
            if isinstance(co, str):
                co = json.loads(co)
            co_ids = [
                c if isinstance(c, uuid.UUID) else uuid.UUID(str(c)) for c in co
            ]
            if author_id == user_id and status != "draft":
                submitted.append(
                    ProfileIdeaRef(
                        id=iid, title=title, status=status, role="author"
                    )
                )
            if user_id in co_ids:
                co_authored.append(
                    ProfileIdeaRef(
                        id=iid, title=title, status=status, role="co_author"
                    )
                )
            if status == "implemented" and (
                author_id == user_id
                or owner_id == user_id
                or user_id in co_ids
            ):
                role = "owner" if owner_id == user_id else "author"
                if user_id in co_ids and author_id != user_id:
                    role = "co_author"
                implemented.append(
                    ProfileIdeaRef(
                        id=iid, title=title, status=status, role=role
                    )
                )

        contrib_result = await self.session.execute(
            select(DeliveryContributor, DeliveryProject)
            .join(
                DeliveryProject,
                DeliveryContributor.project_id == DeliveryProject.id,
            )
            .where(DeliveryContributor.user_id == user_id)
        )
        for c, project in contrib_result.all():
            idea = await self.spine.get_idea(project.idea_id)
            history.append(
                ContributionEventOut(
                    at=c.added_at,
                    role="Contributor",
                    idea_id=project.idea_id,
                    idea_title=idea.title if idea else "",
                    extra=c.role,
                )
            )

        # Reviewer activity: every decision this person recorded, as a history entry.
        decisions = await self.session.execute(
            select(Decision).where(Decision.decider_id == user_id)
        )
        for d in decisions.scalars().all():
            idea = await self.spine.get_idea(d.idea_id)
            history.append(
                ContributionEventOut(
                    at=d.created_at,
                    role="Reviewer",
                    idea_id=d.idea_id,
                    idea_title=idea.title if idea else "",
                    extra=d.outcome,
                )
            )

        history.sort(key=lambda h: h.at, reverse=True)
        impact = await self._impact_summary(user_id)

        return ProfileOut(
            user_id=user_id,
            name=user.name if user else None,
            title=user.title if user else None,
            team_id=user.team_id if user else None,
            roles=list(user.roles) if user else [],
            points=level.points,
            level=level,
            badges=badges,
            submitted=submitted,
            co_authored=co_authored,
            implemented=implemented,
            impact=impact,
            ledger=ledger[:50],
            history=history[:100],
            dims=dims,
            is_self=is_self,
        )

    async def _impact_summary(self, user_id: uuid.UUID) -> ImpactSummaryOut:
        result = await self.session.execute(
            select(ContributionShare).where(ContributionShare.user_id == user_id)
        )
        shares = result.scalars().all()
        hours = hours_v = usd = 0.0
        ideas: set[uuid.UUID] = set()
        for sh in shares:
            ideas.add(sh.idea_id)
            imp = await self.session.execute(
                select(ImpactEntry).where(ImpactEntry.idea_id == sh.idea_id)
            )
            for e in imp.scalars().all():
                share = sh.pct / 100.0
                if e.impact_type == "hours_saved":
                    hours += e.value * share
                    if e.verified_at:
                        hours_v += e.value * share
                elif e.impact_type in {"cost_avoided", "revenue"}:
                    usd += e.value * share
        return ImpactSummaryOut(
            hours_saved=round(hours, 1),
            hours_verified=round(hours_v, 1),
            usd_influenced=round(usd, 0),
            ideas_credited=len(ideas),
        )
