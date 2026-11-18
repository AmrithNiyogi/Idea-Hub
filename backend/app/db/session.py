"""Async SQLAlchemy engine, session factory, and Redis client wiring.

This module is the spine contract that Phase 2+3 soft-imports
(``app.db.session.Base``, ``get_db``, ``AsyncSessionLocal``).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings

_redis: redis.Redis | None = None


class Base(DeclarativeBase):
    """Canonical declarative base for spine and Phase 2+3 models."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async SQLAlchemy session.

    Side Effects:
        Opens a session from the shared pool; commits are the caller's
        responsibility. Rolls back on unhandled exceptions (including
        ``HTTPException`` injected by FastAPI via ``athrow``), then closes.

    Note:
        Use ``try`` / ``yield`` / ``except`` / ``finally`` and always
        re-raise after rollback so the generator completes cleanly after
        ``athrow`` (otherwise clients can see 500 instead of 401).
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_redis() -> redis.Redis:
    """Return a lazily created sync Redis client (decode_responses=True).

    Used by the login OTP service. Sync client matches the Kompass admin
    pattern and keeps OTP issue/verify atomic via pipelines.
    """
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _redis


async def dispose_engine() -> None:
    """Dispose the async engine connection pool."""
    await engine.dispose()


def close_redis() -> None:
    """Close the sync Redis client if it was opened."""
    global _redis
    if _redis is not None:
        _redis.close()
        _redis = None
