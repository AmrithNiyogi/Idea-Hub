"""Team collaboration space — channels, messages, meetings, custom MCP."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.dependencies.phase23_auth import Actor
from app.integrations import mcp_client
from app.integrations.teams_webhook import build_meeting_card, post_webhook
from app.models.collab import CollabRequest
from app.models.delivery import DeliveryContributor, DeliveryProject
from app.models.idea import Idea
from app.models.team_space import (
    IdeaMcpConnection,
    TeamChannel,
    TeamMeeting,
    TeamMessage,
    TeamSpace,
)
from app.repositories.team_space_repository import TeamSpaceRepository
from app.repositories.tracker_repository import TrackerRepository
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
from app.trackers.crypto import decrypt_credentials, encrypt_credentials

DEFAULT_CHANNELS: tuple[tuple[str, str, str, int], ...] = (
    ("general", "General", "Day-to-day team chat", 0),
    ("decisions", "Decisions", "Decisions and rationale", 1),
    ("blockers", "Blockers", "Things blocking progress", 2),
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    s = _SLUG_RE.sub("-", (name or "").strip().lower()).strip("-")
    return (s or "channel")[:64]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TeamSpaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TeamSpaceRepository(session)
        self.trackers = TrackerRepository(session)

    # ----- public API -----

    async def get_or_create_space(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> TeamSpaceOut:
        idea = await self._require_idea(idea_id)
        await self._assert_can_view(idea, actor)
        space = await self._ensure_space(idea, actor)
        channels = await self.repo.list_channels(space.id)
        return TeamSpaceOut(
            id=space.id,
            idea_id=space.idea_id,
            title=space.title,
            created_by=space.created_by,
            created_at=space.created_at,
            channels=[TeamChannelOut.model_validate(c) for c in channels],
            can_post=await self._can_post(idea, actor),
            can_manage=self._can_manage(idea, actor),
        )

    async def create_channel(
        self,
        idea_id: uuid.UUID,
        body: TeamChannelCreateIn,
        actor: Actor,
    ) -> TeamChannelOut:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)
        space = await self._ensure_space(idea, actor)
        slug = _slugify(body.slug or body.name)
        existing = await self.repo.get_channel_by_slug(space.id, slug)
        if existing:
            raise HTTPException(400, f"Channel '#{slug}' already exists.")
        channels = await self.repo.list_channels(space.id)
        row = TeamChannel(
            space_id=space.id,
            slug=slug,
            name=body.name.strip(),
            description=(body.description or "").strip(),
            kind=body.kind,
            sort_order=len(channels),
            created_by=actor.id,
        )
        await self.repo.add_channel(row)
        await self.session.commit()
        await self.session.refresh(row)
        return TeamChannelOut.model_validate(row)

    async def list_messages(
        self,
        idea_id: uuid.UUID,
        channel_id: uuid.UUID,
        actor: Actor,
        *,
        limit: int = 80,
    ) -> list[TeamMessageOut]:
        idea = await self._require_idea(idea_id)
        await self._assert_can_view(idea, actor)
        space = await self._ensure_space(idea, actor)
        channel = await self._require_channel_in_space(channel_id, space.id)
        rows = await self.repo.list_messages(channel.id, limit=min(limit, 200))
        return [TeamMessageOut.model_validate(r) for r in rows]

    async def post_message(
        self,
        idea_id: uuid.UUID,
        channel_id: uuid.UUID,
        body: TeamMessageCreateIn,
        actor: Actor,
    ) -> TeamMessageOut:
        idea = await self._require_idea(idea_id)
        if not await self._can_post(idea, actor):
            raise HTTPException(
                403,
                "Only the idea team (authors, owner, accepted collaborators, "
                "delivery contributors) or leads/admins can post.",
            )
        space = await self._ensure_space(idea, actor)
        channel = await self._require_channel_in_space(channel_id, space.id)
        row = TeamMessage(
            channel_id=channel.id,
            author_id=actor.id,
            body=body.body,
            message_type="user",
            meta={},
        )
        await self.repo.add_message(row)
        await self.session.commit()
        await self.session.refresh(row)
        return TeamMessageOut.model_validate(row)

    async def list_meetings(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> list[TeamMeetingOut]:
        idea = await self._require_idea(idea_id)
        await self._assert_can_view(idea, actor)
        space = await self._ensure_space(idea, actor)
        rows = await self.repo.list_meetings(space.id)
        return [TeamMeetingOut.model_validate(r) for r in rows]

    async def schedule_meeting(
        self,
        idea_id: uuid.UUID,
        body: TeamMeetingCreateIn,
        actor: Actor,
    ) -> TeamMeetingOut:
        idea = await self._require_idea(idea_id)
        if not await self._can_post(idea, actor):
            raise HTTPException(403, "Not allowed to schedule meetings for this team.")
        space = await self._ensure_space(idea, actor)

        channel: Optional[TeamChannel] = None
        if body.channel_id:
            channel = await self._require_channel_in_space(body.channel_id, space.id)
        elif body.channel_slug:
            channel = await self.repo.get_channel_by_slug(
                space.id, _slugify(body.channel_slug)
            )
        if channel is None:
            channel = await self.repo.get_channel_by_slug(space.id, "general")

        meeting = TeamMeeting(
            space_id=space.id,
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
                detail = await self._post_teams_meeting(idea, meeting, actor)
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
            msg = TeamMessage(
                channel_id=channel.id,
                author_id=actor.id,
                body="\n".join(lines),
                message_type="meeting",
                meta={
                    "meeting_id": str(meeting.id),
                    "notify_status": meeting.notify_status,
                },
            )
            await self.repo.add_message(msg)

        await self.session.commit()
        await self.session.refresh(meeting)
        return TeamMeetingOut.model_validate(meeting)

    # ----- MCP -----

    async def list_mcp(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> list[IdeaMcpConnectionOut]:
        idea = await self._require_idea(idea_id)
        await self._assert_can_view(idea, actor)
        space = await self._ensure_space(idea, actor)
        rows = await self.repo.list_mcp(space.id)
        return [self._mcp_out(r) for r in rows]

    async def connect_mcp(
        self,
        idea_id: uuid.UUID,
        body: IdeaMcpConnectionCreateIn,
        actor: Actor,
    ) -> IdeaMcpConnectionOut:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)
        space = await self._ensure_space(idea, actor)

        label = (body.label or "default").strip() or "default"
        for existing in await self.repo.list_mcp(space.id):
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

        creds = {}
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
            except Exception:  # noqa: BLE001 — keep connection; discovery optional
                tools = []

        row = IdeaMcpConnection(
            space_id=space.id,
            idea_id=idea.id,
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

    async def discover_mcp_tools(
        self, idea_id: uuid.UUID, mcp_id: uuid.UUID, actor: Actor
    ) -> IdeaMcpConnectionOut:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)
        space = await self._ensure_space(idea, actor)
        row = await self.repo.get_mcp(mcp_id)
        if not row or row.space_id != space.id:
            raise HTTPException(404, "MCP connection not found.")

        if row.transport == "stub":
            row.tools_cache = list(mcp_client.STUB_TOOL_CATALOG)
            row.last_discovered_at = _now()
        else:
            value = self._mcp_auth_value(row)
            try:
                tools = await mcp_client.list_tools(
                    row.endpoint_url,
                    header_name=row.auth_header_name,
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
        idea_id: uuid.UUID,
        mcp_id: uuid.UUID,
        body: McpToolCallIn,
        actor: Actor,
    ) -> McpToolCallOut:
        idea = await self._require_idea(idea_id)
        if not await self._can_post(idea, actor):
            raise HTTPException(403, "Not allowed to call MCP tools for this team.")
        space = await self._ensure_space(idea, actor)
        row = await self.repo.get_mcp(mcp_id)
        if not row or row.space_id != space.id:
            raise HTTPException(404, "MCP connection not found.")

        # Hub-side stub: schedule_meeting maps to our own scheduler.
        if row.transport == "stub" or body.name == "schedule_meeting":
            if body.name == "schedule_meeting":
                try:
                    meeting = await self._meeting_from_mcp_args(
                        idea_id, body.arguments or {}, actor
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
                        "note": (
                            "Stub MCP — wire a real http_jsonrpc endpoint to "
                            "invoke remote tools."
                        ),
                    },
                )

        value = self._mcp_auth_value(row)
        try:
            result = await mcp_client.call_tool(
                row.endpoint_url,
                body.name,
                body.arguments or {},
                header_name=row.auth_header_name,
                header_value=value,
            )
            return McpToolCallOut(ok=True, result=result)
        except Exception as exc:  # noqa: BLE001
            return McpToolCallOut(ok=False, error=str(exc)[:500])

    async def delete_mcp(
        self, idea_id: uuid.UUID, mcp_id: uuid.UUID, actor: Actor
    ) -> None:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)
        space = await self._ensure_space(idea, actor)
        row = await self.repo.get_mcp(mcp_id)
        if not row or row.space_id != space.id:
            raise HTTPException(404, "MCP connection not found.")
        await self.repo.delete_mcp(row)
        await self.session.commit()

    # ----- internals -----

    async def _meeting_from_mcp_args(
        self, idea_id: uuid.UUID, args: dict[str, Any], actor: Actor
    ) -> TeamMeetingOut:
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
        body = TeamMeetingCreateIn(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            description=str(args.get("description") or ""),
            join_url=str(args.get("join_url") or ""),
            channel_slug=str(args.get("channel_slug") or "") or None,
            notify_teams=bool(args.get("notify_teams", True)),
            announce_in_channel=True,
        )
        return await self.schedule_meeting(idea_id, body, actor)

    async def _post_teams_meeting(
        self, idea: Idea, meeting: TeamMeeting, actor: Actor
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
        idea_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/ideas/{idea.id}"
        card = build_meeting_card(
            title=meeting.title,
            starts_at=meeting.starts_at,
            ends_at=meeting.ends_at,
            description=meeting.description,
            join_url=meeting.join_url,
            idea_title=idea.title,
            idea_url=idea_url,
        )
        result = await post_webhook(credentials, card)
        return f"posted via {source} connection ({result.get('status_code')})"

    async def _ensure_space(self, idea: Idea, actor: Actor) -> TeamSpace:
        space = await self.repo.get_space_by_idea(idea.id)
        if space:
            return space
        space = TeamSpace(
            idea_id=idea.id,
            title=f"Team · {idea.title}"[:200],
            created_by=actor.id,
        )
        await self.repo.add_space(space)
        for slug, name, desc, order in DEFAULT_CHANNELS:
            await self.repo.add_channel(
                TeamChannel(
                    space_id=space.id,
                    slug=slug,
                    name=name,
                    description=desc,
                    kind="text",
                    sort_order=order,
                    created_by=actor.id,
                )
            )
        welcome = await self.repo.get_channel_by_slug(space.id, "general")
        if welcome:
            await self.repo.add_message(
                TeamMessage(
                    channel_id=welcome.id,
                    author_id=actor.id,
                    body=(
                        "Team space created. Use channels for day-to-day chat, "
                        "decisions, and blockers. Schedule meetings from here "
                        "to announce in-channel and optionally post to Teams."
                    ),
                    message_type="system",
                    meta={"event": "space_created"},
                )
            )
        await self.session.flush()
        return space

    async def _require_idea(self, idea_id: uuid.UUID) -> Idea:
        idea = await self.session.get(Idea, idea_id)
        if not idea:
            raise HTTPException(404, "Idea not found.")
        return idea

    async def _require_channel_in_space(
        self, channel_id: uuid.UUID, space_id: uuid.UUID
    ) -> TeamChannel:
        channel = await self.repo.get_channel(channel_id)
        if not channel or channel.space_id != space_id:
            raise HTTPException(404, "Channel not found.")
        return channel

    def _can_manage(self, idea: Idea, actor: Actor) -> bool:
        co = set(idea.co_author_ids or [])
        return bool(
            idea.owner_id == actor.id
            or idea.author_id == actor.id
            or actor.id in co
            or actor.has_role("lead", "admin", "leadership")
        )

    def _assert_can_manage(self, idea: Idea, actor: Actor) -> None:
        if self._can_manage(idea, actor):
            return
        raise HTTPException(
            403,
            "Only the owner, authors, a team lead or an administrator "
            "can manage this team space.",
        )

    async def _member_ids(self, idea: Idea) -> set[uuid.UUID]:
        members: set[uuid.UUID] = {idea.author_id}
        if idea.owner_id:
            members.add(idea.owner_id)
        for cid in idea.co_author_ids or []:
            try:
                members.add(uuid.UUID(str(cid)))
            except (ValueError, TypeError):
                continue
        collab = (
            await self.session.execute(
                select(CollabRequest.from_user_id).where(
                    CollabRequest.idea_id == idea.id,
                    CollabRequest.status == "accepted",
                )
            )
        ).scalars().all()
        members.update(collab)
        contribs = (
            await self.session.execute(
                select(DeliveryContributor.user_id)
                .join(
                    DeliveryProject,
                    DeliveryContributor.project_id == DeliveryProject.id,
                )
                .where(DeliveryProject.idea_id == idea.id)
            )
        ).scalars().all()
        members.update(contribs)
        return members

    async def _can_post(self, idea: Idea, actor: Actor) -> bool:
        if actor.has_role("lead", "admin", "leadership"):
            return True
        if self._can_manage(idea, actor):
            return True
        return actor.id in await self._member_ids(idea)

    async def _assert_can_view(self, idea: Idea, actor: Actor) -> None:
        # Signed-in users can view spaces for non-draft ideas they can see;
        # drafts limited to authors / leads.
        if idea.is_draft or idea.status == "draft":
            if self._can_manage(idea, actor) or await self._can_post(idea, actor):
                return
            raise HTTPException(403, "Draft team space is private to the idea team.")
        _ = actor  # any authenticated actor may view live idea spaces

    def _mcp_auth_value(self, row: IdeaMcpConnection) -> str:
        if not row.credentials_encrypted:
            return ""
        try:
            creds = decrypt_credentials(row.credentials_encrypted)
        except Exception:  # noqa: BLE001
            return ""
        return str(creds.get("auth_header_value") or "")

    def _mcp_out(self, row: IdeaMcpConnection) -> IdeaMcpConnectionOut:
        return IdeaMcpConnectionOut(
            id=row.id,
            space_id=row.space_id,
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
