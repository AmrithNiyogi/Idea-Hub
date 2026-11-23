"""The Phase 2+3 actor dependency says whether a token arrived, or whether it was rejected."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.dependencies.phase23_auth import get_actor


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


@pytest.mark.asyncio
async def test_no_token_says_none_received() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_actor(_request([]), MagicMock(), None, None, None)
    assert exc.value.status_code == 401
    assert "No access token received" in exc.value.detail


@pytest.mark.asyncio
async def test_invalid_token_says_received_but_rejected() -> None:
    req = _request([(b"x-authorization", b"not-a-real-jwt")])
    with pytest.raises(HTTPException) as exc:
        await get_actor(req, MagicMock(), None, None, None)
    assert exc.value.status_code == 401
    assert "invalid or expired" in exc.value.detail
