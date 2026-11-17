"""Insights HTTP API — Phase 4."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.insights import InsightsDashboardOut
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get(
    "",
    response_model=InsightsDashboardOut,
    summary="Insights dashboard aggregates",
    description=(
        "Participation, funnel, review speed, themes, impact, hours, and "
        "recognition summaries computed from Postgres. Cards are labelled Simulated."
    ),
)
async def insights_dashboard(
    session: DbSession,
    actor: RequireActor,
    days: int = Query(90, ge=7, le=365),
) -> InsightsDashboardOut:
    return await InsightsService(session).dashboard(days)
