"""Session dependency for Phase 2+3.

TODO: wire into spine — prefer ``app.db.session.get_db`` once available.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends


async def get_db() -> AsyncGenerator[Any, None]:
    """Yield an async SQLAlchemy session from spine or raise a clear error."""
    try:
        from app.db.session import get_db as spine_get_db

        async for session in spine_get_db():
            yield session
        return
    except Exception:  # noqa: BLE001
        pass

    try:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            yield session
        return
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "No DB session factory found. Spine must expose "
            "app.db.session.get_db or AsyncSessionLocal before "
            "Phase 2+3 endpoints can run."
        ) from exc


DbSession = Annotated[Any, Depends(get_db)]
