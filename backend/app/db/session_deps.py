"""Session dependency for Phase 2+3.

Delegates to spine ``app.db.session.get_db`` (always available in this app).
Do not wrap spine ``get_db`` in ``try/except Exception`` around ``yield`` —
FastAPI injects dependency failures (e.g. auth 401) via ``athrow``, and
swallowing then yielding again causes
``RuntimeError: generator didn't stop after athrow()`` (client sees 500).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
