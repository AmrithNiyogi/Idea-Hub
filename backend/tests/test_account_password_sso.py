"""Password change is refused for Microsoft SSO-only accounts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.auth import ChangePasswordRequest
from app.services import account_service


@pytest.mark.asyncio
async def test_sso_only_account_cannot_change_password() -> None:
    user = SimpleNamespace(has_password=False, password_hash="unusable")
    session = AsyncMock()
    body = ChangePasswordRequest(
        current_password="whatever-1",
        new_password="new-password-1",
        confirm_password="new-password-1",
    )
    with pytest.raises(HTTPException) as exc:
        await account_service.change_password(session, user, body)  # type: ignore[arg-type]
    assert exc.value.status_code == 403
    assert "Microsoft" in str(exc.value.detail)
    session.flush.assert_not_awaited()
