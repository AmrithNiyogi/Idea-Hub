"""Insights aggregates computed from Postgres (Phase 4).

All metrics are derived from live idea/engagement/delivery/recognition rows.
No agent narrative is required for the charts; analytics agent cards are
optional and always labelled Simulated when present.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.admin_defaults import DEFAULT_POOL, DEFAULT_TIMELINES
from app.constants.strategic_themes import STRATEGIC_THEMES
from app.models.admin import PlatformSetting
from app.models.category import Category
from app.models.engagement import Comment, Vote
from app.models.idea import Idea, StatusHistory
from app.models.recognition import PointsLedgerEntry
from app.models.review import Decision
from app.models.user import Team, User
from app.schemas.insights import (
    FunnelOut,
    HoursOut,
    ImpactOut,
    InsightCardOut,
    InsightsDashboardOut,
    ParticipationOut,
    RecognitionSummaryOut,
    ReviewSpeedOut,
    ThemesOut,
)

STAGES = ["Submitted", "In review", "Decided", "Prototype", "Implemented"]
DECISION_STATUSES = {"accepted", "parked", "merged", "declined"}
LIVE_EXCLUDE = {"draft", "withdrawn"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _since(days: int) -> datetime:
    return _now() - timedelta(days=days)


def _median(vals: list[float]) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


class InsightsService:
    """Compute participation, funnel, review speed, themes, impact, hours, recognition."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _timelines(self) -> dict[str, int]:
        row = await self.session.get(PlatformSetting, "timelines")
        if row and isinstance(row.value, dict):
            return {**DEFAULT_TIMELINES, **row.value}
        return dict(DEFAULT_TIMELINES)

    async def _pool_cfg(self) -> dict[str, Any]:
        row = await self.session.get(PlatformSetting, "pool")
        if row and isinstance(row.value, dict):
            return {**DEFAULT_POOL, **row.value}
        return dict(DEFAULT_POOL)

    async def _live_ideas(self, since: Optional[datetime] = None) -> Sequence[Idea]:
        q = select(Idea).where(~Idea.status.in_(tuple(LIVE_EXCLUDE)))
        if since is not None:
            q = q.where(Idea.submitted_at.is_not(None), Idea.submitted_at >= since)
        return (await self.session.execute(q)).scalars().all()

    async def participation(self, days: int = 90) -> ParticipationOut:
        since = _since(days)
        users = (
            await self.session.execute(
                select(User).where(User.status == "active")
            )
        ).scalars().all()
        teams = (await self.session.execute(select(Team))).scalars().all()

        active_ids: set[uuid.UUID] = set()
        events: list[tuple[datetime, uuid.UUID]] = []

        votes = (
            await self.session.execute(
                select(Vote).where(Vote.created_at >= since)
            )
        ).scalars().all()
        for v in votes:
            events.append((v.created_at, v.user_id))
            active_ids.add(v.user_id)

        comments = (
            await self.session.execute(
                select(Comment).where(Comment.created_at >= since)
            )
        ).scalars().all()
        for c in comments:
            events.append((c.created_at, c.author_id))
            active_ids.add(c.author_id)

        ideas = (
            await self.session.execute(
                select(Idea).where(
                    Idea.submitted_at.is_not(None),
                    Idea.submitted_at >= since,
                    Idea.anonymous.is_(False),
                )
            )
        ).scalars().all()
        for i in ideas:
            if i.submitted_at:
                events.append((i.submitted_at, i.author_id))
                active_ids.add(i.author_id)

        prev_since = _since(days * 2)
        prev_votes = (
            await self.session.execute(
                select(Vote.user_id).where(
                    Vote.created_at >= prev_since, Vote.created_at < since
                )
            )
        ).scalars().all()
        prev_active = set(prev_votes)

        n_buckets = min(12, max(4, days // 7))
        width = (days * 86400) / n_buckets
        buckets: list[dict[str, Any]] = []
        for k in range(n_buckets):
            start = since + timedelta(seconds=k * width)
            end = start + timedelta(seconds=width)
            sids: set[uuid.UUID] = set()
            for at, uid in events:
                if start <= at < end:
                    sids.add(uid)
            buckets.append(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "n": len(sids),
                    "label": start.strftime("%b %d"),
                }
            )

        by_team = []
        for t in teams:
            members = [u for u in users if u.team_id == t.id]
            a = sum(1 for u in members if u.id in active_ids)
            by_team.append(
                {
                    "team_id": str(t.id),
                    "team_name": t.name,
                    "size": len(members),
                    "active": a,
                    "pct": round(100 * a / len(members)) if members else 0,
                }
            )
        by_team.sort(key=lambda x: (-x["pct"], x["team_name"]))

        total = len(users)
        return ParticipationOut(
            days=days,
            active=len(active_ids),
            total=total,
            pct=round(100 * len(active_ids) / total) if total else 0,
            prev_active=len(prev_active),
            by_team=by_team,
            buckets=buckets,
        )

    async def funnel(self, days: int = 90) -> FunnelOut:
        since = _since(days)
        ideas = await self._live_ideas(since)
        hist_rows = (
            await self.session.execute(
                select(StatusHistory).where(
                    StatusHistory.idea_id.in_([i.id for i in ideas] or [uuid.uuid4()])
                )
            )
        ).scalars().all()
        ever: dict[uuid.UUID, set[str]] = defaultdict(set)
        for h in hist_rows:
            ever[h.idea_id].add(h.to_status)

        out = [0, 0, 0, 0, 0]
        accepted = 0
        accepted_impl = 0
        for i in ideas:
            e = ever.get(i.id, set())
            decided = bool(e & DECISION_STATUSES) or i.status in DECISION_STATUSES
            out[0] += 1
            if i.picked_up_at or "needs_info" in e or decided or "prototype" in e:
                out[1] += 1
            if decided:
                out[2] += 1
            if "prototype" in e or i.status == "prototype":
                out[3] += 1
            if "implemented" in e or i.status == "implemented":
                out[4] += 1
            if "accepted" in e or i.status == "accepted":
                accepted += 1
                if "implemented" in e or i.status == "implemented":
                    accepted_impl += 1

        conv = []
        for k in range(1, 5):
            conv.append(
                {
                    "from": STAGES[k - 1],
                    "to": STAGES[k],
                    "n": out[k],
                    "of": out[k - 1],
                    "pct": round(100 * out[k] / out[k - 1]) if out[k - 1] else None,
                }
            )
        return FunnelOut(
            days=days,
            counts=out,
            stages=STAGES,
            conversions=conv,
            accepted=accepted,
            accepted_impl=accepted_impl,
        )

    async def review_speed(self, days: int = 90) -> ReviewSpeedOut:
        from app.models.admin import ReviewPanel

        since = _since(days)
        tl = await self._timelines()
        decision_days = int(tl.get("decision_days", 10))
        panels = (await self.session.execute(select(ReviewPanel))).scalars().all()
        cats = {
            c.id: c
            for c in (await self.session.execute(select(Category))).scalars().all()
        }
        decisions = (
            await self.session.execute(
                select(Decision).where(
                    Decision.created_at >= since,
                    Decision.outcome != "needs_info",
                )
            )
        ).scalars().all()
        ideas = {
            i.id: i
            for i in (
                await self.session.execute(select(Idea))
            ).scalars().all()
        }

        rows = []
        for p in panels:
            cat = cats.get(p.category_id)
            panel_decs = []
            for d in decisions:
                idea = ideas.get(d.idea_id)
                if not idea or idea.category_id != p.category_id:
                    continue
                if not idea.submitted_at:
                    continue
                panel_decs.append((d, idea))
            wd = []
            within = 0
            for d, idea in panel_decs:
                delta = (d.created_at - idea.submitted_at).total_seconds() / 86400.0
                wd.append(delta)
                if delta <= decision_days:
                    within += 1
            overdue = sum(
                1
                for i in ideas.values()
                if i.category_id == p.category_id
                and i.status == "under_review"
                and i.due_at
                and i.due_at < _now()
            )
            pickup = sum(
                1
                for i in ideas.values()
                if i.category_id == p.category_id
                and i.status == "under_review"
                and not i.picked_up_at
            )
            med = _median(wd)
            rows.append(
                {
                    "panel_id": str(p.id),
                    "label": cat.label if cat else p.name,
                    "n": len(panel_decs),
                    "median": round(med, 1) if med is not None else None,
                    "timeline": decision_days,
                    "ratio": (med / decision_days) if med is not None else 0,
                    "on_time": round(100 * within / len(panel_decs))
                    if panel_decs
                    else None,
                    "overdue": overdue,
                    "pickup": pickup,
                }
            )

        bottleneck = None
        if rows:
            ranked = sorted(
                rows, key=lambda r: (-r["overdue"], -float(r["ratio"] or 0))
            )
            worst = ranked[0]
            if worst["overdue"] > 0 or (worst["ratio"] or 0) > 1:
                bottleneck = worst

        return ReviewSpeedOut(
            days=days,
            timeline_days=decision_days,
            overdue_total=sum(r["overdue"] for r in rows),
            rows=rows,
            bottleneck=bottleneck,
        )

    async def themes(self, days: int = 90) -> ThemesOut:
        since = _since(days)
        prev_since = _since(days * 2)
        live = await self._live_ideas()
        cur = [i for i in live if i.submitted_at and i.submitted_at >= since]
        prv = [
            i
            for i in live
            if i.submitted_at and prev_since <= i.submitted_at < since
        ]
        tags: dict[str, dict[str, Any]] = {}
        for i in cur:
            for t in i.tags or []:
                tags.setdefault(t, {"tag": t, "cur": 0, "prev": 0})["cur"] += 1
        for i in prv:
            for t in i.tags or []:
                tags.setdefault(t, {"tag": t, "cur": 0, "prev": 0})["prev"] += 1
        tag_list = [
            {**x, "growth": x["cur"] - x["prev"]}
            for x in tags.values()
            if x["cur"] > 0
        ]
        tag_list.sort(key=lambda x: (-x["growth"], -x["cur"], x["tag"]))
        tag_list = tag_list[:8]

        def _txt(i: Idea) -> str:
            return f"{i.title} {i.problem} {i.solution}".lower()

        themes = []
        for th in STRATEGIC_THEMES:
            words = [str(w) for w in th["words"]]  # type: ignore[index]
            c = sum(1 for i in cur if any(w in _txt(i) for w in words))
            p = sum(1 for i in prv if any(w in _txt(i) for w in words))
            themes.append(
                {
                    "id": th["id"],
                    "label": th["label"],
                    "cur": c,
                    "prev": p,
                    "growth": c - p,
                }
            )
        themes.sort(key=lambda x: (-x["growth"], -x["cur"]))
        return ThemesOut(
            days=days,
            tags=tag_list,
            themes=themes,
            cur_n=len(cur),
            prev_n=len(prv),
        )

    async def impact(self, days: int = 90) -> ImpactOut:
        since = _since(days)

        def _empty() -> dict[str, Any]:
            return {
                "hours": {"v": 0.0, "u": 0.0},
                "revenue": {"v": 0.0, "u": 0.0},
                "cost": {"v": 0.0, "u": 0.0},
                "ideas": 0,
                "entries": 0,
                "unverified_entries": 0,
            }

        period = _empty()
        all_time = _empty()
        try:
            from app.models.delivery import DeliveryProject, ImpactEntry

            entries = (await self.session.execute(select(ImpactEntry))).scalars().all()
            projects = {
                p.id: p
                for p in (
                    await self.session.execute(select(DeliveryProject))
                ).scalars().all()
            }
            for e in entries:
                proj = projects.get(e.project_id)
                impl = proj.implemented_at if proj else None
                metric = e.impact_type or "hours_saved"
                val = float(e.value or 0)
                verified = e.verified_by is not None
                bucket = (
                    "hours"
                    if "hour" in metric
                    else "revenue"
                    if "rev" in metric
                    else "cost"
                    if "cost" in metric
                    else None
                )
                targets = [all_time]
                if impl and impl >= since:
                    targets.append(period)
                for t in targets:
                    t["entries"] += 1
                    if not verified:
                        t["unverified_entries"] += 1
                    if bucket:
                        t[bucket]["v" if verified else "u"] += val
            impl_ideas = [p for p in projects.values() if p.implemented_at]
            all_time["ideas"] = len(impl_ideas)
            period["ideas"] = sum(
                1 for p in impl_ideas if p.implemented_at and p.implemented_at >= since
            )
        except Exception:  # noqa: BLE001 — delivery layer may be empty
            pass

        return ImpactOut(days=days, period=period, all_time=all_time)

    async def hours(self) -> HoursOut:
        pool = await self._pool_cfg()
        quarterly = int(pool.get("quarterly_hours", 450))
        granted = 0
        logged = 0
        by_idea: list[dict[str, Any]] = []
        try:
            from app.models.delivery import DeliveryProject, TimeLog

            projects = (
                await self.session.execute(select(DeliveryProject))
            ).scalars().all()
            for p in projects:
                g = int(getattr(p, "hours_granted", 0) or 0)
                granted += g
                logs = (
                    await self.session.execute(
                        select(func.coalesce(func.sum(TimeLog.hours), 0.0)).where(
                            TimeLog.project_id == p.id
                        )
                    )
                ).scalar_one()
                logged += float(logs or 0)
                by_idea.append(
                    {
                        "idea_id": str(p.idea_id),
                        "granted": g,
                        "logged": float(logs or 0),
                    }
                )
            by_idea.sort(key=lambda x: -x["granted"])
            by_idea = by_idea[:6]
        except Exception:  # noqa: BLE001
            pass
        remaining = max(0, quarterly - granted)
        return HoursOut(
            quarterly_hours=quarterly,
            remaining=remaining,
            granted=granted,
            logged=int(round(logged)),
            by_idea=by_idea,
        )

    async def recognition_summary(self, days: int = 90) -> RecognitionSummaryOut:
        since = _since(days)
        rows = (
            await self.session.execute(
                select(PointsLedgerEntry).where(
                    PointsLedgerEntry.created_at >= since,
                    PointsLedgerEntry.escrow.is_(False),
                )
            )
        ).scalars().all()
        dims = {"quality": 0, "collab": 0, "delivery": 0, "impact": 0}
        # Best-effort dim mapping from rule_id prefixes / known rules
        dim_map = {
            "submit": "quality",
            "accepted": "quality",
            "prototype": "delivery",
            "implemented": "delivery",
            "dedupe": "collab",
            "helpful": "collab",
            "volunteer": "collab",
            "review_ontime": "quality",
            "pitch_finalist": "quality",
            "pitch_winner": "quality",
            "ioq": "impact",
            "impact": "impact",
        }
        team_pts: dict[uuid.UUID, int] = defaultdict(int)
        users = {
            u.id: u
            for u in (await self.session.execute(select(User))).scalars().all()
        }
        teams = {
            t.id: t
            for t in (await self.session.execute(select(Team))).scalars().all()
        }
        total = 0
        for r in rows:
            total += r.points
            dim = dim_map.get(r.rule_id, "quality")
            if dim in dims:
                dims[dim] += r.points
            u = users.get(r.user_id)
            if u and u.team_id:
                team_pts[u.team_id] += r.points
        by_team = [
            {
                "team_id": str(tid),
                "team_name": teams[tid].name if tid in teams else "?",
                "pts": pts,
                "size": sum(1 for u in users.values() if u.team_id == tid),
            }
            for tid, pts in team_pts.items()
        ]
        by_team.sort(key=lambda x: -x["pts"])
        return RecognitionSummaryOut(
            days=days,
            total=total,
            rows=len(rows),
            dims=dims,
            by_team=by_team,
        )

    async def cards(
        self,
        days: int,
        review: ReviewSpeedOut,
        participation: ParticipationOut,
        funnel: FunnelOut,
        impact: ImpactOut,
        hours: HoursOut,
        themes: ThemesOut,
    ) -> list[InsightCardOut]:
        out: list[InsightCardOut] = []
        if review.bottleneck and review.bottleneck.get("overdue", 0) > 0:
            b = review.bottleneck
            out.append(
                InsightCardOut(
                    id="bottleneck",
                    text=(
                        f"{b['label']} is the bottleneck: {b['overdue']} decision(s) "
                        f"overdue"
                        + (
                            f" and a median of {b['median']} days to decide against a "
                            f"{b['timeline']}-day timeline."
                            if b.get("median") is not None
                            else "."
                        )
                    ),
                    evidence=[f"panel:{b['panel_id']}"],
                    link="/review",
                )
            )
        if participation.pct < 50 and participation.total:
            out.append(
                InsightCardOut(
                    id="participation",
                    text=(
                        f"Participation is {participation.pct}% over {days} days "
                        f"({participation.active} of {participation.total} people)."
                    ),
                    link="/insights",
                )
            )
        if funnel.counts[0] and funnel.conversions:
            last = funnel.conversions[-1]
            if last.get("pct") is not None and last["pct"] < 20:
                out.append(
                    InsightCardOut(
                        id="funnel",
                        text=(
                            f"Only {last['pct']}% of decided ideas reach Implemented "
                            f"in this cohort ({last['n']} of {last['of']})."
                        ),
                        link="/insights",
                    )
                )
        if themes.themes:
            top = themes.themes[0]
            if top["growth"] > 0:
                out.append(
                    InsightCardOut(
                        id="theme",
                        text=(
                            f"“{top['label']}” is rising: {top['cur']} ideas this "
                            f"period vs {top['prev']} before."
                        ),
                        link="/problems",
                    )
                )
        hours_v = impact.period.get("hours", {}).get("v", 0)
        if hours_v:
            out.append(
                InsightCardOut(
                    id="impact",
                    text=(
                        f"Verified hours saved this period: {int(hours_v)}. "
                        f"Innovation pool remaining: {hours.remaining} h."
                    ),
                    link="/insights",
                )
            )
        if not out:
            out.append(
                InsightCardOut(
                    id="healthy",
                    text=(
                        "No sharp bottlenecks this period. Review speed and "
                        "participation look steady."
                    ),
                )
            )
        return out

    async def dashboard(self, days: int = 90) -> InsightsDashboardOut:
        days = max(7, min(365, days))
        participation = await self.participation(days)
        funnel = await self.funnel(days)
        review = await self.review_speed(days)
        themes = await self.themes(days)
        impact = await self.impact(days)
        hours = await self.hours()
        recognition = await self.recognition_summary(days)
        cards = await self.cards(
            days, review, participation, funnel, impact, hours, themes
        )
        return InsightsDashboardOut(
            days=days,
            participation=participation,
            funnel=funnel,
            review=review,
            themes=themes,
            impact=impact,
            hours=hours,
            recognition=recognition,
            cards=cards,
        )
