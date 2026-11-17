"""Delivery service smoke — quarter helpers and request/list guards."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.dependencies.phase23_auth import Actor
from app.schemas.delivery import HoursRequestCreate, PoolOut
from app.services.delivery_service import (
    DeliveryService,
    _quarter_bounds,
    _quarter_key,
)


def test_quarter_key_and_bounds() -> None:
    ts = datetime(2026, 5, 15, tzinfo=timezone.utc)
    assert _quarter_key(ts) == "2026-Q2"
    start, end = _quarter_bounds("2026-Q2")
    assert start == datetime(2026, 4, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 1, tzinfo=timezone.utc)
    start4, end4 = _quarter_bounds("2026-Q4")
    assert start4.month == 10
    assert end4 == datetime(2027, 1, 1, tzinfo=timezone.utc)


def _actor(**overrides) -> Actor:
    base = {
        "id": uuid.uuid4(),
        "roles": ["contributor"],
        "active_role": "contributor",
        "name": "Owner",
        "email": "owner@example.com",
    }
    base.update(overrides)
    return Actor(**base)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_get_delivery_without_project(async_session: AsyncMock) -> None:
    svc = DeliveryService(async_session)
    idea = SimpleNamespace(id=uuid.uuid4(), status="accepted", owner_id=uuid.uuid4())
    svc.spine = MagicMock()
    svc.spine.get_idea = AsyncMock(return_value=idea)
    svc.repo = MagicMock()
    svc.repo.get_project_by_idea = AsyncMock(return_value=None)
    svc.repo.pending_request = AsyncMock(return_value=None)
    svc._pool_out = AsyncMock(
        return_value=PoolOut(
            period_key="2026-Q4",
            budget_hours=400,
            granted_hours=10,
            remaining=390,
        )
    )
    out = await svc.get_delivery(idea.id, _actor())
    assert out.idea_id == idea.id
    assert out.project_id is None


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_request_hours_guards(async_session: AsyncMock) -> None:
    svc = DeliveryService(async_session)
    actor = _actor(roles=["contributor"])
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        status="under_review",
        owner_id=actor.id,
        title="t",
    )
    svc.spine = MagicMock()
    svc.spine.get_idea = AsyncMock(return_value=idea)
    body = HoursRequestCreate(hours=20, justification="Need time to prototype the cache.")

    with pytest.raises(HTTPException) as exc:
        await svc.request_hours(idea.id, body, actor)
    assert exc.value.status_code == 400

    idea.status = "accepted"
    idea.owner_id = None
    with pytest.raises(HTTPException) as exc2:
        await svc.request_hours(idea.id, body, actor)
    assert exc2.value.status_code == 400

    idea.owner_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc3:
        await svc.request_hours(idea.id, body, actor)
    assert exc3.value.status_code == 403


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_request_hours_success(async_session: AsyncMock) -> None:
    svc = DeliveryService(async_session)
    actor = _actor(roles=["contributor"])
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        status="accepted",
        owner_id=actor.id,
        title="Ship cache",
    )
    svc.spine = MagicMock()
    svc.spine.get_idea = AsyncMock(return_value=idea)
    svc.repo = MagicMock()
    svc.repo.pending_request = AsyncMock(return_value=None)

    async def _add_request(req: object) -> None:
        # ORM defaults/server_defaults are not applied without a real DB flush.
        req.id = uuid.uuid4()  # type: ignore[attr-defined]
        req.reason = ""  # type: ignore[attr-defined]
        req.override = False  # type: ignore[attr-defined]
        req.created_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
        req.decided_by = None  # type: ignore[attr-defined]
        req.decided_at = None  # type: ignore[attr-defined]
        req.granted_hours = None  # type: ignore[attr-defined]

    svc.repo.add_request = AsyncMock(side_effect=_add_request)

    leaders = MagicMock()
    leaders.scalars.return_value.all.return_value = [uuid.uuid4()]
    async_session.execute.return_value = leaders

    with patch(
        "app.services.delivery_service.notify_users", AsyncMock()
    ):
        out = await svc.request_hours(
            idea.id,
            HoursRequestCreate(
                hours=40, justification="Need a sprint to build the prototype."
            ),
            actor,
        )
    assert out.hours == 40
    assert out.state == "pending"
    async_session.commit.assert_awaited()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_list_hours_requests_requires_leadership(
    async_session: AsyncMock,
) -> None:
    svc = DeliveryService(async_session)
    with pytest.raises(HTTPException) as exc:
        await svc.list_hours_requests(_actor(roles=["contributor"]))
    assert exc.value.status_code == 403

    svc.repo = MagicMock()
    svc.repo.list_requests = AsyncMock(return_value=[])
    rows = await svc.list_hours_requests(
        _actor(roles=["leadership"], active_role="leadership")
    )
    assert rows == []


@pytest.mark.asyncio
async def test_require_idea_404(async_session: AsyncMock) -> None:
    svc = DeliveryService(async_session)
    svc.spine = MagicMock()
    svc.spine.get_idea = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        await svc._require_idea(uuid.uuid4())
    assert exc.value.status_code == 404
