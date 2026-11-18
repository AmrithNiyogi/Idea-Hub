"""Persistence for AI Newsletter stories and category state."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsCategoryState, NewsItem


class NewsRepository:
    """Repository for stored newsletter stories (keyed by category)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_state(self, category: str) -> Optional[NewsCategoryState]:
        return await self.session.get(NewsCategoryState, category)

    async def list_items(self, category: str) -> Sequence[NewsItem]:
        stmt = (
            select(NewsItem)
            .where(NewsItem.category == category)
            .order_by(NewsItem.published_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_all_items(self) -> Sequence[NewsItem]:
        stmt = select(NewsItem).order_by(NewsItem.published_at.desc())
        return (await self.session.execute(stmt)).scalars().all()

    async def replace_digest(
        self,
        category: str,
        brief: str,
        items: Sequence[dict[str, Any]],
        refreshed_at: datetime,
    ) -> None:
        """Swap a category's stories and brief for a fresh set."""
        await self.session.execute(
            delete(NewsItem).where(NewsItem.category == category)
        )
        self.session.add_all(NewsItem(category=category, **item) for item in items)
        state = await self.get_state(category)
        if state is None:
            state = NewsCategoryState(category=category)
            self.session.add(state)
        state.brief = brief
        state.refreshed_at = refreshed_at
        state.last_error = None
        await self.session.commit()

    async def record_error(self, category: str, message: str) -> None:
        """Keep the last good stories and note why the refresh failed."""
        state = await self.get_state(category)
        if state is None:
            state = NewsCategoryState(category=category, brief="")
            self.session.add(state)
        state.last_error = message
        await self.session.commit()
