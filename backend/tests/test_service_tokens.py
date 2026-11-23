"""Service tokens: hashed storage, verification, revocation, expiry, and the admin-only API."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.dependencies.phase23_auth import Actor
from app.models.service_token import ServiceToken
from app.routers import service_tokens as router
from app.schemas.service_tokens import ServiceTokenCreateIn
from app.services import service_token_service as svc

ADMIN = Actor(id=uuid.UUID("11111111-1111-1111-1111-111111111111"), roles=["admin"], active_role="admin")
CONTRIB = Actor(id=uuid.UUID("22222222-2222-2222-2222-222222222222"), roles=["contributor"])


def _session(row: ServiceToken | None = None) -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=row)
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=row)
    session.execute = AsyncMock(return_value=result)
    return session


def _row(**overrides) -> ServiceToken:
    base = dict(
        id=uuid.uuid4(), name="Kompass workflows", token_hash="x", prefix="ikst_abc",
        created_by=None, created_at=datetime.now(timezone.utc), expires_at=None,
        last_used_at=None, revoked_at=None, revoked_by=None,
    )
    base.update(overrides)
    return ServiceToken(**base)


@pytest.mark.asyncio
async def test_create_returns_plaintext_and_stores_only_the_hash() -> None:
    session = _session()
    row, plaintext = await svc.create(session, name="  Kompass  ", created_by=ADMIN.id)
    assert plaintext.startswith("ikst_")
    assert row.token_hash == svc._hash(plaintext)
    assert plaintext not in row.token_hash
    assert row.prefix == plaintext[:12]
    assert row.name == "Kompass"


@pytest.mark.asyncio
async def test_verify_accepts_a_live_token_and_records_use() -> None:
    token = "ikst_" + "a" * 43
    row = _row(token_hash=svc._hash(token))
    session = _session(row)
    assert await svc.verify(session, token) is row
    assert row.last_used_at is not None
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_verify_rejects_revoked_expired_unknown_and_wrong_form() -> None:
    token = "ikst_" + "b" * 43
    revoked = _row(token_hash=svc._hash(token), revoked_at=datetime.now(timezone.utc))
    assert await svc.verify(_session(revoked), token) is None

    expired = _row(
        token_hash=svc._hash(token),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert await svc.verify(_session(expired), token) is None

    assert await svc.verify(_session(None), token) is None
    assert await svc.verify(_session(_row()), "not-a-service-token") is None


def test_status_reports_revoked_before_expired() -> None:
    now = datetime.now(timezone.utc)
    assert svc.status_of(_row()) == "active"
    assert svc.status_of(_row(expires_at=now - timedelta(days=1))) == "expired"
    assert svc.status_of(_row(revoked_at=now, expires_at=now - timedelta(days=1))) == "revoked"


@pytest.mark.asyncio
async def test_revoke_sets_time_once() -> None:
    row = _row()
    await svc.revoke(_session(row), row.id, revoked_by=ADMIN.id)
    first = row.revoked_at
    assert first is not None and row.revoked_by == ADMIN.id
    await svc.revoke(_session(row), row.id, revoked_by=CONTRIB.id)
    assert row.revoked_at == first
    assert row.revoked_by == ADMIN.id


@pytest.mark.asyncio
async def test_revoke_unknown_token_is_404() -> None:
    with pytest.raises(HTTPException) as exc:
        await svc.revoke(_session(None), uuid.uuid4(), revoked_by=ADMIN.id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_admin_routes_refuse_non_admins() -> None:
    with pytest.raises(HTTPException) as exc:
        await router.list_tokens(_session(), CONTRIB)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        await router.create_token(ServiceTokenCreateIn(name="x"), _session(), CONTRIB)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_returns_token_once_with_record(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    out = await router.create_token(
        ServiceTokenCreateIn(name="Kompass", expires_in_days=30), session, ADMIN
    )
    assert out.token.startswith("ikst_")
    assert out.record.name == "Kompass"
    assert out.record.status == "active"
    assert out.record.expires_at is not None
    assert out.token not in out.record.model_dump_json()
    session.commit.assert_awaited()


def test_is_service_token_form() -> None:
    assert svc.is_service_token("ikst_abc")
    assert not svc.is_service_token("eyJhbGciOi.jwt.form")
    assert not svc.is_service_token(None)
