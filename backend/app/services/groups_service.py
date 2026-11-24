# pylint: disable=too-many-lines  # cohesive module; splitting is a separate refactor
"""Collaboration groups — Discord-like channels + WhatsApp-like chat + DMs."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.dependencies.phase23_auth import Actor
from app.integrations import mcp_client
from app.integrations.teams_webhook import build_meeting_card, post_webhook
from app.models.groups import (
    GroupChannel,
    GroupInvite,
    GroupMeeting,
    GroupMember,
    GroupMessage,
    GroupMcpConnection,
    GroupPoll,
    GroupPollVote,
    HubGroup,
)
from app.models.idea import Idea
from app.models.user import User
from app.repositories.groups_repository import GroupsRepository
from app.repositories.tracker_repository import TrackerRepository
from app.schemas.groups import (
    DmCreateIn,
    GroupChannelCreateIn,
    GroupChannelOut,
    GroupCreateIn,
    GroupInviteCreateIn,
    GroupInviteOut,
    GroupMeetingCreateIn,
    GroupMeetingOut,
    GroupMemberOut,
    GroupMessageCreateIn,
    GroupMessageOut,
    GroupMcpConnectionCreateIn,
    GroupMcpConnectionOut,
    GroupOut,
    GroupSummaryOut,
    GroupUpdateIn,
    McpToolCallIn,
    McpToolCallOut,
    PollCreateIn,
    PollOut,
    PollVoteIn,
)
from app.services.account_service import (
    ALLOWED_AVATAR_TYPES,
    MAX_AVATAR_BYTES,
    uploads_root,
)
from app.services.mcp_oauth_service import McpOAuthService
from app.services.notification_service import notify_users
from app.trackers.crypto import decrypt_credentials, encrypt_credentials

logger = logging.getLogger("idea_hub.groups")

DEFAULT_CHANNELS: tuple[tuple[str, str, str, int], ...] = (
    ("general", "General", "Day-to-day chat", 0),
    ("decisions", "Decisions", "Decisions and rationale", 1),
    ("blockers", "Blockers", "Things blocking progress", 2),
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    s = _SLUG_RE.sub("-", (name or "").strip().lower()).strip("-")
    return (s or "channel")[:64]


def _poll_is_closed(poll: GroupPoll) -> bool:
    """Closed manually, or past its end time."""
    if poll.closed_at is not None:
        return True
    return poll.ends_at is not None and poll.ends_at <= _now()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def dm_pair_key(user_a: uuid.UUID, user_b: uuid.UUID) -> str:
    """Stable sorted key for idempotent 1:1 DM threads."""
    a, b = sorted((str(user_a), str(user_b)))
    return f"{a}:{b}"


def group_avatar_public_url(filename: str) -> str:
    return f"/uploads/group-avatars/{filename}"


class GroupsService:
    # pylint: disable=too-many-public-methods  # one cohesive service/repo surface
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = GroupsRepository(session)
        self.trackers = TrackerRepository(session)

    # ----- groups CRUD -----

    async def list_mine(
        self, actor: Actor, *, kind: Optional[str] = None
    ) -> list[GroupSummaryOut]:
        rows = await self.repo.list_for_user(actor.id, kind=kind)
        out: list[GroupSummaryOut] = []
        for g in rows:
            member = await self.repo.get_member(g.id, actor.id)
            peer_user = await self._dm_peer_user(g, actor.id)
            display_name = g.name
            if peer_user:
                display_name = peer_user.name or peer_user.email or g.name
            out.append(
                GroupSummaryOut(
                    id=g.id,
                    name=display_name,
                    description=g.description,
                    kind=g.kind or "group",
                    idea_id=g.idea_id,
                    avatar_url=g.avatar_url,
                    created_by=g.created_by,
                    created_at=g.created_at,
                    member_count=await self.repo.member_count(g.id),
                    my_role=member.role if member else None,
                    peer_user_id=peer_user.id if peer_user else None,
                    peer_avatar=peer_user.avatar if peer_user else 1,
                    peer_avatar_url=(
                        getattr(peer_user, "avatar_url", None)
                        if peer_user
                        else None
                    ),
                )
            )
        return out

    async def create(self, body: GroupCreateIn, actor: Actor) -> GroupOut:
        idea: Optional[Idea] = None
        if body.idea_id:
            idea = await self.session.get(Idea, body.idea_id)
            if not idea:
                raise HTTPException(404, "Idea not found.")
            existing = await self.repo.get_by_idea(idea.id)
            if existing:
                raise HTTPException(
                    400,
                    "This idea already has a linked group. Open it from Groups.",
                )

        group = HubGroup(
            name=body.name.strip(),
            description=(body.description or "").strip(),
            kind="group",
            idea_id=idea.id if idea else None,
            created_by=actor.id,
        )
        await self.repo.add_group(group)
        await self.repo.add_member(
            GroupMember(group_id=group.id, user_id=actor.id, role="owner")
        )
        for slug, name, desc, order in DEFAULT_CHANNELS:
            await self.repo.add_channel(
                GroupChannel(
                    group_id=group.id,
                    slug=slug,
                    name=name,
                    description=desc,
                    kind="text",
                    sort_order=order,
                    created_by=actor.id,
                )
            )
        general = await self.repo.get_channel_by_slug(group.id, "general")
        if general:
            await self.repo.add_message(
                GroupMessage(
                    channel_id=general.id,
                    author_id=actor.id,
                    body=(
                        f"**{group.name}** is ready. Invite teammates from Members "
                        "— they must Accept before joining."
                    ),
                    message_type="system",
                    meta={"event": "group_created"},
                )
            )
        await self.session.commit()
        return await self.get(group.id, actor)

    async def get(self, group_id: uuid.UUID, actor: Actor) -> GroupOut:
        group = await self._require_group(group_id)
        await self._assert_can_view(group, actor)
        return await self._to_out(group, actor)

    async def get_for_idea(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> Optional[GroupOut]:
        idea = await self.session.get(Idea, idea_id)
        if not idea:
            raise HTTPException(404, "Idea not found.")
        group = await self.repo.get_by_idea(idea_id)
        if not group:
            return None
        # Linked group is only returned when the actor is a member.
        me = await self.repo.get_member(group.id, actor.id)
        if not me:
            return None
        return await self._to_out(group, actor)

    async def update(
        self, group_id: uuid.UUID, body: GroupUpdateIn, actor: Actor
    ) -> GroupOut:
        group = await self._require_group(group_id)
        if group.kind == "dm":
            raise HTTPException(400, "Direct messages cannot be renamed here.")
        self._assert_can_manage(
            group, actor, await self.repo.get_member(group.id, actor.id)
        )
        if body.name is not None:
            group.name = body.name.strip()
        if body.description is not None:
            group.description = body.description.strip()
        if body.clear_idea:
            group.idea_id = None
        elif body.idea_id is not None:
            idea = await self.session.get(Idea, body.idea_id)
            if not idea:
                raise HTTPException(404, "Idea not found.")
            other = await self.repo.get_by_idea(idea.id)
            if other and other.id != group.id:
                raise HTTPException(
                    400, "That idea is already linked to another group."
                )
            group.idea_id = idea.id
        if body.clear_avatar:
            await self._clear_local_avatar(group)
            group.avatar_url = None
        elif body.avatar_url is not None:
            url = body.avatar_url.strip()
            if url and not (
                url.startswith("http://")
                or url.startswith("https://")
                or url.startswith("/uploads/")
            ):
                raise HTTPException(400, "avatar_url must be http(s) or /uploads/…")
            group.avatar_url = url or None
        group.updated_at = _now()
        await self.session.commit()
        return await self.get(group.id, actor)

    async def soft_delete(self, group_id: uuid.UUID, actor: Actor) -> None:
        group = await self._require_group(group_id)
        if group.kind == "dm":
            raise HTTPException(400, "Direct messages cannot be deleted this way.")
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)
        group.deleted_at = _now()
        group.updated_at = _now()
        await self.repo.cancel_pending_for_group(group.id)
        await self.session.commit()

    async def upload_avatar(
        self, group_id: uuid.UUID, actor: Actor, file: UploadFile
    ) -> GroupOut:
        group = await self._require_group(group_id)
        if group.kind == "dm":
            raise HTTPException(400, "Direct messages use profile avatars.")
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)

        content_type = (file.content_type or "").split(";")[0].strip().lower()
        ext = ALLOWED_AVATAR_TYPES.get(content_type)
        if not ext:
            raise HTTPException(400, "Avatar must be JPEG, PNG, WebP, or GIF")
        data = await file.read(MAX_AVATAR_BYTES + 1)
        if not data:
            raise HTTPException(400, "Empty avatar file")
        if len(data) > MAX_AVATAR_BYTES:
            raise HTTPException(400, "Avatar must be 2 MB or smaller")

        await self._clear_local_avatar(group)
        root = uploads_root() / "group-avatars"
        root.mkdir(parents=True, exist_ok=True)
        filename = f"{group.id}_{uuid.uuid4().hex[:12]}{ext}"
        (root / filename).write_bytes(data)
        group.avatar_url = group_avatar_public_url(filename)
        group.updated_at = _now()
        await self.session.commit()
        return await self.get(group.id, actor)

    # ----- invites -----

    async def list_my_invites(self, actor: Actor) -> list[GroupInviteOut]:
        rows = await self.repo.list_my_pending_invites(actor.id)
        return [await self._invite_out(r) for r in rows]

    async def list_group_invites(
        self, group_id: uuid.UUID, actor: Actor
    ) -> list[GroupInviteOut]:
        group = await self._require_group(group_id)
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)
        rows = await self.repo.list_pending_invites(group.id)
        return [await self._invite_out(r) for r in rows]

    async def invite_member(
        self, group_id: uuid.UUID, body: GroupInviteCreateIn, actor: Actor
    ) -> GroupInviteOut:
        group = await self._require_group(group_id)
        if group.kind == "dm":
            raise HTTPException(400, "Cannot invite to a direct message.")
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)

        invitee = await self.session.get(User, body.user_id)
        if not invitee or invitee.status != "active":
            raise HTTPException(404, "User not found.")
        if invitee.id == actor.id:
            raise HTTPException(400, "You are already in this group.")
        if await self.repo.get_member(group.id, invitee.id):
            raise HTTPException(400, "User is already a member.")
        pending = await self.repo.get_pending_invite(group.id, invitee.id)
        if pending:
            raise HTTPException(400, "An invite is already pending for this user.")

        invite = GroupInvite(
            group_id=group.id,
            invitee_id=invitee.id,
            invited_by=actor.id,
            role=body.role,
            status="pending",
        )
        await self.repo.add_invite(invite)

        inviter_name = actor.name or "Someone"
        await notify_users(
            self.session,
            [invitee.id],
            kind="group_invite",
            text=f'{inviter_name} invited you to join “{group.name}”.',
            href="/groups?tab=invites",
            idea_id=group.idea_id,
            idea_title=group.name,
            exclude=actor.id,
            meta={
                "event": "group_invite",
                "group_id": str(group.id),
                "invite_id": str(invite.id),
            },
            send_email=True,
        )
        await self.session.commit()
        await self.session.refresh(invite)
        return await self._invite_out(invite)

    async def accept_invite(
        self, invite_id: uuid.UUID, actor: Actor
    ) -> GroupOut:
        invite = await self._require_pending_invite(invite_id, actor)
        group = await self._require_group(invite.group_id)
        existing = await self.repo.get_member(group.id, actor.id)
        if not existing:
            await self.repo.add_member(
                GroupMember(
                    group_id=group.id,
                    user_id=actor.id,
                    role=invite.role if invite.role in ("admin", "member") else "member",
                )
            )
        invite.status = "accepted"
        invite.responded_at = _now()
        group.updated_at = _now()
        await notify_users(
            self.session,
            [invite.invited_by],
            kind="collab",
            text=f"{actor.name or 'Someone'} joined “{group.name}”.",
            href=f"/groups/{group.id}",
            exclude=actor.id,
            meta={"event": "group_invite_accepted", "group_id": str(group.id)},
            send_email=False,
        )

        general = await self.repo.get_channel_by_slug(group.id, "general")
        if general:
            await self.repo.add_message(
                GroupMessage(
                    channel_id=general.id,
                    author_id=actor.id,
                    body=f"**{actor.name or 'Someone'}** joined the group.",
                    message_type="system",
                    meta={"event": "member_joined", "user_id": str(actor.id)},
                )
            )
        await self.session.commit()
        return await self.get(group.id, actor)

    async def decline_invite(self, invite_id: uuid.UUID, actor: Actor) -> None:
        invite = await self._require_pending_invite(invite_id, actor)
        invite.status = "declined"
        invite.responded_at = _now()
        group = await self.repo.get(invite.group_id)
        await notify_users(
            self.session,
            [invite.invited_by],
            kind="collab",
            text=(
                f"{actor.name or 'Someone'} declined your invite to "
                f"“{group.name if group else 'a group'}”."
            ),
            href=f"/groups/{invite.group_id}" if group else "/groups",
            exclude=actor.id,
            meta={"event": "group_invite_declined"},
            send_email=False,
        )
        await self.session.commit()

    async def cancel_invite(
        self, group_id: uuid.UUID, invite_id: uuid.UUID, actor: Actor
    ) -> None:
        group = await self._require_group(group_id)
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)
        invite = await self.repo.get_invite(invite_id)
        if not invite or invite.group_id != group.id:
            raise HTTPException(404, "Invite not found.")
        if invite.status != "pending":
            raise HTTPException(400, "Invite is no longer pending.")
        invite.status = "cancelled"
        invite.responded_at = _now()
        await self.session.commit()

    async def remove_member(
        self, group_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
    ) -> None:
        group = await self._require_group(group_id)
        if group.kind == "dm":
            raise HTTPException(400, "Leave a DM from Messages instead.")
        me = await self.repo.get_member(group.id, actor.id)
        target = await self.repo.get_member(group.id, user_id)
        if not target:
            raise HTTPException(404, "Member not found.")
        if target.role == "owner":
            raise HTTPException(400, "Cannot remove the group owner.")
        if user_id != actor.id:
            self._assert_can_manage(group, actor, me)
            is_owner = group.created_by == actor.id or (
                me is not None and me.role == "owner"
            )
            if target.role == "admin" and not is_owner:
                raise HTTPException(
                    403, "Only the group owner can remove an admin."
                )
        await self.repo.delete_member(target)
        await self.session.commit()

    # ----- DMs -----

    async def create_or_get_dm(self, body: DmCreateIn, actor: Actor) -> GroupOut:
        if body.user_id == actor.id:
            raise HTTPException(400, "Cannot start a DM with yourself.")
        peer = await self.session.get(User, body.user_id)
        if not peer or peer.status != "active":
            raise HTTPException(404, "User not found.")

        key = dm_pair_key(actor.id, peer.id)
        existing = await self.repo.get_dm_by_pair_key(key)
        if existing:
            # Ensure both are members (repair edge cases).
            for uid in (actor.id, peer.id):
                if not await self.repo.get_member(existing.id, uid):
                    await self.repo.add_member(
                        GroupMember(
                            group_id=existing.id,
                            user_id=uid,
                            role="member",
                        )
                    )
            await self.session.commit()
            return await self.get(existing.id, actor)

        peer_name = peer.name or peer.email or "Direct message"
        group = HubGroup(
            name=peer_name,
            description="",
            kind="dm",
            dm_pair_key=key,
            created_by=actor.id,
        )
        await self.repo.add_group(group)
        await self.repo.add_member(
            GroupMember(group_id=group.id, user_id=actor.id, role="member")
        )
        await self.repo.add_member(
            GroupMember(group_id=group.id, user_id=peer.id, role="member")
        )
        channel = GroupChannel(
            group_id=group.id,
            slug="dm",
            name="Chat",
            description="Direct message",
            kind="text",
            sort_order=0,
            created_by=actor.id,
        )
        await self.repo.add_channel(channel)
        await self.session.commit()
        return await self.get(group.id, actor)

    # ----- channels / messages -----

    async def create_channel(
        self, group_id: uuid.UUID, body: GroupChannelCreateIn, actor: Actor
    ) -> GroupChannelOut:
        group = await self._require_group(group_id)
        if group.kind == "dm":
            raise HTTPException(400, "Direct messages have a single chat thread.")
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)
        slug = _slugify(body.slug or body.name)
        if await self.repo.get_channel_by_slug(group.id, slug):
            raise HTTPException(400, f"Channel '#{slug}' already exists.")
        channels = await self.repo.list_channels(group.id)
        row = GroupChannel(
            group_id=group.id,
            slug=slug,
            name=body.name.strip(),
            description=(body.description or "").strip(),
            kind=body.kind,
            sort_order=len(channels),
            created_by=actor.id,
        )
        await self.repo.add_channel(row)
        group.updated_at = _now()
        await self.session.commit()
        await self.session.refresh(row)
        return GroupChannelOut.model_validate(row)

    async def list_messages(
        self,
        group_id: uuid.UUID,
        channel_id: uuid.UUID,
        actor: Actor,
        *,
        limit: int = 80,
    ) -> list[GroupMessageOut]:
        group = await self._require_group(group_id)
        await self._assert_can_view(group, actor)
        channel = await self._require_channel(channel_id, group.id)
        rows = await self.repo.list_messages(channel.id, limit=min(limit, 200))
        return [GroupMessageOut.model_validate(r) for r in rows]

    async def post_message(
        self,
        group_id: uuid.UUID,
        channel_id: uuid.UUID,
        body: GroupMessageCreateIn,
        actor: Actor,
    ) -> GroupMessageOut:
        group = await self._require_group(group_id)
        if not await self._can_post(group, actor):
            raise HTTPException(403, "Only group members can post.")
        channel = await self._require_channel(channel_id, group.id)
        row = GroupMessage(
            channel_id=channel.id,
            author_id=actor.id,
            body=body.body,
            message_type="user",
            meta={},
        )
        await self.repo.add_message(row)
        group.updated_at = _now()
        if group.kind == "dm":
            peer = await self._dm_peer_user(group, actor.id)
            if peer:
                preview = body.body if len(body.body) <= 140 else body.body[:137] + "…"
                await notify_users(
                    self.session,
                    [peer.id],
                    kind="dm",
                    text=f"{actor.name or 'Someone'}: {preview}",
                    href=f"/dms/{group.id}",
                    exclude=actor.id,
                    meta={"event": "dm_message", "group_id": str(group.id)},
                    send_email=False,
                )
        await self.session.commit()
        await self.session.refresh(row)
        return GroupMessageOut.model_validate(row)

    # ----- meetings -----

    async def list_meetings(
        self, group_id: uuid.UUID, actor: Actor
    ) -> list[GroupMeetingOut]:
        group = await self._require_group(group_id)
        await self._assert_can_view(group, actor)
        rows = await self.repo.list_meetings(group.id)
        return [GroupMeetingOut.model_validate(r) for r in rows]

    async def schedule_meeting(
        self,
        group_id: uuid.UUID,
        body: GroupMeetingCreateIn,
        actor: Actor,
    ) -> GroupMeetingOut:
        group = await self._require_group(group_id)
        if not await self._can_post(group, actor):
            raise HTTPException(403, "Not allowed to schedule meetings.")
        channel: Optional[GroupChannel] = None
        if body.channel_id:
            channel = await self._require_channel(body.channel_id, group.id)
        elif body.channel_slug:
            channel = await self.repo.get_channel_by_slug(
                group.id, _slugify(body.channel_slug)
            )
        if channel is None:
            channel = await self.repo.get_channel_by_slug(group.id, "general")
            if channel is None:
                channel = await self.repo.get_channel_by_slug(group.id, "dm")

        meeting = GroupMeeting(
            group_id=group.id,
            channel_id=channel.id if channel else None,
            title=body.title.strip(),
            description=(body.description or "").strip(),
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            join_url=(body.join_url or "").strip(),
            created_by=actor.id,
            notify_via="none",
            notify_status="skipped",
            notify_detail="",
            meta={},
        )

        if body.notify_teams:
            meeting.notify_via = "teams_webhook"
            try:
                detail = await self._post_teams_meeting(group, meeting, actor)
                meeting.notify_status = "posted"
                meeting.notify_detail = detail
            except HTTPException as exc:
                meeting.notify_status = "failed"
                meeting.notify_detail = str(exc.detail)
            except Exception as exc:  # noqa: BLE001
                meeting.notify_status = "failed"
                meeting.notify_detail = str(exc)[:500]

        await self.repo.add_meeting(meeting)

        if body.announce_in_channel and channel:
            when = meeting.starts_at.isoformat()
            lines = [
                f"**Meeting:** {meeting.title}",
                f"When: {when}",
            ]
            if meeting.join_url:
                lines.append(f"Join: {meeting.join_url}")
            if meeting.description:
                lines.append(meeting.description)
            if meeting.notify_via == "teams_webhook":
                lines.append(f"Teams notify: {meeting.notify_status}")
            await self.repo.add_message(
                GroupMessage(
                    channel_id=channel.id,
                    author_id=actor.id,
                    body="\n".join(lines),
                    message_type="meeting",
                    meta={
                        "meeting_id": str(meeting.id),
                        "notify_status": meeting.notify_status,
                    },
                )
            )

        group.updated_at = _now()
        await self.session.commit()
        await self.session.refresh(meeting)
        return GroupMeetingOut.model_validate(meeting)

    # ----- MCP -----

    async def list_mcp(
        self, group_id: uuid.UUID, actor: Actor
    ) -> list[GroupMcpConnectionOut]:
        group = await self._require_group(group_id)
        await self._assert_can_view(group, actor)
        return [self._mcp_out(r) for r in await self.repo.list_mcp(group.id)]

    async def connect_mcp(
        self,
        group_id: uuid.UUID,
        body: GroupMcpConnectionCreateIn,
        actor: Actor,
    ) -> GroupMcpConnectionOut:
        group = await self._require_group(group_id)
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)

        if body.connection_id is not None:
            return await self._attach_connection_mcp(group, body.connection_id, body.label, actor)

        if body.transport == "http_jsonrpc" and not body.endpoint_url.strip():
            raise HTTPException(400, "Choose an MCP connection from Integrations.")

        label = (body.label or "default").strip() or "default"
        for existing in await self.repo.list_mcp(group.id):
            if existing.label == label:
                raise HTTPException(400, f"MCP connection '{label}' already exists.")

        transport = body.transport
        endpoint = body.endpoint_url.strip()
        if transport == "http_jsonrpc":
            try:
                mcp_client.require_https_endpoint(endpoint)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        elif transport == "stub":
            endpoint = endpoint or "stub://local"

        creds: dict[str, str] = {}
        if (body.auth_header_value or "").strip():
            creds["auth_header_value"] = body.auth_header_value.strip()
        encrypted = encrypt_credentials(creds) if creds else ""

        tools: list[dict[str, Any]] = []
        discovered_at: Optional[datetime] = None
        if transport == "stub" or body.seed_stub_tools:
            tools = list(mcp_client.STUB_TOOL_CATALOG)
            discovered_at = _now()
        elif transport == "http_jsonrpc":
            try:
                tools = await mcp_client.list_tools(
                    endpoint,
                    header_name=body.auth_header_name,
                    header_value=(body.auth_header_value or "").strip(),
                )
                discovered_at = _now()
            except Exception:  # noqa: BLE001
                tools = []

        row = GroupMcpConnection(
            group_id=group.id,
            idea_id=group.idea_id,
            label=label,
            endpoint_url=endpoint,
            auth_header_name=(body.auth_header_name or "Authorization").strip()
            or "Authorization",
            credentials_encrypted=encrypted,
            transport=transport,
            tools_cache=tools,
            last_discovered_at=discovered_at,
            created_by=actor.id,
        )
        await self.repo.add_mcp(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._mcp_out(row)

    async def _attach_connection_mcp(
        self,
        group: HubGroup,
        connection_id: uuid.UUID,
        label_in: str,
        actor: Actor,
    ) -> GroupMcpConnectionOut:
        conn = await self.trackers.get_usable_connection(connection_id, actor.id)
        if conn is None or conn.provider_id != "mcp_server":
            raise HTTPException(404, "MCP connection not found.")
        label = (label_in or "default").strip() or "default"
        if label == "default":
            label = conn.label
        for existing in await self.repo.list_mcp(group.id):
            if existing.label == label:
                raise HTTPException(400, f"MCP connection '{label}' already exists.")

        row = GroupMcpConnection(
            group_id=group.id,
            idea_id=group.idea_id,
            connection_id=conn.id,
            label=label,
            endpoint_url=str(decrypt_credentials(conn.credentials_encrypted).get("endpoint_url") or ""),
            auth_header_name="Authorization",
            credentials_encrypted="",
            transport="http_jsonrpc",
            tools_cache=[],
            created_by=actor.id,
        )
        try:
            endpoint, hname, hval = await McpOAuthService(self.session).auth_for(conn)
            row.tools_cache = await mcp_client.list_tools(endpoint, header_name=hname, header_value=hval)
            row.last_discovered_at = _now()
        except Exception:  # noqa: BLE001 — attach anyway; tools can be discovered later
            logger.info("MCP tool discovery failed on attach; leaving tools empty")
        await self.repo.add_mcp(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._mcp_out(row)

    async def _mcp_endpoint_auth(self, row: GroupMcpConnection) -> tuple[str, str, str]:
        """Endpoint and auth header for a group MCP row (refreshes OAuth tokens if needed)."""
        if row.connection_id is None:
            return row.endpoint_url, row.auth_header_name, self._mcp_auth_value(row)
        conn = await self.trackers.get_connection(row.connection_id)
        if conn is None:
            raise HTTPException(409, "This MCP connection was removed. Re-attach it from Integrations.")
        return await McpOAuthService(self.session).auth_for(conn)

    async def discover_mcp_tools(
        self, group_id: uuid.UUID, mcp_id: uuid.UUID, actor: Actor
    ) -> GroupMcpConnectionOut:
        group = await self._require_group(group_id)
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)
        row = await self.repo.get_mcp(mcp_id)
        if not row or row.group_id != group.id:
            raise HTTPException(404, "MCP connection not found.")

        if row.transport == "stub":
            row.tools_cache = list(mcp_client.STUB_TOOL_CATALOG)
            row.last_discovered_at = _now()
        else:
            endpoint, hname, value = await self._mcp_endpoint_auth(row)
            try:
                tools = await mcp_client.list_tools(
                    endpoint,
                    header_name=hname,
                    header_value=value,
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    f"Could not list MCP tools: {exc}",
                ) from exc
            row.tools_cache = tools
            row.last_discovered_at = _now()

        await self.session.commit()
        await self.session.refresh(row)
        return self._mcp_out(row)

    async def call_mcp_tool(
        self,
        group_id: uuid.UUID,
        mcp_id: uuid.UUID,
        body: McpToolCallIn,
        actor: Actor,
    ) -> McpToolCallOut:
        group = await self._require_group(group_id)
        if not await self._can_post(group, actor):
            raise HTTPException(403, "Not allowed to call MCP tools.")
        row = await self.repo.get_mcp(mcp_id)
        if not row or row.group_id != group.id:
            raise HTTPException(404, "MCP connection not found.")

        if row.transport == "stub" or body.name == "schedule_meeting":
            if body.name == "schedule_meeting":
                try:
                    meeting = await self._meeting_from_mcp_args(
                        group_id, body.arguments or {}, actor
                    )
                    return McpToolCallOut(
                        ok=True,
                        result={
                            "meeting_id": str(meeting.id),
                            "title": meeting.title,
                            "notify_status": meeting.notify_status,
                        },
                    )
                except HTTPException as exc:
                    return McpToolCallOut(ok=False, error=str(exc.detail))
            if row.transport == "stub":
                return McpToolCallOut(
                    ok=True,
                    result={
                        "stub": True,
                        "tool": body.name,
                        "echo": body.arguments,
                    },
                )

        endpoint, hname, value = await self._mcp_endpoint_auth(row)
        try:
            result = await mcp_client.call_tool(
                endpoint,
                body.name,
                body.arguments or {},
                header_name=hname,
                header_value=value,
            )
            return McpToolCallOut(ok=True, result=result)
        except Exception as exc:  # noqa: BLE001
            return McpToolCallOut(ok=False, error=str(exc)[:500])

    async def delete_mcp(
        self, group_id: uuid.UUID, mcp_id: uuid.UUID, actor: Actor
    ) -> None:
        group = await self._require_group(group_id)
        me = await self.repo.get_member(group.id, actor.id)
        self._assert_can_manage(group, actor, me)
        row = await self.repo.get_mcp(mcp_id)
        if not row or row.group_id != group.id:
            raise HTTPException(404, "MCP connection not found.")
        await self.repo.delete_mcp(row)
        await self.session.commit()

    # ----- internals -----

    async def _meeting_from_mcp_args(
        self, group_id: uuid.UUID, args: dict[str, Any], actor: Actor
    ) -> GroupMeetingOut:
        title = str(args.get("title") or "").strip()
        starts_raw = args.get("starts_at")
        if not title or not starts_raw:
            raise HTTPException(400, "schedule_meeting requires title and starts_at.")
        starts_at = (
            starts_raw
            if isinstance(starts_raw, datetime)
            else datetime.fromisoformat(str(starts_raw).replace("Z", "+00:00"))
        )
        ends_at = None
        if args.get("ends_at"):
            ends_raw = args["ends_at"]
            ends_at = (
                ends_raw
                if isinstance(ends_raw, datetime)
                else datetime.fromisoformat(str(ends_raw).replace("Z", "+00:00"))
            )
        body = GroupMeetingCreateIn(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            description=str(args.get("description") or ""),
            join_url=str(args.get("join_url") or ""),
            channel_slug=str(args.get("channel_slug") or "") or None,
            notify_teams=bool(args.get("notify_teams", True)),
            announce_in_channel=True,
        )
        return await self.schedule_meeting(group_id, body, actor)

    async def _post_teams_meeting(
        self, group: HubGroup, meeting: GroupMeeting, actor: Actor
    ) -> str:
        conn, source = await self.trackers.resolve_effective(actor.id, "teams")
        if not conn:
            raise HTTPException(
                400,
                "No Microsoft Teams connection. Connect an Incoming Webhook "
                "under Integrations (personal or org default).",
            )
        credentials = decrypt_credentials(conn.credentials_encrypted)
        settings = get_settings()
        group_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/groups/{group.id}"
        idea_title = group.name
        idea_url = group_url
        if group.idea_id:
            idea = await self.session.get(Idea, group.idea_id)
            if idea:
                idea_title = idea.title
                idea_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/ideas/{idea.id}"
        card = build_meeting_card(
            title=meeting.title,
            starts_at=meeting.starts_at,
            ends_at=meeting.ends_at,
            description=meeting.description,
            join_url=meeting.join_url,
            idea_title=idea_title,
            idea_url=idea_url,
        )
        result = await post_webhook(credentials, card)
        return f"posted via {source} connection ({result.get('status_code')})"

    async def _to_out(self, group: HubGroup, actor: Actor) -> GroupOut:
        channels = await self.repo.list_channels(group.id)
        members = await self.repo.list_members(group.id)
        me = await self.repo.get_member(group.id, actor.id)
        pending: list[GroupInviteOut] = []
        if group.kind != "dm" and self._is_manager(group, actor, me):
            for inv in await self.repo.list_pending_invites(group.id):
                pending.append(await self._invite_out(inv))

        peer_user = await self._dm_peer_user(group, actor.id)
        display_name = group.name
        if peer_user:
            display_name = peer_user.name or peer_user.email or group.name

        return GroupOut(
            id=group.id,
            name=display_name,
            description=group.description,
            kind=group.kind or "group",
            idea_id=group.idea_id,
            avatar_url=group.avatar_url,
            created_by=group.created_by,
            created_at=group.created_at,
            updated_at=group.updated_at,
            channels=[GroupChannelOut.model_validate(c) for c in channels],
            members=[await self._member_out(m) for m in members],
            pending_invites=pending,
            can_post=await self._can_post(group, actor),
            can_manage=self._is_manager(group, actor, me),
            peer_user_id=peer_user.id if peer_user else None,
            peer_avatar=peer_user.avatar if peer_user else 1,
            peer_avatar_url=(
                getattr(peer_user, "avatar_url", None) if peer_user else None
            ),
        )

    async def _member_out(self, member: GroupMember) -> GroupMemberOut:
        user = await self.session.get(User, member.user_id)
        return GroupMemberOut(
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            name=(user.name if user else "") or "",
            email=(user.email if user else "") or "",
            avatar=user.avatar if user else 1,
            avatar_url=getattr(user, "avatar_url", None) if user else None,
        )

    async def _invite_out(self, invite: GroupInvite) -> GroupInviteOut:
        group = await self.repo.get(invite.group_id)
        invitee = await self.session.get(User, invite.invitee_id)
        inviter = await self.session.get(User, invite.invited_by)
        return GroupInviteOut(
            id=invite.id,
            group_id=invite.group_id,
            group_name=group.name if group else "",
            invitee_id=invite.invitee_id,
            invited_by=invite.invited_by,
            role=invite.role,
            status=invite.status,
            created_at=invite.created_at,
            responded_at=invite.responded_at,
            invitee_name=(invitee.name if invitee else "") or "",
            invitee_email=(invitee.email if invitee else "") or "",
            invitee_avatar=invitee.avatar if invitee else 1,
            invitee_avatar_url=(
                getattr(invitee, "avatar_url", None) if invitee else None
            ),
            invited_by_name=(inviter.name if inviter else "") or "",
        )

    async def _require_pending_invite(
        self, invite_id: uuid.UUID, actor: Actor
    ) -> GroupInvite:
        invite = await self.repo.get_invite(invite_id)
        if not invite or invite.status != "pending":
            raise HTTPException(404, "Invite not found.")
        if invite.invitee_id != actor.id:
            raise HTTPException(403, "This invite is not for you.")
        return invite

    async def _require_group(self, group_id: uuid.UUID) -> HubGroup:
        group = await self.repo.get(group_id)
        if not group or group.deleted_at is not None:
            raise HTTPException(404, "Group not found.")
        return group

    async def _require_channel(
        self, channel_id: uuid.UUID, group_id: uuid.UUID
    ) -> GroupChannel:
        channel = await self.repo.get_channel(channel_id)
        if not channel or channel.group_id != group_id:
            raise HTTPException(404, "Channel not found.")
        return channel

    async def _dm_peer_user(
        self, group: HubGroup, actor_id: uuid.UUID
    ) -> Optional[User]:
        """Other participant of a DM (``None`` for normal groups)."""
        if group.kind != "dm":
            return None
        for m in await self.repo.list_members(group.id):
            if m.user_id != actor_id:
                return await self.session.get(User, m.user_id)
        return None

    async def _clear_local_avatar(self, group: HubGroup) -> None:
        url = group.avatar_url or ""
        if not url.startswith("/uploads/group-avatars/"):
            return
        root = uploads_root() / "group-avatars"
        old = root / Path(url).name
        try:
            if old.is_file() and old.resolve().parent == root.resolve():
                old.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove old group avatar %s", old)

    def _is_manager(
        self, group: HubGroup, actor: Actor, member: Optional[GroupMember]
    ) -> bool:
        if group.kind == "dm":
            return False
        if group.created_by == actor.id:
            return True
        return bool(member and member.role in ("owner", "admin"))

    def _assert_can_manage(
        self, group: HubGroup, actor: Actor, member: Optional[GroupMember]
    ) -> None:
        if self._is_manager(group, actor, member):
            return
        raise HTTPException(403, "Only group owners/admins can manage this group.")

    async def _can_post(self, group: HubGroup, actor: Actor) -> bool:
        member = await self.repo.get_member(group.id, actor.id)
        return member is not None

    async def _assert_can_view(self, group: HubGroup, actor: Actor) -> None:
        member = await self.repo.get_member(group.id, actor.id)
        if member:
            return
        raise HTTPException(403, "You are not a member of this group.")

    def _mcp_auth_value(self, row: GroupMcpConnection) -> str:
        if not row.credentials_encrypted:
            return ""
        try:
            creds = decrypt_credentials(row.credentials_encrypted)
        except Exception:  # noqa: BLE001
            return ""
        return str(creds.get("auth_header_value") or "")

    def _mcp_out(self, row: GroupMcpConnection) -> GroupMcpConnectionOut:
        return GroupMcpConnectionOut(
            id=row.id,
            group_id=row.group_id,
            idea_id=row.idea_id,
            label=row.label,
            endpoint_url=row.endpoint_url,
            auth_header_name=row.auth_header_name,
            has_auth=bool(row.credentials_encrypted),
            transport=row.transport,
            tools_cache=list(row.tools_cache or []),
            last_discovered_at=row.last_discovered_at,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # ----- polls -----

    async def list_polls(self, group_id: uuid.UUID, actor: Actor) -> list[PollOut]:
        group = await self._require_group(group_id)
        await self._assert_can_view(group, actor)
        polls = list(await self.repo.list_polls(group.id))
        votes = list(await self.repo.list_poll_votes([p.id for p in polls]))
        return [
            self._poll_out(p, [v for v in votes if v.poll_id == p.id], actor.id)
            for p in polls
        ]

    async def create_poll(
        self, group_id: uuid.UUID, body: PollCreateIn, actor: Actor
    ) -> PollOut:
        group = await self._require_group(group_id)
        if not await self._can_post(group, actor):
            raise HTTPException(403, "Only group members can create polls.")
        ends_at = body.ends_at
        if ends_at is not None and ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        if ends_at is not None and ends_at <= _now():
            raise HTTPException(400, "The end time must be in the future.")
        if body.channel_id is not None:
            channel = await self._require_channel(body.channel_id, group.id)
        else:
            channels = list(await self.repo.list_channels(group.id))
            if not channels:
                raise HTTPException(400, "This group has no channel to post the poll in.")
            channel = channels[0]
        row = GroupPoll(
            group_id=group.id,
            question=body.question,
            options=body.options,
            created_by=actor.id,
            multi_select=body.multi_select,
            ends_at=body.ends_at,
        )
        await self.repo.add_poll(row)
        # The poll appears in the channel as a chat message that points at the poll.
        await self.repo.add_message(
            GroupMessage(
                channel_id=channel.id,
                author_id=actor.id,
                body=body.question,
                message_type="poll",
                meta={"poll_id": str(row.id)},
            )
        )
        group.updated_at = _now()
        await self.session.commit()
        await self.session.refresh(row)
        return self._poll_out(row, [], actor.id)

    async def vote_poll(
        self, group_id: uuid.UUID, poll_id: uuid.UUID, body: PollVoteIn, actor: Actor
    ) -> PollOut:
        group = await self._require_group(group_id)
        if not await self._can_post(group, actor):
            raise HTTPException(403, "Only group members can vote.")
        poll = await self._require_poll(poll_id, group.id)
        if _poll_is_closed(poll):
            raise HTTPException(409, "This poll is closed.")
        if body.option_index >= len(poll.options):
            raise HTTPException(422, "Unknown poll option.")
        mine = list(await self.repo.list_user_poll_votes(poll.id, actor.id))
        same = next((v for v in mine if v.option_index == body.option_index), None)
        if poll.multi_select:
            # Multi-select: the option toggles on/off, other choices stay.
            if same:
                await self.repo.delete_poll_vote(same)
            else:
                await self.repo.add_poll_vote(
                    GroupPollVote(
                        poll_id=poll.id, user_id=actor.id, option_index=body.option_index
                    )
                )
        else:
            # Single-select: picking an option replaces the previous choice.
            for v in mine:
                if v is not same:
                    await self.repo.delete_poll_vote(v)
            if same is None:
                await self.repo.add_poll_vote(
                    GroupPollVote(
                        poll_id=poll.id, user_id=actor.id, option_index=body.option_index
                    )
                )
        await self.session.commit()
        votes = list(await self.repo.list_poll_votes([poll.id]))
        return self._poll_out(poll, votes, actor.id)

    async def close_poll(
        self, group_id: uuid.UUID, poll_id: uuid.UUID, actor: Actor
    ) -> PollOut:
        group = await self._require_group(group_id)
        member = await self.repo.get_member(group.id, actor.id)
        poll = await self._require_poll(poll_id, group.id)
        if poll.created_by != actor.id and not self._is_manager(group, actor, member):
            raise HTTPException(403, "Only the poll creator or group admins can close it.")
        if poll.closed_at is None:
            poll.closed_at = _now()
        await self.session.commit()
        votes = list(await self.repo.list_poll_votes([poll.id]))
        return self._poll_out(poll, votes, actor.id)

    async def _require_poll(self, poll_id: uuid.UUID, group_id: uuid.UUID) -> GroupPoll:
        poll = await self.repo.get_poll(poll_id)
        if not poll or poll.group_id != group_id:
            raise HTTPException(404, "Poll not found.")
        return poll

    def _poll_out(
        self, poll: GroupPoll, votes: list[GroupPollVote], me: uuid.UUID
    ) -> PollOut:
        counts = [0] * len(poll.options)
        my_votes: list[int] = []
        for v in votes:
            if 0 <= v.option_index < len(counts):
                counts[v.option_index] += 1
            if v.user_id == me:
                my_votes.append(v.option_index)
        return PollOut(
            id=poll.id,
            group_id=poll.group_id,
            question=poll.question,
            options=list(poll.options),
            created_by=poll.created_by,
            closed_at=poll.closed_at or (poll.ends_at if _poll_is_closed(poll) else None),
            ends_at=poll.ends_at,
            created_at=poll.created_at,
            multi_select=bool(poll.multi_select),
            counts=counts,
            total_votes=sum(counts),
            my_votes=sorted(my_votes),
        )
