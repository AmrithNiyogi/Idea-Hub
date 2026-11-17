"""Persistence for tracker / integration connections and idea links."""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracker import IdeaTrackerLink, TrackerConnection

SCOPE_USER = "user"
SCOPE_ORG = "organization"


class TrackerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_connections_for_user(
        self, user_id: uuid.UUID
    ) -> Sequence[TrackerConnection]:
        result = await self.session.execute(
            select(TrackerConnection)
            .where(
                TrackerConnection.scope == SCOPE_USER,
                TrackerConnection.user_id == user_id,
            )
            .order_by(TrackerConnection.provider_id, TrackerConnection.label)
        )
        return result.scalars().all()

    async def list_org_connections(self) -> Sequence[TrackerConnection]:
        result = await self.session.execute(
            select(TrackerConnection)
            .where(TrackerConnection.scope == SCOPE_ORG)
            .order_by(TrackerConnection.provider_id, TrackerConnection.label)
        )
        return result.scalars().all()

    async def get_connection(
        self, connection_id: uuid.UUID
    ) -> Optional[TrackerConnection]:
        result = await self.session.execute(
            select(TrackerConnection).where(TrackerConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def get_user_connection(
        self, connection_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[TrackerConnection]:
        result = await self.session.execute(
            select(TrackerConnection).where(
                TrackerConnection.id == connection_id,
                TrackerConnection.scope == SCOPE_USER,
                TrackerConnection.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_connection_for_user(
        self, connection_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[TrackerConnection]:
        """Backward-compatible: personal connection only."""
        return await self.get_user_connection(connection_id, user_id)

    async def get_usable_connection(
        self, connection_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[TrackerConnection]:
        """Personal connection owned by user, or any org-default connection."""
        result = await self.session.execute(
            select(TrackerConnection).where(TrackerConnection.id == connection_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        if row.scope == SCOPE_ORG:
            return row
        if row.scope == SCOPE_USER and row.user_id == user_id:
            return row
        return None

    async def find_user_connection(
        self, user_id: uuid.UUID, provider_id: str, label: str = "default"
    ) -> Optional[TrackerConnection]:
        result = await self.session.execute(
            select(TrackerConnection).where(
                TrackerConnection.scope == SCOPE_USER,
                TrackerConnection.user_id == user_id,
                TrackerConnection.provider_id == provider_id,
                TrackerConnection.label == label,
            )
        )
        return result.scalar_one_or_none()

    async def find_org_connection(
        self, provider_id: str, label: str = "default"
    ) -> Optional[TrackerConnection]:
        result = await self.session.execute(
            select(TrackerConnection).where(
                TrackerConnection.scope == SCOPE_ORG,
                TrackerConnection.provider_id == provider_id,
                TrackerConnection.label == label,
            )
        )
        return result.scalar_one_or_none()

    async def find_connection(
        self, user_id: uuid.UUID, provider_id: str, label: str
    ) -> Optional[TrackerConnection]:
        """Backward-compatible alias for personal find."""
        return await self.find_user_connection(user_id, provider_id, label)

    async def resolve_effective(
        self, user_id: uuid.UUID, provider_id: str, label: str = "default"
    ) -> tuple[Optional[TrackerConnection], str]:
        """Return (connection, source) where source is user|organization|none."""
        user_conn = await self.find_user_connection(user_id, provider_id, label)
        if user_conn:
            return user_conn, "user"
        org_conn = await self.find_org_connection(provider_id, label)
        if org_conn:
            return org_conn, "organization"
        return None, "none"

    async def add_connection(self, row: TrackerConnection) -> TrackerConnection:
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete_connection(self, row: TrackerConnection) -> None:
        await self.session.delete(row)
        await self.session.flush()

    async def list_links_for_idea(
        self, idea_id: uuid.UUID
    ) -> Sequence[IdeaTrackerLink]:
        result = await self.session.execute(
            select(IdeaTrackerLink)
            .where(IdeaTrackerLink.idea_id == idea_id)
            .order_by(IdeaTrackerLink.created_at.desc())
        )
        return result.scalars().all()

    async def get_link(self, link_id: uuid.UUID) -> Optional[IdeaTrackerLink]:
        result = await self.session.execute(
            select(IdeaTrackerLink).where(IdeaTrackerLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def add_link(self, row: IdeaTrackerLink) -> IdeaTrackerLink:
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete_link(self, row: IdeaTrackerLink) -> None:
        await self.session.delete(row)
        await self.session.flush()
