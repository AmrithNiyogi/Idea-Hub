"""Shared fixtures for KonnektIdea backend unit tests.

External I/O (Postgres, Redis, SMTP) is mocked so ``make test`` runs without
dev-services. Critical-path coverage targets are declared in ``pyproject.toml``.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import app modules inside fixtures (not at collection time) so pytest-cov
# can start measuring before they are loaded.


@pytest.fixture
def user_id() -> uuid.UUID:
    """Stable UUID for the primary test principal."""
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def reviewer_id() -> uuid.UUID:
    """Stable UUID for a reviewer principal."""
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def make_user(user_id: uuid.UUID):
    """Factory for lightweight ORM-like user objects."""
    from app.services import auth_service

    def _factory(**overrides: Any) -> SimpleNamespace:
        base = {
            "id": user_id,
            "email": "priya@dotkonnekt.example",
            "password_hash": auth_service.hash_password("IdeaHub!2026"),
            "name": "Priya Sharma",
            "title": "Product",
            "team_id": None,
            "roles": ["contributor", "lead"],
            "primary_role": "contributor",
            "status": "active",
            "avatar": 1,
            "avatar_url": None,
            "slug": "priya-sharma",
            "totp_enabled": False,
            "totp_secret": None,
            "has_password": True,
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    return _factory


@pytest.fixture
def current_user(user_id: uuid.UUID):
    """Authenticated contributor principal."""
    from app.dependencies.auth import CurrentUser

    return CurrentUser(
        id=user_id,
        email="priya@dotkonnekt.example",
        name="Priya Sharma",
        roles=["contributor", "lead"],
        active_role="contributor",
        primary_role="contributor",
        slug="priya-sharma",
    )


@pytest.fixture
def reviewer_user(reviewer_id: uuid.UUID):
    """Authenticated reviewer principal."""
    from app.dependencies.auth import CurrentUser

    return CurrentUser(
        id=reviewer_id,
        email="elena@dotkonnekt.example",
        name="Elena Rossi",
        roles=["reviewer"],
        active_role="reviewer",
        primary_role="reviewer",
        slug="elena-rossi",
    )


@pytest.fixture
def async_session() -> AsyncMock:
    """Async SQLAlchemy session stub with commit/flush/add/get/refresh."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


class FakeRedis:
    """Minimal in-memory Redis stand-in for login OTP tests.

    Supports the subset used by ``login_otp_service``: ``set`` (nx/ex),
    ``hset``/``hget``/``hincrby``, ``delete``, ``expire``, and ``pipeline``.
    """

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str | int]] = {}

    def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool | None:
        del ex
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    def delete(self, *keys: str) -> int:
        n = 0
        for key in keys:
            if key in self.kv:
                del self.kv[key]
                n += 1
            if key in self.hashes:
                del self.hashes[key]
                n += 1
        return n

    def hset(self, key: str, mapping: dict[str, Any] | None = None, **kwargs: Any) -> int:
        data = dict(mapping or {})
        data.update(kwargs)
        bucket = self.hashes.setdefault(key, {})
        for field, value in data.items():
            bucket[field] = value
        return len(data)

    def hget(self, key: str, field: str) -> str | None:
        bucket = self.hashes.get(key)
        if not bucket or field not in bucket:
            return None
        return str(bucket[field])

    def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        bucket = self.hashes.setdefault(key, {})
        current = int(bucket.get(field, 0))
        current += amount
        bucket[field] = current
        return current

    def expire(self, key: str, seconds: int) -> bool:
        del seconds
        return key in self.kv or key in self.hashes

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self)


class FakeRedisPipeline:
    """Collects Redis commands and executes them against ``FakeRedis``."""

    def __init__(self, client: FakeRedis) -> None:
        self.client = client
        self._ops: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def delete(self, *keys: str) -> FakeRedisPipeline:
        self._ops.append(("delete", keys, {}))
        return self

    def hset(self, key: str, mapping: dict[str, Any] | None = None, **kwargs: Any) -> FakeRedisPipeline:
        self._ops.append(("hset", (key,), {"mapping": mapping, **kwargs}))
        return self

    def expire(self, key: str, seconds: int) -> FakeRedisPipeline:
        self._ops.append(("expire", (key, seconds), {}))
        return self

    def execute(self) -> list[Any]:
        results: list[Any] = []
        for name, args, kwargs in self._ops:
            results.append(getattr(self.client, name)(*args, **kwargs))
        self._ops.clear()
        return results


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """Patch ``get_redis`` to return an in-memory FakeRedis."""
    client = FakeRedis()
    monkeypatch.setattr("app.services.login_otp_service.get_redis", lambda: client)
    monkeypatch.setattr("app.db.session.get_redis", lambda: client)
    return client
