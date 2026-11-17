"""Auth dependency helpers — token extraction and CurrentUser shaping."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.dependencies import auth as auth_deps
from app.services import auth_service


def _request(*, cookies: dict | None = None, headers: dict | None = None) -> Request:
    hdrs: list[tuple[bytes, bytes]] = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    if cookies:
        cookie = "; ".join(f"{k}={v}" for k, v in cookies.items())
        hdrs.append((b"cookie", cookie.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": hdrs,
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_current_user_role_helpers() -> None:
    user = auth_deps.CurrentUser(
        id=uuid.uuid4(),
        email="a@b.c",
        name="A",
        roles=["contributor", "Reviewer"],
        active_role="reviewer",
    )
    assert user.has_role("reviewer") is True
    assert user.has_role("admin") is False
    assert user.acting_as("reviewer") is True
    assert user.acting_as("admin") is False


def test_to_actor_dict(current_user) -> None:
    d = auth_deps.to_actor_dict(current_user)
    assert d["id"] == current_user.id
    assert d["active_role"] == current_user.active_role
    assert d["roles"] == current_user.roles


def test_extract_access_token_cookie_and_bearer() -> None:
    cookie_req = _request(cookies={"access_token": "cookie-tok"})
    assert auth_deps._extract_access_token(cookie_req) == "cookie-tok"

    bearer_req = _request(headers={"Authorization": "Bearer hdr-tok"})
    assert auth_deps._extract_access_token(bearer_req) == "hdr-tok"

    empty = _request()
    assert auth_deps._extract_access_token(empty) is None


@pytest.mark.asyncio
async def test_resolve_user_from_request_success(make_user, async_session: AsyncMock) -> None:
    user = make_user()
    token = auth_service.create_access_token(user, active_role="contributor")
    req = _request(cookies={"access_token": token})
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    async_session.execute.return_value = result

    current = await auth_deps.resolve_user_from_request(req, async_session)
    assert current is not None
    assert current.id == user.id
    assert current.email == user.email


@pytest.mark.asyncio
async def test_resolve_user_from_request_no_token(async_session: AsyncMock) -> None:
    assert await auth_deps.resolve_user_from_request(_request(), async_session) is None


@pytest.mark.asyncio
async def test_get_current_user_requires_auth(async_session: AsyncMock) -> None:
    with pytest.raises(HTTPException) as exc:
        await auth_deps.get_current_user(_request(), async_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_optional_user_passthrough(async_session: AsyncMock) -> None:
    with patch.object(
        auth_deps, "resolve_user_from_request", AsyncMock(return_value=None)
    ):
        assert await auth_deps.get_optional_user(_request(), async_session) is None
