"""Collaboration groups HTTP API — CRUD, invites, DMs, channels, chat, meetings, MCP."""

from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, File, Query, Response, UploadFile

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.groups import (
    DmCreateIn,
    GroupChannelCreateIn,
    GroupChannelOut,
    GroupCreateIn,
    GroupInviteCreateIn,
    GroupInviteOut,
    GroupMeetingCreateIn,
    GroupMeetingOut,
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
from app.services.groups_service import GroupsService

router = APIRouter(tags=["groups"])


@router.get(
    "/groups",
    response_model=list[GroupSummaryOut],
    summary="List my groups / DMs (accepted membership only)",
)
async def list_groups(
    session: DbSession,
    actor: RequireActor,
    kind: Optional[Literal["group", "dm"]] = Query(
        default=None, description="Filter by kind; omit for all"
    ),
) -> list[GroupSummaryOut]:
    return await GroupsService(session).list_mine(actor, kind=kind)


@router.post(
    "/groups",
    response_model=GroupOut,
    status_code=201,
    summary="Create a group (no idea required)",
)
async def create_group(
    body: GroupCreateIn, session: DbSession, actor: RequireActor
) -> GroupOut:
    return await GroupsService(session).create(body, actor)


@router.get(
    "/groups/invites/mine",
    response_model=list[GroupInviteOut],
    summary="Pending invites for the current user",
)
async def my_invites(
    session: DbSession, actor: RequireActor
) -> list[GroupInviteOut]:
    return await GroupsService(session).list_my_invites(actor)


@router.post(
    "/groups/invites/{invite_id}/accept",
    response_model=GroupOut,
    summary="Accept a group invite",
)
async def accept_invite(
    invite_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> GroupOut:
    return await GroupsService(session).accept_invite(invite_id, actor)


@router.post(
    "/groups/invites/{invite_id}/decline",
    status_code=204,
    summary="Decline a group invite",
)
async def decline_invite(
    invite_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> Response:
    await GroupsService(session).decline_invite(invite_id, actor)
    return Response(status_code=204)


@router.post(
    "/groups/dms",
    response_model=GroupOut,
    status_code=201,
    summary="Create or get a 1:1 DM thread with a user",
)
async def open_dm(
    body: DmCreateIn, session: DbSession, actor: RequireActor
) -> GroupOut:
    return await GroupsService(session).create_or_get_dm(body, actor)


@router.get("/groups/{group_id}", response_model=GroupOut, summary="Get group detail")
async def get_group(
    group_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> GroupOut:
    return await GroupsService(session).get(group_id, actor)


@router.patch(
    "/groups/{group_id}",
    response_model=GroupOut,
    summary="Update group (name, description, link/unlink idea, avatar URL)",
)
async def update_group(
    group_id: uuid.UUID,
    body: GroupUpdateIn,
    session: DbSession,
    actor: RequireActor,
) -> GroupOut:
    return await GroupsService(session).update(group_id, body, actor)


@router.delete(
    "/groups/{group_id}",
    status_code=204,
    summary="Soft-delete a group (owner/admin only)",
)
async def delete_group(
    group_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> Response:
    await GroupsService(session).soft_delete(group_id, actor)
    return Response(status_code=204)


@router.post(
    "/groups/{group_id}/avatar",
    response_model=GroupOut,
    summary="Upload group avatar (owner/admin only)",
)
async def upload_group_avatar(
    group_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
    file: UploadFile = File(..., description="Avatar image file"),
) -> GroupOut:
    return await GroupsService(session).upload_avatar(group_id, actor, file)


@router.get(
    "/groups/{group_id}/invites",
    response_model=list[GroupInviteOut],
    summary="List pending invites for a group (admin)",
)
async def list_group_invites(
    group_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[GroupInviteOut]:
    return await GroupsService(session).list_group_invites(group_id, actor)


@router.post(
    "/groups/{group_id}/invites",
    response_model=GroupInviteOut,
    status_code=201,
    summary="Invite a user by id (admin/owner; invitee must accept)",
)
async def invite_member(
    group_id: uuid.UUID,
    body: GroupInviteCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> GroupInviteOut:
    return await GroupsService(session).invite_member(group_id, body, actor)


@router.delete(
    "/groups/{group_id}/invites/{invite_id}",
    status_code=204,
    summary="Cancel a pending invite (admin/owner)",
)
async def cancel_invite(
    group_id: uuid.UUID,
    invite_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> Response:
    await GroupsService(session).cancel_invite(group_id, invite_id, actor)
    return Response(status_code=204)


@router.delete(
    "/groups/{group_id}/members/{user_id}",
    status_code=204,
    summary="Remove a member (or leave)",
)
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> Response:
    await GroupsService(session).remove_member(group_id, user_id, actor)
    return Response(status_code=204)


@router.post(
    "/groups/{group_id}/channels",
    response_model=GroupChannelOut,
    status_code=201,
)
async def create_channel(
    group_id: uuid.UUID,
    body: GroupChannelCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> GroupChannelOut:
    return await GroupsService(session).create_channel(group_id, body, actor)


@router.get(
    "/groups/{group_id}/channels/{channel_id}/messages",
    response_model=list[GroupMessageOut],
)
async def list_messages(
    group_id: uuid.UUID,
    channel_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
    limit: int = Query(default=80, ge=1, le=200),
) -> list[GroupMessageOut]:
    return await GroupsService(session).list_messages(
        group_id, channel_id, actor, limit=limit
    )


@router.post(
    "/groups/{group_id}/channels/{channel_id}/messages",
    response_model=GroupMessageOut,
    status_code=201,
)
async def post_message(
    group_id: uuid.UUID,
    channel_id: uuid.UUID,
    body: GroupMessageCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> GroupMessageOut:
    return await GroupsService(session).post_message(
        group_id, channel_id, body, actor
    )


@router.get("/groups/{group_id}/meetings", response_model=list[GroupMeetingOut])
async def list_meetings(
    group_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[GroupMeetingOut]:
    return await GroupsService(session).list_meetings(group_id, actor)


@router.post(
    "/groups/{group_id}/meetings",
    response_model=GroupMeetingOut,
    status_code=201,
)
async def schedule_meeting(
    group_id: uuid.UUID,
    body: GroupMeetingCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> GroupMeetingOut:
    return await GroupsService(session).schedule_meeting(group_id, body, actor)


@router.get("/groups/{group_id}/mcp", response_model=list[GroupMcpConnectionOut])
async def list_mcp(
    group_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[GroupMcpConnectionOut]:
    return await GroupsService(session).list_mcp(group_id, actor)


@router.post(
    "/groups/{group_id}/mcp",
    response_model=GroupMcpConnectionOut,
    status_code=201,
)
async def connect_mcp(
    group_id: uuid.UUID,
    body: GroupMcpConnectionCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> GroupMcpConnectionOut:
    return await GroupsService(session).connect_mcp(group_id, body, actor)


@router.post(
    "/groups/{group_id}/mcp/{mcp_id}/discover",
    response_model=GroupMcpConnectionOut,
)
async def discover_mcp(
    group_id: uuid.UUID,
    mcp_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> GroupMcpConnectionOut:
    return await GroupsService(session).discover_mcp_tools(group_id, mcp_id, actor)


@router.post(
    "/groups/{group_id}/mcp/{mcp_id}/call",
    response_model=McpToolCallOut,
)
async def call_mcp(
    group_id: uuid.UUID,
    mcp_id: uuid.UUID,
    body: McpToolCallIn,
    session: DbSession,
    actor: RequireActor,
) -> McpToolCallOut:
    return await GroupsService(session).call_mcp_tool(
        group_id, mcp_id, body, actor
    )


@router.delete("/groups/{group_id}/mcp/{mcp_id}", status_code=204)
async def delete_mcp(
    group_id: uuid.UUID,
    mcp_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> Response:
    await GroupsService(session).delete_mcp(group_id, mcp_id, actor)
    return Response(status_code=204)


@router.get(
    "/ideas/{idea_id}/group",
    response_model=Optional[GroupOut],
    summary="Linked group for an idea (null if none or not a member)",
)
async def idea_group(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> Optional[GroupOut]:
    return await GroupsService(session).get_for_idea(idea_id, actor)


@router.get("/groups/{group_id}/polls", response_model=list[PollOut])
async def list_polls(
    group_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[PollOut]:
    return await GroupsService(session).list_polls(group_id, actor)


@router.post("/groups/{group_id}/polls", response_model=PollOut, status_code=201)
async def create_poll(
    group_id: uuid.UUID,
    body: PollCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> PollOut:
    return await GroupsService(session).create_poll(group_id, body, actor)


@router.post("/groups/{group_id}/polls/{poll_id}/vote", response_model=PollOut)
async def vote_poll(
    group_id: uuid.UUID,
    poll_id: uuid.UUID,
    body: PollVoteIn,
    session: DbSession,
    actor: RequireActor,
) -> PollOut:
    return await GroupsService(session).vote_poll(group_id, poll_id, body, actor)


@router.post("/groups/{group_id}/polls/{poll_id}/close", response_model=PollOut)
async def close_poll(
    group_id: uuid.UUID,
    poll_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> PollOut:
    return await GroupsService(session).close_poll(group_id, poll_id, actor)
