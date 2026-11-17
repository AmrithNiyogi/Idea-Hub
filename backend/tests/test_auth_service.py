"""Auth service — password hashing, JWT issue/verify, role switch."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config.settings import settings
from app.services import auth_service


def test_hash_and_verify_password_roundtrip() -> None:
    hashed = auth_service.hash_password("IdeaHub!2026")
    assert hashed != "IdeaHub!2026"
    assert auth_service.verify_password("IdeaHub!2026", hashed) is True
    assert auth_service.verify_password("wrong", hashed) is False


def test_create_and_decode_access_token(make_user) -> None:
    user = make_user()
    token = auth_service.create_access_token(user, active_role="lead")
    payload = auth_service.decode_token(token, "access")
    assert payload["sub"] == str(user.id)
    assert payload["active_role"] == "lead"
    assert payload["type"] == "access"
    assert "lead" in payload["roles"] or "contributor" in payload["roles"]


def test_decode_token_rejects_wrong_type(make_user) -> None:
    user = make_user()
    refresh = auth_service.create_refresh_token(user.id)
    with pytest.raises(HTTPException) as exc:
        auth_service.decode_token(refresh, "access")
    assert exc.value.status_code == 401


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(HTTPException) as exc:
        auth_service.decode_token("not.a.jwt", "access")
    assert exc.value.status_code == 401


def test_decode_token_expired(make_user) -> None:
    user = make_user()
    payload = {
        "sub": str(user.id),
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(minutes=5),
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as exc:
        auth_service.decode_token(token, "access")
    assert exc.value.status_code == 403


def test_user_to_public_and_issue_tokens(make_user) -> None:
    user = make_user()
    public = auth_service.user_to_public(user, active_role="contributor")
    assert public.email == user.email
    assert public.active_role == "contributor"

    bundle = auth_service.issue_login_tokens(user)
    assert "access_token" in bundle and "refresh_token" in bundle
    assert bundle["user"].id == user.id


def test_resolve_user_roles_and_default(make_user) -> None:
    multi = make_user(roles=["lead", "contributor", "reviewer"], primary_role="lead")
    assert auth_service.resolve_user_roles(multi) == [
        "contributor",
        "reviewer",
        "lead",
    ]
    assert auth_service.default_active_role(multi) == "lead"

    single = make_user(roles=["admin"], primary_role="admin")
    assert auth_service.resolve_user_roles(single) == ["admin"]
    assert auth_service.default_active_role(single) == "admin"


@pytest.mark.asyncio
async def test_complete_login_with_role(make_user, async_session: AsyncMock) -> None:
    user = make_user(roles=["contributor", "lead"], primary_role="contributor")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    out = await auth_service.complete_login_with_role(
        async_session, user.id, "lead"
    )
    payload = auth_service.decode_token(out["access_token"], "access")
    assert payload["active_role"] == "lead"
    assert out["user"].active_role == "lead"


@pytest.mark.asyncio
async def test_authenticate_credentials_success(make_user, async_session: AsyncMock) -> None:
    user = make_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    got = await auth_service.authenticate_credentials(
        async_session, user.email, "IdeaHub!2026"
    )
    assert got is user


@pytest.mark.asyncio
async def test_authenticate_credentials_bad_password(
    make_user, async_session: AsyncMock
) -> None:
    user = make_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    with pytest.raises(HTTPException) as exc:
        await auth_service.authenticate_credentials(
            async_session, user.email, "nope"
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_credentials_disabled(
    make_user, async_session: AsyncMock
) -> None:
    user = make_user(status="disabled")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    with pytest.raises(HTTPException) as exc:
        await auth_service.authenticate_credentials(
            async_session, user.email, "IdeaHub!2026"
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_access_token(make_user, async_session: AsyncMock) -> None:
    user = make_user()
    refresh = auth_service.create_refresh_token(user.id)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    access, public = await auth_service.refresh_access_token(async_session, refresh)
    assert public.id == user.id
    payload = auth_service.decode_token(access, "access")
    assert payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_refresh_access_token_disabled_user(
    make_user, async_session: AsyncMock
) -> None:
    user = make_user(status="disabled")
    refresh = auth_service.create_refresh_token(user.id)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    with pytest.raises(HTTPException) as exc:
        await auth_service.refresh_access_token(async_session, refresh)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_switch_role_success(make_user, async_session: AsyncMock) -> None:
    user = make_user(roles=["contributor", "lead"], primary_role="contributor")
    out = await auth_service.switch_role(
        async_session, user, "lead", "contributor"
    )
    assert out["role"] == "lead"
    payload = auth_service.decode_token(out["access_token"], "access")
    assert payload["active_role"] == "lead"


@pytest.mark.asyncio
async def test_switch_role_unknown_and_unheld(
    make_user, async_session: AsyncMock
) -> None:
    user = make_user(roles=["contributor"])
    with pytest.raises(HTTPException) as exc:
        await auth_service.switch_role(async_session, user, "wizard", "contributor")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        await auth_service.switch_role(async_session, user, "admin", "contributor")
    assert exc2.value.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_email_and_id(make_user, async_session: AsyncMock) -> None:
    user = make_user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    assert await auth_service.get_user_by_email(async_session, user.email) is user
    assert await auth_service.get_user_by_id(async_session, user.id) is user


def test_create_access_token_falls_back_when_active_not_in_roles() -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="x@example.com",
        roles=["contributor"],
        primary_role="contributor",
    )
    token = auth_service.create_access_token(user, active_role="admin")
    payload = auth_service.decode_token(token, "access")
    assert payload["active_role"] == "contributor"


def test_slug_from_email() -> None:
    assert auth_service._slug_from_email("Priya.Sharma@dotkonnekt.example") == "priya-sharma"
    assert auth_service._slug_from_email("@@@") == "user"


@pytest.mark.asyncio
async def test_unique_slug_collides_then_succeeds(async_session: AsyncMock) -> None:
    first = MagicMock()
    first.scalar_one_or_none.return_value = uuid.uuid4()
    second = MagicMock()
    second.scalar_one_or_none.return_value = None
    async_session.execute = AsyncMock(side_effect=[first, second])
    slug = await auth_service._unique_slug(async_session, "priya")
    assert slug.startswith("priya")


@pytest.mark.asyncio
async def test_upsert_microsoft_user_existing(
    make_user, async_session: AsyncMock
) -> None:
    user = make_user(name="priya")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result
    out = await auth_service.upsert_microsoft_user(
        async_session, email=user.email, name="Priya Sharma"
    )
    assert out is user
    assert user.name == "Priya Sharma"


@pytest.mark.asyncio
async def test_upsert_microsoft_user_disabled(
    make_user, async_session: AsyncMock
) -> None:
    user = make_user(status="disabled")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result
    with pytest.raises(HTTPException) as exc:
        await auth_service.upsert_microsoft_user(
            async_session, email=user.email, name="X"
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_upsert_microsoft_user_creates(
    async_session: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config.settings import settings

    monkeypatch.setattr(settings, "MICROSOFT_DEFAULT_ROLE", "wizard")
    miss = MagicMock()
    miss.scalar_one_or_none.return_value = None
    slug_ok = MagicMock()
    slug_ok.scalar_one_or_none.return_value = None
    async_session.execute = AsyncMock(side_effect=[miss, slug_ok])

    created: list[Any] = []

    def _add(obj: Any) -> None:
        created.append(obj)

    async_session.add = _add
    out = await auth_service.upsert_microsoft_user(
        async_session, email="new.user@example.com", name="New User"
    )
    assert out.email == "new.user@example.com"
    assert out.primary_role == "contributor"  # invalid role falls back
    assert out.has_password is False
    assert created
    async_session.commit.assert_awaited()


def test_user_to_public_includes_has_password(make_user) -> None:
    public = auth_service.user_to_public(make_user(has_password=False))
    assert public.has_password is False
    public_pw = auth_service.user_to_public(make_user(has_password=True))
    assert public_pw.has_password is True
