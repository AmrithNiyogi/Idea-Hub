"""AI Newsletter HTTP API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.constants.news_constants import NEWS_DEFAULT_CATEGORY
from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.news import NewsCategoryOut, NewsFeedOut, NewsInsightsOut
from app.services.news_service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


@router.get(
    "/categories",
    response_model=list[NewsCategoryOut],
    summary="List AI newsletter categories",
)
async def list_categories(actor: RequireActor) -> list[NewsCategoryOut]:
    del actor
    return NewsService.list_categories()


@router.get(
    "/insights",
    response_model=NewsInsightsOut,
    summary="Trending repos, weekly paper counts and recurring themes",
)
async def get_insights(session: DbSession, actor: RequireActor) -> NewsInsightsOut:
    del actor
    return await NewsService(session).get_insights()


@router.get(
    "",
    response_model=NewsFeedOut,
    summary="Stored AI news for one category",
)
async def get_feed(
    session: DbSession,
    actor: RequireActor,
    category: str = Query(NEWS_DEFAULT_CATEGORY),
) -> NewsFeedOut:
    del actor
    return await NewsService(session).get_feed(category)


@router.post(
    "/{category}/refresh",
    response_model=NewsFeedOut,
    summary="Refresh a category when stale (admins can force)",
)
async def refresh_category(
    category: str,
    session: DbSession,
    actor: RequireActor,
    force: bool = Query(False),
) -> NewsFeedOut:
    return await NewsService(session).refresh(category, force=force, actor=actor)
