"""Persistence helpers for team spaces, channels, messages, meetings, MCP."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team_space import (
    IdeaMcpConnection,
    TeamChannel,
    TeamMeeting,
    TeamMessage,
    TeamSpace,
)


class TeamSpaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_space_by_idea(self, idea_id: uuid.UUID) -> Optional[TeamSpace]:
        result = await self.session.execute(
            select(TeamSpace).where(TeamSpace.idea_id == idea_id)
        )
        return result.scalar_one_or_none()

    async def get_space(self, space_id: uuid.UUID) -> Optional[TeamSpace]:
        result = await self.session.execute(
            select(TeamSpace).where(TeamSpace.id == space_id)
        )
        return result.scalar_one_or_none()

    async def add_space(self, row: TeamSpace) -> TeamSpace:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_channels(self, space_id: uuid.UUID) -> Sequence[TeamChannel]:
        result = await self.session.execute(
            select(TeamChannel)
            .where(TeamChannel.space_id == space_id)
            .order_by(TeamChannel.sort_order.asc(), TeamChannel.created_at.asc())
        )
        return result.scalars().all()

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[TeamChannel]:
        result = await self.session.execute(
            select(TeamChannel).where(TeamChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_channel_by_slug(
        self, space_id: uuid.UUID, slug: str
    ) -> Optional[TeamChannel]:
        result = await self.session.execute(
            select(TeamChannel).where(
                TeamChannel.space_id == space_id,
                TeamChannel.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def add_channel(self, row: TeamChannel) -> TeamChannel:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_messages(
        self,
        channel_id: uuid.UUID,
        *,
        limit: int = 80,
        before: Optional[datetime] = None,
    ) -> Sequence[TeamMessage]:
        stmt = (
            select(TeamMessage)
            .where(TeamMessage.channel_id == channel_id)
            .order_by(TeamMessage.created_at.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = stmt.where(TeamMessage.created_at < before)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def add_message(self, row: TeamMessage) -> TeamMessage:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_meetings(self, space_id: uuid.UUID) -> Sequence[TeamMeeting]:
        result = await self.session.execute(
            select(TeamMeeting)
            .where(TeamMeeting.space_id == space_id)
            .order_by(TeamMeeting.starts_at.desc())
            .limit(50)
        )
        return result.scalars().all()

    async def add_meeting(self, row: TeamMeeting) -> TeamMeeting:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_mcp(self, space_id: uuid.UUID) -> Sequence[IdeaMcpConnection]:
        result = await self.session.execute(
            select(IdeaMcpConnection)
            .where(IdeaMcpConnection.space_id == space_id)
            .order_by(IdeaMcpConnection.created_at.asc())
        )
        return result.scalars().all()

    async def get_mcp(self, mcp_id: uuid.UUID) -> Optional[IdeaMcpConnection]:
        result = await self.session.execute(
            select(IdeaMcpConnection).where(IdeaMcpConnection.id == mcp_id)
        )
        return result.scalar_one_or_none()

    async def add_mcp(self, row: IdeaMcpConnection) -> IdeaMcpConnection:
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete_mcp(self, row: IdeaMcpConnection) -> None:
        await self.session.delete(row)
        await self.session.flush()
