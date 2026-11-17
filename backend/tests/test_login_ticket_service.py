"""Login ticket Redis helpers for multi-role complete-login."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import login_ticket_service


def test_issue_and_consume_ticket_roundtrip() -> None:
    store: dict[str, str] = {}
    client = MagicMock()

    def _set(key: str, value: str, ex: int | None = None) -> bool:
        del ex
        store[key] = value
        return True

    def _get(key: str) -> str | None:
        return store.get(key)

    def _delete(key: str) -> int:
        return 1 if store.pop(key, None) is not None else 0

    client.set.side_effect = _set
    client.get.side_effect = _get
    client.delete.side_effect = _delete

    with patch("app.services.login_ticket_service.get_redis", return_value=client):
        ticket = login_ticket_service.issue_ticket("user-1")
        assert ticket
        assert login_ticket_service.consume_ticket(ticket) == "user-1"
        with pytest.raises(HTTPException) as exc:
            login_ticket_service.consume_ticket(ticket)
        assert exc.value.status_code == 401


def test_consume_empty_ticket() -> None:
    with pytest.raises(HTTPException) as exc:
        login_ticket_service.consume_ticket("")
    assert exc.value.status_code == 401
