"""Problem radar — average-link clustering over idea problem/tags (Phase 6).

Clusters are computed on read (threshold ~0.34). Metoo + leadership meta persist.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.phase23_auth import Actor
from app.models.idea import Idea
from app.models.problem import ProblemMeToo, ProblemMeta
from app.models.user import User
from app.schemas.problems import (
    MeTooOut,
    ProblemHeadlineOut,
    ProblemIdeaOut,
    ProblemMetaIn,
    ProblemOut,
)
from app.services.agent_heuristics import _jaccard, _words

CLUSTER_THRESHOLD = 0.34


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stable_key(idea_ids: list[uuid.UUID]) -> str:
    raw = ",".join(sorted(str(i) for i in idea_ids))
    return "prob_" + hashlib.sha1(raw.encode()).hexdigest()[:12]


class ProblemService:
    """Group similar problem statements; support metoo and sponsor meta."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _ideas(self) -> Sequence[Idea]:
        return (
            await self.session.execute(
                select(Idea).where(
                    ~Idea.status.in_(("draft", "withdrawn")),
                    Idea.submitted_at.is_not(None),
                )
            )
        ).scalars().all()

    def _features(self, idea: Idea) -> set[str]:
        return set(_words(f"{idea.title} {idea.problem}")) | {
            str(t).lower() for t in (idea.tags or [])
        }

    def _cluster(self, ideas: Sequence[Idea]) -> list[dict[str, Any]]:
        """Greedy average-link clustering; singletons excluded."""
        items = list(ideas)
        if len(items) < 2:
            return []
        feats = {i.id: self._features(i) for i in items}
        # Union-find style merge when avg link >= threshold
        parent = {i.id: i.id for i in items}

        def find(x: uuid.UUID) -> uuid.UUID:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: uuid.UUID, b: uuid.UUID) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        n = len(items)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = items[i], items[j]
                sim = _jaccard(feats[a.id], feats[b.id])
                if sim >= CLUSTER_THRESHOLD:
                    union(a.id, b.id)

        groups: dict[uuid.UUID, list[Idea]] = defaultdict(list)
        for idea in items:
            groups[find(idea.id)].append(idea)

        clusters = []
        for members in groups.values():
            if len(members) < 2:
                continue
            term_counts: dict[str, int] = defaultdict(int)
            for m in members:
                for t in feats[m.id]:
                    term_counts[t] += 1
            terms = sorted(
                term_counts.keys(),
                key=lambda t: (-term_counts[t], t),
            )[:8]
            key = _stable_key([m.id for m in members])
            clusters.append(
                {
                    "cluster_key": key,
                    "ideas": members,
                    "terms": terms,
                    "feats": feats,
                }
            )
        return clusters

    def _state(self, members: Sequence[Idea]) -> str:
        statuses = {m.status for m in members}
        if "implemented" in statuses and statuses <= {
            "implemented",
            "merged",
            "declined",
            "parked",
        }:
            # at least one implemented and no active delivery
            if not (statuses & {"accepted", "prototype", "under_review", "submitted", "needs_info"}):
                if "implemented" in statuses:
                    return "solved"
        if statuses & {"accepted", "prototype", "under_review", "submitted", "needs_info"}:
            return "in_progress"
        return "unsolved"

    def _label(self, terms: list[str], meta: Optional[ProblemMeta]) -> str:
        if meta and meta.custom_label:
            return meta.custom_label
        if terms:
            return " / ".join(terms[:3])
        return "Recurring problem"

    async def _meta_map(self) -> dict[str, ProblemMeta]:
        rows = (await self.session.execute(select(ProblemMeta))).scalars().all()
        return {r.cluster_key: r for r in rows}

    async def _me_map(self) -> dict[str, list[uuid.UUID]]:
        rows = (await self.session.execute(select(ProblemMeToo))).scalars().all()
        out: dict[str, list[uuid.UUID]] = defaultdict(list)
        for r in rows:
            out[r.cluster_key].append(r.user_id)
        return out

    async def _to_out(
        self,
        cl: dict[str, Any],
        meta: Optional[ProblemMeta],
        me_ids: list[uuid.UUID],
        viewer: Optional[uuid.UUID],
        users: dict[uuid.UUID, User],
    ) -> ProblemOut:
        members: list[Idea] = cl["ideas"]
        teams = {
            users[m.author_id].team_id
            for m in members
            if m.author_id in users and users[m.author_id].team_id and not m.anonymous
        }
        return ProblemOut(
            cluster_key=cl["cluster_key"],
            label=self._label(cl["terms"], meta),
            terms=cl["terms"],
            state=self._state(members),
            idea_count=len(members),
            me_too_count=len(me_ids),
            me_too_mine=bool(viewer and viewer in me_ids),
            team_count=len(teams),
            ideas=[
                ProblemIdeaOut(
                    id=m.id,
                    title=m.title,
                    status=m.status,
                    tags=list(m.tags or []),
                    submitted_at=m.submitted_at,
                    anonymous=m.anonymous,
                )
                for m in sorted(
                    members,
                    key=lambda x: x.submitted_at or _now(),
                    reverse=True,
                )
            ],
            sponsor_id=meta.sponsor_id if meta else None,
            acknowledged_at=meta.acknowledged_at if meta else None,
            custom_label=meta.custom_label if meta else "",
            note=meta.note if meta else "",
        )

    async def list_problems(
        self,
        actor: Actor,
        *,
        state: Optional[str] = None,
        sort: str = "raised",
    ) -> list[ProblemOut]:
        ideas = await self._ideas()
        clusters = self._cluster(ideas)
        meta_map = await self._meta_map()
        me_map = await self._me_map()
        users = {
            u.id: u
            for u in (await self.session.execute(select(User))).scalars().all()
        }
        out = []
        for cl in clusters:
            key = cl["cluster_key"]
            po = await self._to_out(
                cl, meta_map.get(key), me_map.get(key, []), actor.id, users
            )
            if state and po.state != state:
                continue
            out.append(po)

        def sort_key(p: ProblemOut) -> tuple:
            if sort == "growing":
                return (-p.idea_count, -p.me_too_count)
            if sort == "teams":
                return (-p.team_count, -p.idea_count)
            return (-p.idea_count, -p.me_too_count)

        out.sort(key=sort_key)
        return out

    async def get_problem(self, cluster_key: str, actor: Actor) -> ProblemOut:
        for p in await self.list_problems(actor):
            if p.cluster_key == cluster_key:
                return p
        raise HTTPException(status_code=404, detail="Problem cluster not found")

    async def of_idea(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> Optional[ProblemOut]:
        for p in await self.list_problems(actor):
            if any(i.id == idea_id for i in p.ideas):
                return p
        return None

    async def headline(self, actor: Actor) -> ProblemHeadlineOut:
        all_p = await self.list_problems(actor)
        since = _now() - timedelta(days=30)
        again = 0
        for p in all_p:
            if sum(1 for i in p.ideas if i.submitted_at and i.submitted_at >= since) >= 2:
                again += 1
        return ProblemHeadlineOut(
            recurring=len(all_p),
            unsolved=sum(1 for p in all_p if p.state == "unsolved"),
            again_30=again,
        )

    async def me_too(self, cluster_key: str, actor: Actor) -> MeTooOut:
        # validate cluster exists
        await self.get_problem(cluster_key, actor)
        existing = (
            await self.session.execute(
                select(ProblemMeToo).where(
                    ProblemMeToo.cluster_key == cluster_key,
                    ProblemMeToo.user_id == actor.id,
                )
            )
        ).scalar_one_or_none()
        if not existing:
            self.session.add(
                ProblemMeToo(cluster_key=cluster_key, user_id=actor.id)
            )
            await self.session.commit()
        count = len(
            (
                await self.session.execute(
                    select(ProblemMeToo).where(
                        ProblemMeToo.cluster_key == cluster_key
                    )
                )
            ).scalars().all()
        )
        return MeTooOut(
            cluster_key=cluster_key, me_too_count=count, me_too_mine=True
        )

    async def un_me_too(self, cluster_key: str, actor: Actor) -> MeTooOut:
        existing = (
            await self.session.execute(
                select(ProblemMeToo).where(
                    ProblemMeToo.cluster_key == cluster_key,
                    ProblemMeToo.user_id == actor.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.commit()
        count = len(
            (
                await self.session.execute(
                    select(ProblemMeToo).where(
                        ProblemMeToo.cluster_key == cluster_key
                    )
                )
            ).scalars().all()
        )
        return MeTooOut(
            cluster_key=cluster_key, me_too_count=count, me_too_mine=False
        )

    async def update_meta(
        self, cluster_key: str, body: ProblemMetaIn, actor: Actor
    ) -> ProblemOut:
        if not actor.has_role("leadership", "admin"):
            raise HTTPException(
                status_code=403,
                detail="Leadership or admin required to annotate problems",
            )
        await self.get_problem(cluster_key, actor)
        row = await self.session.get(ProblemMeta, cluster_key)
        if row is None:
            row = ProblemMeta(cluster_key=cluster_key)
            self.session.add(row)
        if body.custom_label is not None:
            row.custom_label = body.custom_label.strip()[:200]
        if body.sponsor_id is not None:
            row.sponsor_id = body.sponsor_id
        if body.note is not None:
            row.note = body.note
        if body.acknowledge is True:
            row.acknowledged_at = _now()
            row.acknowledged_by = actor.id
        elif body.acknowledge is False:
            row.acknowledged_at = None
            row.acknowledged_by = None
        await self.session.commit()
        return await self.get_problem(cluster_key, actor)
