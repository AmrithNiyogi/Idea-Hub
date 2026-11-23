"""The signed-in access token is accepted from the cookie, Bearer header, or X-Authorization (agent tools)."""

from __future__ import annotations

from starlette.requests import Request

from app.dependencies.auth import _extract_access_token


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def test_x_authorization_is_accepted_when_no_cookie() -> None:
    req = _request([(b"x-authorization", b"token-abc")])
    assert _extract_access_token(req) == "token-abc"


def test_x_authorization_bearer_prefix_is_stripped() -> None:
    req = _request([(b"x-authorization", b"Bearer token-abc")])
    assert _extract_access_token(req) == "token-abc"


def test_cookie_still_wins_over_x_authorization() -> None:
    req = _request([(b"cookie", b"access_token=cookie-token"), (b"x-authorization", b"header-token")])
    assert _extract_access_token(req) == "cookie-token"


def test_no_token_returns_none() -> None:
    assert _extract_access_token(_request([])) is None
