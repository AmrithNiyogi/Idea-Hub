"""Registration hook for Phase 2+3 routers.

Spine ``main.py`` should call::

    from app.phase23_register import include_phase23_routers
    include_phase23_routers(app)

This keeps Phase 2+3 additive — no edits to auth or core idea routers required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def include_phase23_routers(app: "FastAPI", *, prefix: str = "/api/v1") -> None:
    """Mount Delivery, Ideathons, Recognition, and Profiles routers.

    Args:
        app: FastAPI application instance owned by spine.
        prefix: API version prefix (default ``/api/v1``).

    Side Effects:
        Registers four routers on ``app``. Safe to call once at startup.
    """
    from app.routers import (
        agent_internal,
        delivery,
        ideathon_agents,
        ideathons,
        integrations,
        profiles,
        recognition,
        trackers,
    )

    app.include_router(delivery.router, prefix=prefix)
    app.include_router(ideathons.router, prefix=prefix)
    app.include_router(ideathon_agents.router, prefix=prefix)
    app.include_router(agent_internal.router, prefix=prefix)
    app.include_router(recognition.router, prefix=prefix)
    app.include_router(profiles.router, prefix=prefix)
    app.include_router(trackers.router, prefix=prefix)
    app.include_router(integrations.router, prefix=prefix)


# Models to import so Alembic / metadata sees Phase 2+3 tables.
PHASE23_MODEL_MODULES = (
    "app.models.delivery",
    "app.models.ideathon",
    "app.models.recognition",
    "app.models.tracker",
)


def import_phase23_models() -> None:
    """Import all Phase 2+3 ORM modules for metadata registration."""
    import importlib

    for mod in PHASE23_MODEL_MODULES:
        importlib.import_module(mod)
