"""Team collaboration space HTTP API — channels, meetings, custom MCP.

Mounted by ``phase456_register.include_phase456_routers``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.team_space import (
    IdeaMcpConnectionCreateIn,
    IdeaMcpConnectionOut,
    McpToolCallIn,
    McpToolCallOut,
    TeamChannelCreateIn,
    TeamChannelOut,
    TeamMeetingCreateIn,
    TeamMeetingOut,
    TeamMessageCreateIn,
    TeamMessageOut,
    TeamSpaceOut,
)
from app.services.team_space_service import TeamSpaceService

router = APIRouter(tags=["team-space"])


@router.get(
    "/ideas/{idea_id}/team-space",
    response_model=TeamSpaceOut,
    summary="Get or create the idea team collaboration space",
)
async def get_space(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> TeamSpaceOut:
    return await TeamSpaceService(session).get_or_create_space(idea_id, actor)


@router.post(
    "/ideas/{idea_id}/team-space/channels",
    response_model=TeamChannelOut,
    status_code=201,
    summary="Create a channel in the team space",
)
async def create_channel(
    idea_id: uuid.UUID,
    body: TeamChannelCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> TeamChannelOut:
    return await TeamSpaceService(session).create_channel(idea_id, body, actor)


@router.get(
    "/ideas/{idea_id}/team-space/channels/{channel_id}/messages",
    response_model=list[TeamMessageOut],
    summary="List messages in a channel",
)
async def list_messages(
    idea_id: uuid.UUID,
    channel_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
    limit: int = Query(default=80, ge=1, le=200),
) -> list[TeamMessageOut]:
    return await TeamSpaceService(session).list_messages(
        idea_id, channel_id, actor, limit=limit
    )


@router.post(
    "/ideas/{idea_id}/team-space/channels/{channel_id}/messages",
    response_model=TeamMessageOut,
    status_code=201,
    summary="Post a message to a channel",
)
async def post_message(
    idea_id: uuid.UUID,
    channel_id: uuid.UUID,
    body: TeamMessageCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> TeamMessageOut:
    return await TeamSpaceService(session).post_message(
        idea_id, channel_id, body, actor
    )


@router.get(
    "/ideas/{idea_id}/team-space/meetings",
    response_model=list[TeamMeetingOut],
    summary="List scheduled meetings for the team space",
)
async def list_meetings(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[TeamMeetingOut]:
    return await TeamSpaceService(session).list_meetings(idea_id, actor)


@router.post(
    "/ideas/{idea_id}/team-space/meetings",
    response_model=TeamMeetingOut,
    status_code=201,
    summary="Schedule a meeting (optional Teams webhook + channel announce)",
)
async def schedule_meeting(
    idea_id: uuid.UUID,
    body: TeamMeetingCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> TeamMeetingOut:
    return await TeamSpaceService(session).schedule_meeting(idea_id, body, actor)


@router.get(
    "/ideas/{idea_id}/team-space/mcp",
    response_model=list[IdeaMcpConnectionOut],
    summary="List custom MCP connections for this team space",
)
async def list_mcp(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[IdeaMcpConnectionOut]:
    return await TeamSpaceService(session).list_mcp(idea_id, actor)


@router.post(
    "/ideas/{idea_id}/team-space/mcp",
    response_model=IdeaMcpConnectionOut,
    status_code=201,
    summary="Attach a custom MCP endpoint to this team space",
)
async def connect_mcp(
    idea_id: uuid.UUID,
    body: IdeaMcpConnectionCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> IdeaMcpConnectionOut:
    return await TeamSpaceService(session).connect_mcp(idea_id, body, actor)


@router.post(
    "/ideas/{idea_id}/team-space/mcp/{mcp_id}/discover",
    response_model=IdeaMcpConnectionOut,
    summary="Refresh tools/list from the MCP endpoint",
)
async def discover_mcp(
    idea_id: uuid.UUID,
    mcp_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> IdeaMcpConnectionOut:
    return await TeamSpaceService(session).discover_mcp_tools(
        idea_id, mcp_id, actor
    )


@router.post(
    "/ideas/{idea_id}/team-space/mcp/{mcp_id}/call",
    response_model=McpToolCallOut,
    summary="Call a tool on the attached MCP (Hub handles schedule_meeting)",
)
async def call_mcp(
    idea_id: uuid.UUID,
    mcp_id: uuid.UUID,
    body: McpToolCallIn,
    session: DbSession,
    actor: RequireActor,
) -> McpToolCallOut:
    return await TeamSpaceService(session).call_mcp_tool(
        idea_id, mcp_id, body, actor
    )


@router.delete(
    "/ideas/{idea_id}/team-space/mcp/{mcp_id}",
    status_code=204,
    summary="Remove a custom MCP connection",
)
async def delete_mcp(
    idea_id: uuid.UUID,
    mcp_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> None:
    await TeamSpaceService(session).delete_mcp(idea_id, mcp_id, actor)
