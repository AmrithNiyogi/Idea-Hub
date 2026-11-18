"""Persistence helpers for hub groups, channels, messages, meetings, MCP, invites."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.groups import (
    GroupChannel,
    GroupInvite,
    GroupMeeting,
    GroupMember,
    GroupMessage,
    GroupMcpConnection,
    HubGroup,
)


class GroupsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        kind: Optional[str] = None,
    ) -> Sequence[HubGroup]:
        stmt = (
            select(HubGroup)
            .join(GroupMember, GroupMember.group_id == HubGroup.id)
            .where(
                GroupMember.user_id == user_id,
                HubGroup.deleted_at.is_(None),
            )
            .order_by(HubGroup.updated_at.desc())
        )
        if kind:
            stmt = stmt.where(HubGroup.kind == kind)
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def get(self, group_id: uuid.UUID) -> Optional[HubGroup]:
        return await self.session.get(HubGroup, group_id)

    async def get_by_idea(self, idea_id: uuid.UUID) -> Optional[HubGroup]:
        result = await self.session.execute(
            select(HubGroup).where(
                HubGroup.idea_id == idea_id,
                HubGroup.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_dm_by_pair_key(self, pair_key: str) -> Optional[HubGroup]:
        result = await self.session.execute(
            select(HubGroup).where(
                HubGroup.kind == "dm",
                HubGroup.dm_pair_key == pair_key,
                HubGroup.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def add_group(self, row: HubGroup) -> HubGroup:
        self.session.add(row)
        await self.session.flush()
        return row

    async def member_count(self, group_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(GroupMember)
            .where(GroupMember.group_id == group_id)
        )
        return int(result.scalar_one() or 0)

    async def get_member(
        self, group_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[GroupMember]:
        result = await self.session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, group_id: uuid.UUID) -> Sequence[GroupMember]:
        result = await self.session.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at.asc())
        )
        return result.scalars().all()

    async def add_member(self, row: GroupMember) -> GroupMember:
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete_member(self, row: GroupMember) -> None:
        await self.session.delete(row)
        await self.session.flush()

    # ----- invites -----

    async def get_invite(self, invite_id: uuid.UUID) -> Optional[GroupInvite]:
        return await self.session.get(GroupInvite, invite_id)

    async def get_pending_invite(
        self, group_id: uuid.UUID, invitee_id: uuid.UUID
    ) -> Optional[GroupInvite]:
        result = await self.session.execute(
            select(GroupInvite).where(
                GroupInvite.group_id == group_id,
                GroupInvite.invitee_id == invitee_id,
                GroupInvite.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_invites(
        self, group_id: uuid.UUID
    ) -> Sequence[GroupInvite]:
        result = await self.session.execute(
            select(GroupInvite)
            .where(
                GroupInvite.group_id == group_id,
                GroupInvite.status == "pending",
            )
            .order_by(GroupInvite.created_at.desc())
        )
        return result.scalars().all()

    async def list_my_pending_invites(
        self, invitee_id: uuid.UUID
    ) -> Sequence[GroupInvite]:
        result = await self.session.execute(
            select(GroupInvite)
            .join(HubGroup, HubGroup.id == GroupInvite.group_id)
            .where(
                GroupInvite.invitee_id == invitee_id,
                GroupInvite.status == "pending",
                HubGroup.deleted_at.is_(None),
            )
            .order_by(GroupInvite.created_at.desc())
        )
        return result.scalars().all()

    async def add_invite(self, row: GroupInvite) -> GroupInvite:
        self.session.add(row)
        await self.session.flush()
        return row

    async def cancel_pending_for_group(self, group_id: uuid.UUID) -> int:
        rows = await self.list_pending_invites(group_id)
        now = datetime.now(timezone.utc)
        count = 0
        for row in rows:
            row.status = "cancelled"
            row.responded_at = now
            count += 1
        if count:
            await self.session.flush()
        return count

    # ----- channels / messages / meetings / mcp -----

    async def list_channels(self, group_id: uuid.UUID) -> Sequence[GroupChannel]:
        result = await self.session.execute(
            select(GroupChannel)
            .where(GroupChannel.group_id == group_id)
            .order_by(GroupChannel.sort_order.asc(), GroupChannel.created_at.asc())
        )
        return result.scalars().all()

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[GroupChannel]:
        return await self.session.get(GroupChannel, channel_id)

    async def get_channel_by_slug(
        self, group_id: uuid.UUID, slug: str
    ) -> Optional[GroupChannel]:
        result = await self.session.execute(
            select(GroupChannel).where(
                GroupChannel.group_id == group_id,
                GroupChannel.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def add_channel(self, row: GroupChannel) -> GroupChannel:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_messages(
        self,
        channel_id: uuid.UUID,
        *,
        limit: int = 80,
        before: Optional[datetime] = None,
    ) -> Sequence[GroupMessage]:
        stmt = (
            select(GroupMessage)
            .where(GroupMessage.channel_id == channel_id)
            .order_by(GroupMessage.created_at.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = stmt.where(GroupMessage.created_at < before)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def add_message(self, row: GroupMessage) -> GroupMessage:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_meetings(self, group_id: uuid.UUID) -> Sequence[GroupMeeting]:
        result = await self.session.execute(
            select(GroupMeeting)
            .where(GroupMeeting.group_id == group_id)
            .order_by(GroupMeeting.starts_at.desc())
            .limit(50)
        )
        return result.scalars().all()

    async def add_meeting(self, row: GroupMeeting) -> GroupMeeting:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_mcp(self, group_id: uuid.UUID) -> Sequence[GroupMcpConnection]:
        result = await self.session.execute(
            select(GroupMcpConnection)
            .where(GroupMcpConnection.group_id == group_id)
            .order_by(GroupMcpConnection.created_at.asc())
        )
        return result.scalars().all()

    async def get_mcp(self, mcp_id: uuid.UUID) -> Optional[GroupMcpConnection]:
        return await self.session.get(GroupMcpConnection, mcp_id)

    async def add_mcp(self, row: GroupMcpConnection) -> GroupMcpConnection:
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete_mcp(self, row: GroupMcpConnection) -> None:
        await self.session.delete(row)
        await self.session.flush()
