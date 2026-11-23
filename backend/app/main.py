"""IdeaKonnekt FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.db.session import close_redis, dispose_engine
from app.phase23_register import import_phase23_models, include_phase23_routers
from app.phase456_register import import_phase456_models, include_phase456_routers
from app.routers import agent_handoff, auth, ideas, notifications, review, users
from app.services.account_service import uploads_root

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("idea_hub")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Start/stop shared resources."""
    import_phase23_models()
    import_phase456_models()
    import app.models.notification  # noqa: F401 — register notifications metadata
    uploads = uploads_root()
    (uploads / "avatars").mkdir(parents=True, exist_ok=True)
    (uploads / "group-avatars").mkdir(parents=True, exist_ok=True)
    logger.info("IdeaKonnekt API starting (env=%s)", settings.ENV)
    yield
    close_redis()
    await dispose_engine()
    logger.info("IdeaKonnekt API stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["access-token", "refresh-token"],
)

prefix = settings.API_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(ideas.router, prefix=prefix)
app.include_router(agent_handoff.router, prefix=prefix)
app.include_router(review.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
include_phase23_routers(app, prefix=prefix)
include_phase456_routers(app, prefix=prefix)

_upload_path = Path(settings.UPLOAD_DIR)
if not _upload_path.is_absolute():
    _upload_path = Path.cwd() / _upload_path
_upload_path.mkdir(parents=True, exist_ok=True)
(_upload_path / "avatars").mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=str(_upload_path.resolve())),
    name="uploads",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
