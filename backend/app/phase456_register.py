"""Registration hook for Phase 4+5+6 routers.

Spine ``main.py`` should call::

    from app.phase456_register import include_phase456_routers, import_phase456_models
    import_phase456_models()
    include_phase456_routers(app)

This keeps Phases 4–6 additive — no edits to auth or core idea routers required.
Safe to call alongside ``include_phase23_routers``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def include_phase456_routers(app: "FastAPI", *, prefix: str = "/api/v1") -> None:
    """Mount Insights, Admin, Agents, Problems, Reopen, Collab, Team-space routers.

    Args:
        app: FastAPI application instance owned by spine.
        prefix: API version prefix (default ``/api/v1``).

    Side Effects:
        Registers routers on ``app``. Safe to call once at startup.
    """
    from app.routers import (
        admin,
        agents,
        collab,
        groups,
        insights,
        problems,
        reopen,
    )

    app.include_router(insights.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(problems.router, prefix=prefix)
    app.include_router(reopen.router, prefix=prefix)
    app.include_router(collab.router, prefix=prefix)
    app.include_router(groups.router, prefix=prefix)


PHASE456_MODEL_MODULES = (
    "app.models.admin",
    "app.models.agent",
    "app.models.problem",
    "app.models.reopen",
    "app.models.collab",
    "app.models.groups",
)


def import_phase456_models() -> None:
    """Import all Phase 4+5+6 ORM modules for metadata registration."""
    import importlib

    for mod in PHASE456_MODEL_MODULES:
        importlib.import_module(mod)
