"""Recognition ledger service (Phase 3).

Append-only points ledger with rule citations, badge awards, leaderboards,
and Idea of the Quarter / Annual confirmation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.recognition_rules import (
    BADGE_DEFS,
    LEVELS,
    REC_DIMS,
    REC_RULES,
    impact_bonus_points,
    level_for_points,
)
from app.dependencies.phase23_auth import Actor
from app.models.recognition import (
    BadgeAward,
    PointsLedgerEntry,
    RecognitionAward,
    RecognitionThanks,
)
from app.models.user import User
from app.constants.recognition_rules import (
    THANKS_MAX_LEN,
    THANKS_MIN_LEN,
    THANKS_PER_GIVER_MONTH,
)
from app.repositories.recognition_repository import RecognitionRepository
from app.schemas.recognition import (
    ThanksIn,
    ThanksOut,
    AwardOut,
    BadgeAwardOut,
    BadgeOut,
    ConfirmAnnualRequest,
    ConfirmIoqRequest,
    LeaderboardRowOut,
    LedgerEntryOut,
    LevelOut,
    RulesOut,
)
from app.services.spine_bridge import SpineBridge


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _quarter_key(ts: datetime | None = None) -> str:
    d = ts or _now()
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def _sum_points(rules_pts: dict[str, int]) -> int:
    return int(sum(rules_pts.values()))


def _dims_of(rules_pts: dict[str, int]) -> dict[str, int]:
    """Points per dimension, using each rule's dimension from the published rules."""
    out: dict[str, int] = {}
    for rule_id, pts in rules_pts.items():
        dim = REC_RULES.get(rule_id, {}).get("dim")
        if dim:
            out[str(dim)] = out.get(str(dim), 0) + int(pts)
    return out


def _period_start(period: str, now: datetime) -> Optional[datetime]:
    """Start of the leaderboard window. 'all' has no start."""
    if period == "week":
        return now - timedelta(days=7)
    if period == "year":
        return datetime(now.year, 1, 1, tzinfo=timezone.utc)
    if period == "quarter":
        quarter_month = 3 * ((now.month - 1) // 3) + 1
        return datetime(now.year, quarter_month, 1, tzinfo=timezone.utc)
    return None


class RecognitionService:
    """Application service for points, badges, awards, leaderboards."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecognitionRepository(session)
        self.spine = SpineBridge(session)

    async def ensure_catalog(self) -> None:
        await self.repo.ensure_badges(list(BADGE_DEFS))

    async def rules(self) -> RulesOut:
        return RulesOut(
            rules=REC_RULES,
            levels=list(LEVELS),
            badges=[{"id": b["id"], "name": b["name"], "icon": b["icon"], "rule": b["rule"]} for b in BADGE_DEFS],
            dims=REC_DIMS,
        )

    async def add_points(
        self,
        rule_id: str,
        user_id: uuid.UUID,
        points: int,
        *,
        idea_id: Optional[uuid.UUID] = None,
        ref_key: str = "",
        ref_id: Optional[str] = None,
        note: str = "",
        escrow: bool = False,
        at: Optional[datetime] = None,
    ) -> Optional[PointsLedgerEntry]:
        """Idempotent ledger write (one row per rule+user+idea+ref_key)."""
        rule = REC_RULES.get(rule_id)
        points = int(round(points))
        if not rule or not user_id or points <= 0:
            return None
        dedupe = f"{rule_id}|{user_id}|{idea_id or ''}|{ref_key}"
        if await self.repo.find_by_dedupe(dedupe):
            return None
        cap = rule.get("cap_per_month")
        when = at or _now()
        if cap:
            n = await self.repo.monthly_rule_count(
                user_id, rule_id, when.year, when.month
            )
            if n >= int(cap):
                return None
        row = PointsLedgerEntry(
            dedupe_key=dedupe,
            user_id=user_id,
            rule_id=rule_id,
            points=points,
            idea_id=idea_id,
            ref_id=ref_id,
            note=note,
            escrow=escrow,
            created_at=when,
        )
        return await self.repo.add_ledger(row)

    async def split_equal(
        self,
        rule_id: str,
        idea_id: uuid.UUID,
        user_ids: Sequence[uuid.UUID],
        total: int,
        *,
        ref_key: str = "",
        note: str = "",
        escrow_for: Optional[set[uuid.UUID]] = None,
    ) -> None:
        ids = list(dict.fromkeys([u for u in user_ids if u]))
        if not ids:
            return
        base = total // len(ids)
        rem = total - base * len(ids)
        for u in ids:
            await self.add_points(
                rule_id,
                u,
                base + (1 if rem > 0 else 0),
                idea_id=idea_id,
                ref_key=ref_key,
                note=note,
                escrow=bool(escrow_for and u in escrow_for),
            )
            if rem > 0:
                rem -= 1

    async def split_shares(
        self,
        rule_id: str,
        idea_id: uuid.UUID,
        shares: Sequence[tuple[uuid.UUID, float]],
        total: int,
        *,
        ref_key: str = "",
        ref_id: Optional[str] = None,
        note: str = "",
    ) -> None:
        sh = [(u, p) for u, p in shares if p > 0]
        if not sh:
            return
        pct_sum = sum(p for _, p in sh) or 1.0
        raw = [(u, total * p / pct_sum) for u, p in sh]
        parts = [{"u": u, "n": int(v), "f": v - int(v)} for u, v in raw]
        left = int(round(total - sum(p["n"] for p in parts)))
        for p in sorted(parts, key=lambda x: x["f"], reverse=True):
            if left <= 0:
                break
            p["n"] += 1
            left -= 1
        for p in parts:
            await self.add_points(
                rule_id,
                p["u"],
                p["n"],
                idea_id=idea_id,
                ref_key=ref_key,
                ref_id=ref_id,
                note=note,
            )

    async def on_prototype(
        self,
        idea_id: uuid.UUID,
        owner_id: Optional[uuid.UUID],
        contributor_ids: Sequence[uuid.UUID],
    ) -> None:
        if not owner_id:
            return
        pts = int(REC_RULES["prototype"]["points"])
        await self.split_equal(
            "prototype",
            idea_id,
            [owner_id, *contributor_ids],
            pts,
            ref_key="prototype",
            note="Prototype started",
        )

    async def on_implemented(
        self,
        idea_id: uuid.UUID,
        shares: Sequence[tuple[uuid.UUID, float]],
    ) -> None:
        pts = int(REC_RULES["implemented"]["points"])
        await self.split_shares(
            "implemented",
            idea_id,
            shares,
            pts,
            ref_key="implemented",
            note="Implemented, split by contribution share",
        )
        for uid, _ in shares:
            await self.repo.award_badge(
                BadgeAward(
                    user_id=uid,
                    badge_id="closer",
                    idea_id=idea_id,
                    note="Credit on implemented idea",
                )
            )

    async def on_verified(
        self,
        idea_id: uuid.UUID,
        impact_type: str,
        value: float,
        confidence: str,
        entry_id: str,
        shares: Sequence[tuple[uuid.UUID, float]],
    ) -> None:
        pts = impact_bonus_points(
            impact_type=impact_type, value=value, confidence=confidence
        )
        await self.split_shares(
            "impact_verified",
            idea_id,
            shares,
            pts,
            ref_key=entry_id,
            ref_id=entry_id,
            note=f"{impact_type} verified ({confidence} confidence)",
        )

    async def on_pitch_results(
        self,
        ideathon_id: uuid.UUID,
        winners: Sequence[uuid.UUID],
        shortlist: Sequence[uuid.UUID],
        title: str,
        author_fn,
    ) -> None:
        """Award pitch winner/finalist points. ``author_fn(idea_id) -> list[UUID]``."""
        for idea_id in shortlist:
            authors = await author_fn(idea_id)
            win = idea_id in winners
            rule = "pitch_winner" if win else "pitch_finalist"
            await self.split_equal(
                rule,
                idea_id,
                authors,
                int(REC_RULES[rule]["points"]),
                ref_key=str(ideathon_id),
                note=("Winner of " if win else "Finalist in ") + f"“{title[:50]}”",
            )
            if win:
                for a in authors:
                    await self.repo.award_badge(
                        BadgeAward(
                            user_id=a,
                            badge_id="pitch_winner",
                            idea_id=idea_id,
                            note=f"Won {title[:60]}",
                        )
                    )

    async def ledger(
        self, user_id: uuid.UUID, actor: Actor
    ) -> list[LedgerEntryOut]:
        include_escrow = actor.id == user_id
        rows = await self.repo.ledger_for_user(
            user_id, include_escrow=include_escrow
        )
        out: list[LedgerEntryOut] = []
        for r in rows:
            rule = REC_RULES.get(r.rule_id, {})
            out.append(
                LedgerEntryOut(
                    id=r.id,
                    user_id=r.user_id,
                    rule_id=r.rule_id,
                    points=r.points,
                    idea_id=r.idea_id,
                    ref_id=r.ref_id,
                    note=r.note,
                    escrow=r.escrow,
                    claimed_at=r.claimed_at,
                    created_at=r.created_at,
                    rule_label=rule.get("label"),
                    dimension=rule.get("dim"),
                )
            )
        return out

    async def level(self, user_id: uuid.UUID) -> LevelOut:
        pts = await self.repo.public_points(user_id)
        lvl = level_for_points(pts)
        nxt = None
        for candidate in LEVELS:
            if int(candidate["min"]) > pts:
                nxt = int(candidate["min"])
                break
        return LevelOut(
            id=lvl["id"],
            name=lvl["name"],
            min=int(lvl["min"]),
            points=pts,
            next_min=nxt,
        )

    async def leaderboard(
        self, limit: int = 50, period: str = "all"
    ) -> list[LeaderboardRowOut]:
        """Points board for a period. Levels always use lifetime points."""
        now = _now()
        since = _period_start(period, now)
        period_totals = await self.repo.totals(since=since)
        lifetime = await self.repo.totals()
        ranked = sorted(
            period_totals.items(), key=lambda kv: -_sum_points(kv[1])
        )
        rank_now = {uid: i for i, (uid, _) in enumerate(ranked)}

        week_start = now - timedelta(days=7)
        week_totals = await self.repo.totals(since=week_start) if period == "all" else {}
        prev_rank: dict[uuid.UUID, int] = {}
        if period == "all":
            prev = await self.repo.totals(until=week_start)
            prev_sorted = sorted(prev.items(), key=lambda kv: -_sum_points(kv[1]))
            prev_rank = {uid: i for i, (uid, _) in enumerate(prev_sorted)}

        out: list[LeaderboardRowOut] = []
        for uid, rules_pts in ranked[:limit]:
            lvl = level_for_points(_sum_points(lifetime.get(uid, {})))
            change = None
            if period == "all" and uid in prev_rank:
                change = prev_rank[uid] - rank_now[uid]
            out.append(
                LeaderboardRowOut(
                    user_id=uid,
                    points=_sum_points(rules_pts),
                    level_id=lvl["id"],
                    level_name=lvl["name"],
                    dims=_dims_of(rules_pts),
                    week_points=_sum_points(week_totals.get(uid, {})),
                    rank_change=change,
                )
            )
        return out

    async def send_thanks(self, actor: Actor, body: ThanksIn) -> ThanksOut:
        """Written thanks: earns the recipient points, capped per giver."""
        if body.to_user_id == actor.id:
            raise HTTPException(400, "You cannot thank yourself.")
        note = body.note.strip()
        if len(note) < THANKS_MIN_LEN or len(note) > THANKS_MAX_LEN:
            raise HTTPException(
                400,
                f"Write between {THANKS_MIN_LEN} and {THANKS_MAX_LEN} characters "
                "so the thanks says what it was for.",
            )
        recipient = await self.session.get(User, body.to_user_id)
        if recipient is None:
            raise HTTPException(404, "That teammate was not found.")
        now = _now()
        if await self.repo.thanks_sent_in_month(actor.id, now.year, now.month) >= THANKS_PER_GIVER_MONTH:
            raise HTTPException(
                400, f"You have used this month's {THANKS_PER_GIVER_MONTH} thanks."
            )
        if await self.repo.thanks_between_in_month(
            actor.id, body.to_user_id, now.year, now.month
        ):
            raise HTTPException(400, "You already thanked this person this month.")
        row = await self.repo.add_thanks(
            RecognitionThanks(
                from_user_id=actor.id,
                to_user_id=body.to_user_id,
                note=note,
                created_at=now,
            )
        )
        await self.add_points(
            "thanks",
            body.to_user_id,
            int(REC_RULES["thanks"]["points"]),
            ref_key=str(row.id),
            note=f"Thanks from {actor.name or 'a teammate'}",
            at=now,
        )
        return ThanksOut(
            id=row.id,
            from_user_id=row.from_user_id,
            to_user_id=row.to_user_id,
            note=row.note,
            created_at=now,
        )

    async def recent_thanks(self, limit: int = 10) -> list[ThanksOut]:
        rows = await self.repo.recent_thanks(limit)
        return [
            ThanksOut(
                id=r.id,
                from_user_id=r.from_user_id,
                to_user_id=r.to_user_id,
                note=r.note,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def badges_catalog(self) -> list[BadgeOut]:
        await self.ensure_catalog()
        return [BadgeOut.model_validate(b) for b in await self.repo.list_badges()]

    async def user_badges(self, user_id: uuid.UUID) -> list[BadgeAwardOut]:
        await self.ensure_catalog()
        awards = await self.repo.awards_for_user(user_id)
        catalog = {b.id: b for b in await self.repo.list_badges()}
        out: list[BadgeAwardOut] = []
        for a in awards:
            b = catalog.get(a.badge_id)
            out.append(
                BadgeAwardOut(
                    badge_id=a.badge_id,
                    name=b.name if b else a.badge_id,
                    icon=b.icon if b else "",
                    awarded_at=a.awarded_at,
                    note=a.note,
                    idea_id=a.idea_id,
                )
            )
        return out

    async def confirm_ioq(
        self, body: ConfirmIoqRequest, actor: Actor
    ) -> AwardOut:
        if not actor.has_role("leadership"):
            raise HTTPException(403, "Only leadership can confirm Idea of the Quarter.")
        qk = _quarter_key()
        if body.period != qk:
            raise HTTPException(400, "Only the current quarter can be confirmed here.")
        if await self.repo.get_award_by_period("ioq", qk):
            raise HTTPException(409, f"Idea of the Quarter already confirmed for {qk}.")
        idea = await self.spine.get_idea(body.idea_id)
        if not idea:
            raise HTTPException(404, "Idea not found.")
        authors = [idea.author_id, *idea.co_author_ids]
        pts = int(REC_RULES["ioq"]["points"])
        award = RecognitionAward(
            kind="ioq",
            period=qk,
            idea_id=idea.id,
            user_ids=authors,
            nominee_ids=[str(idea.id)],
            reason=body.reason.strip(),
            points=pts,
            confirmed_by=actor.id,
        )
        await self.repo.add_award(award)
        await self.split_equal(
            "ioq",
            idea.id,
            authors,
            pts,
            ref_key=str(award.id),
            note=f"Idea of the Quarter {qk}",
        )
        for a in authors:
            await self.repo.award_badge(
                BadgeAward(
                    user_id=a,
                    badge_id="quarter_champion",
                    idea_id=idea.id,
                    note=f"IoQ {qk}",
                )
            )
        await self.session.commit()
        return AwardOut.model_validate(award)

    async def confirm_annual(
        self, body: ConfirmAnnualRequest, actor: Actor
    ) -> AwardOut:
        if not actor.has_role("leadership"):
            raise HTTPException(403, "Only leadership can confirm the Annual Award.")
        year = str(_now().year)
        if body.year != year:
            raise HTTPException(400, "Only the current year can be confirmed here.")
        if await self.repo.get_award_by_period("annual", year):
            raise HTTPException(409, f"Annual award already confirmed for {year}.")
        pts = int(REC_RULES["annual_award"]["points"])
        award = RecognitionAward(
            kind="annual",
            period=year,
            idea_id=None,
            user_ids=[body.user_id],
            nominee_ids=[str(body.user_id)],
            reason=body.reason.strip(),
            points=pts,
            confirmed_by=actor.id,
        )
        await self.repo.add_award(award)
        await self.add_points(
            "annual_award",
            body.user_id,
            pts,
            ref_key=str(award.id),
            note=f"Annual Innovation Award {year}",
        )
        await self.session.commit()
        return AwardOut.model_validate(award)

    async def list_awards(self) -> list[AwardOut]:
        return [AwardOut.model_validate(a) for a in await self.repo.list_awards()]
