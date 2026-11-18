"""Regression: DB session deps must exit cleanly when auth raises 401."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_session_deps_get_db_athrow_http_exception_exits_cleanly() -> None:
    """FastAPI athrows HTTPException into yielded deps on auth failure.

    A buggy wrapper that catches Exception and yields again produces
    ``RuntimeError: generator didn't stop after athrow()`` → client 500.
    """
    from app.db import session_deps
    from app.db.session import get_db as spine_get_db

    # Phase routers import DbSession from session_deps; it must be spine get_db.
    assert session_deps.get_db is spine_get_db

    mock_session = MagicMock(name="AsyncSession")
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_session):
        gen = session_deps.get_db()
        session = await gen.__anext__()
        assert session is mock_session

        with pytest.raises(HTTPException) as exc_info:
            await gen.athrow(
                HTTPException(status_code=401, detail="Not authenticated")
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"
        mock_session.rollback.assert_awaited()
        mock_session.close.assert_awaited()

        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
