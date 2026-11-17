"""SQLAlchemy declarative base re-export.

Phase 2+3 models import ``Base`` from here. Prefer the spine session Base;
keep a local fallback only if session wiring is temporarily unavailable.
"""

from __future__ import annotations

try:
    from app.db.session import Base
except Exception:  # noqa: BLE001 — import-time fallback for incomplete installs
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        """Fallback declarative base used only until spine session lands."""


__all__ = ["Base"]
