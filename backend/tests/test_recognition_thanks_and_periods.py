"""Written thanks caps and leaderboard period windows.

Runs against an in-memory fake repository, so no database is touched.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.constants.recognition_rules import REC_RULES, THANKS_PER_GIVER_MONTH
from app.dependencies.phase23_auth import Actor
from app.schemas.recognition import ThanksIn
from app.services import recognition_service as rs

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
ALICE = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
BEN = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
CARA = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
DAN = uuid.UUID("dddddddd-0000-0000-0000-000000000004")
NOTE = "Reviewed my idea within a day and asked the question that made it stronger."


class FakeRepo:
    """Keeps ledger entries and thanks in memory and filters them like the SQL does."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.thanks: list[Any] = []

    def add_entry(self, user_id, rule_id, points, created_at, escrow=False) -> None:
        self.entries.append(
            {"user_id": user_id, "rule_id": rule_id, "points": points,
             "created_at": created_at, "escrow": escrow}
        )

    async def totals(self, *, since=None, until=None):
        out: dict[uuid.UUID, dict[str, int]] = {}
        for e in self.entries:
            if e["escrow"]:
                continue
            if since is not None and e["created_at"] < since:
                continue
            if until is not None and e["created_at"] >= until:
                continue
            rules = out.setdefault(e["user_id"], {})
            rules[e["rule_id"]] = rules.get(e["rule_id"], 0) + e["points"]
        return out

    async def thanks_sent_in_month(self, from_user_id, year, month) -> int:
        return sum(
            1 for t in self.thanks
            if t.from_user_id == from_user_id
            and t.created_at.year == year and t.created_at.month == month
        )

    async def thanks_between_in_month(self, from_user_id, to_user_id, year, month) -> int:
        return sum(
            1 for t in self.thanks
            if t.from_user_id == from_user_id and t.to_user_id == to_user_id
            and t.created_at.year == year and t.created_at.month == month
        )

    async def add_thanks(self, row):
        if row.id is None:
            row.id = uuid.uuid4()
        self.thanks.append(row)
        return row

    async def recent_thanks(self, limit):
        return list(reversed(self.thanks))[:limit]


def _service(monkeypatch, repo: FakeRepo | None = None) -> tuple[rs.RecognitionService, FakeRepo]:
    monkeypatch.setattr(rs, "_now", lambda: NOW)
    session = MagicMock()
    session.get = AsyncMock(
        side_effect=lambda model, uid: SimpleNamespace(id=uid, name="Teammate")
        if uid in (BEN, CARA, DAN) else None
    )
    svc = rs.RecognitionService(session)
    fake = repo or FakeRepo()
    svc.repo = fake  # type: ignore[assignment]
    svc.add_points = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return svc, fake


def _actor(uid: uuid.UUID = ALICE) -> Actor:
    return Actor(id=uid, name="Alice")


# ---- thanks caps -----------------------------------------------------------

@pytest.mark.asyncio
async def test_cannot_thank_yourself(monkeypatch) -> None:
    svc, _ = _service(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await svc.send_thanks(_actor(), ThanksIn(to_user_id=ALICE, note=NOTE))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_note_must_be_at_least_twenty_characters(monkeypatch) -> None:
    svc, _ = _service(monkeypatch)
    with pytest.raises(HTTPException) as short:
        await svc.send_thanks(_actor(), ThanksIn(to_user_id=BEN, note="x" * 19))
    assert short.value.status_code == 400
    ok = await svc.send_thanks(_actor(), ThanksIn(to_user_id=BEN, note="x" * 20))
    assert ok.to_user_id == BEN


def test_note_longer_than_280_is_rejected_by_schema() -> None:
    with pytest.raises(ValueError):
        ThanksIn(to_user_id=BEN, note="x" * 281)


@pytest.mark.asyncio
async def test_unknown_teammate_is_not_found(monkeypatch) -> None:
    svc, _ = _service(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await svc.send_thanks(_actor(), ThanksIn(to_user_id=uuid.uuid4(), note=NOTE))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_monthly_cap_per_giver(monkeypatch) -> None:
    svc, _ = _service(monkeypatch)
    recipients = [BEN, CARA, DAN]
    assert len(recipients) == THANKS_PER_GIVER_MONTH
    for uid in recipients:
        await svc.send_thanks(_actor(), ThanksIn(to_user_id=uid, note=NOTE))
    # Three used; a fourth to anyone is refused. Add a fresh recipient to prove it is the cap.
    fourth = uuid.uuid4()
    svc.session.get = AsyncMock(return_value=SimpleNamespace(id=fourth, name="New"))
    with pytest.raises(HTTPException) as exc:
        await svc.send_thanks(_actor(), ThanksIn(to_user_id=fourth, note=NOTE))
    assert exc.value.status_code == 400
    assert "3 thanks" in exc.value.detail


@pytest.mark.asyncio
async def test_only_one_thanks_per_teammate_per_month(monkeypatch) -> None:
    svc, _ = _service(monkeypatch)
    await svc.send_thanks(_actor(), ThanksIn(to_user_id=BEN, note=NOTE))
    with pytest.raises(HTTPException) as exc:
        await svc.send_thanks(_actor(), ThanksIn(to_user_id=BEN, note=NOTE))
    assert exc.value.status_code == 400
    assert "already thanked" in exc.value.detail


@pytest.mark.asyncio
async def test_thanks_last_month_do_not_count(monkeypatch) -> None:
    repo = FakeRepo()
    last_month = NOW.replace(month=10)
    for uid in (BEN, CARA, DAN):
        repo.thanks.append(SimpleNamespace(
            id=uuid.uuid4(), from_user_id=ALICE, to_user_id=uid, note=NOTE,
            created_at=last_month,
        ))
    svc, _ = _service(monkeypatch, repo)
    result = await svc.send_thanks(_actor(), ThanksIn(to_user_id=BEN, note=NOTE))
    assert result.to_user_id == BEN


@pytest.mark.asyncio
async def test_successful_thanks_awards_recipient_four_collab_points(monkeypatch) -> None:
    svc, repo = _service(monkeypatch)
    out = await svc.send_thanks(_actor(), ThanksIn(to_user_id=BEN, note=NOTE))
    assert out.from_user_id == ALICE and out.to_user_id == BEN
    assert len(repo.thanks) == 1
    svc.add_points.assert_awaited_once()
    args, kwargs = svc.add_points.call_args
    assert args[0] == "thanks" and args[1] == BEN
    assert args[2] == REC_RULES["thanks"]["points"] == 4
    assert REC_RULES["thanks"]["dim"] == "collab"
    assert kwargs["ref_key"] == str(out.id)


# ---- period windows ----------------------------------------------------------

def test_period_windows() -> None:
    assert rs._period_start("all", NOW) is None
    assert rs._period_start("week", NOW) == NOW - timedelta(days=7)
    assert rs._period_start("quarter", NOW) == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert rs._period_start("year", NOW) == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_quarter_window_on_quarter_start_day() -> None:
    first_day = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    assert rs._period_start("quarter", first_day) == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_dims_and_sum_helpers() -> None:
    pts = {"submit": 5, "accepted": 30, "prototype": 40, "unknown_rule": 9}
    assert rs._sum_points(pts) == 84
    assert rs._dims_of(pts) == {"quality": 35, "delivery": 40}


# ---- leaderboard -------------------------------------------------------------

def _seed(repo: FakeRepo) -> None:
    d = timedelta(days=1)
    repo.add_entry(ALICE, "submit", 5, NOW - 1 * d)          # this week, quality
    repo.add_entry(ALICE, "accepted", 30, NOW - 30 * d)      # last month, quality
    repo.add_entry(BEN, "prototype", 40, NOW - 2 * d)        # this week, delivery
    repo.add_entry(CARA, "helpful", 3, datetime(2026, 1, 15, tzinfo=timezone.utc))  # old, collab
    repo.add_entry(DAN, "accepted", 99, NOW - 1 * d, escrow=True)  # escrowed: never shown


@pytest.mark.asyncio
async def test_all_time_board_ranks_movement_and_dims(monkeypatch) -> None:
    repo = FakeRepo()
    _seed(repo)
    svc, _ = _service(monkeypatch, repo)
    rows = await svc.leaderboard(limit=10, period="all")
    ids = [r.user_id for r in rows]
    assert ids == [BEN, ALICE, CARA]                    # DAN is escrowed and excluded
    by_id = {r.user_id: r for r in rows}
    assert by_id[BEN].points == 40 and by_id[BEN].dims == {"delivery": 40}
    assert by_id[ALICE].points == 35 and by_id[ALICE].dims == {"quality": 35}
    assert by_id[ALICE].week_points == 5
    assert by_id[BEN].week_points == 40
    assert by_id[CARA].week_points == 0
    # Last week Alice was #1 (30 pts), Cara #2. Now Ben is #1, Alice #2, Cara #3.
    assert by_id[ALICE].rank_change == -1
    assert by_id[CARA].rank_change == -1
    assert by_id[BEN].rank_change is None               # not on last week's board


@pytest.mark.asyncio
async def test_quarter_board_drops_older_points_and_has_no_movement(monkeypatch) -> None:
    repo = FakeRepo()
    _seed(repo)
    svc, _ = _service(monkeypatch, repo)
    rows = await svc.leaderboard(limit=10, period="quarter")
    assert [r.user_id for r in rows] == [BEN, ALICE]    # Cara's January points are out of window
    assert [r.points for r in rows] == [40, 35]
    assert all(r.rank_change is None and r.week_points == 0 for r in rows)


@pytest.mark.asyncio
async def test_year_board_includes_january(monkeypatch) -> None:
    repo = FakeRepo()
    _seed(repo)
    svc, _ = _service(monkeypatch, repo)
    rows = await svc.leaderboard(limit=10, period="year")
    assert [r.user_id for r in rows] == [BEN, ALICE, CARA]


@pytest.mark.asyncio
async def test_board_limit_applies(monkeypatch) -> None:
    repo = FakeRepo()
    _seed(repo)
    svc, _ = _service(monkeypatch, repo)
    rows = await svc.leaderboard(limit=1, period="all")
    assert [r.user_id for r in rows] == [BEN]
