"""Orchestrate tracker / integration connections and idea links.

Resolution order when creating/linking from an idea:
  1. Explicit ``connection_id`` (must be actor's personal or an org default)
  2. Else ``provider_id`` → user connection → org default → 400 prompt to connect
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.constants.tracker_constants import (
    TRACKER_CREATABLE_STATUSES,
    TRACKER_LINKABLE_STATUSES,
)
from app.dependencies.phase23_auth import Actor
from app.integrations.registry import list_integrations
from app.models.tracker import IdeaTrackerLink, TrackerConnection
from app.repositories.tracker_repository import (
    SCOPE_ORG,
    SCOPE_USER,
    TrackerRepository,
)
from app.schemas.trackers import (
    EffectiveConnectionOut,
    IdeaTrackerLinkCreate,
    IdeaTrackerLinkOut,
    IdeaTrackerRemoteUpdate,
    IntegrationProviderOut,
    LiveTrackerTaskOut,
    RemoteAssigneeOut,
    RemotePriorityOptionOut,
    RemoteStatusOptionOut,
    TrackerConnectionCreate,
    TrackerConnectionOut,
    TrackerProviderOut,
)
from app.services.spine_bridge import SpineBridge
from app.integrations.adapters import resolve_provider
from app.trackers.base import CreateIssuePayload, RemoteTask, UpdateTaskPayload
from app.trackers.crypto import decrypt_credentials, encrypt_credentials
from app.trackers.registry import list_providers, provider_public_dict


class TrackerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TrackerRepository(session)
        self.spine = SpineBridge(session)

    # ----- catalogs -----

    def list_providers(self) -> list[TrackerProviderOut]:
        return [
            TrackerProviderOut.model_validate(provider_public_dict(p))
            for p in list_providers()
        ]

    def list_integrations(
        self, *, category: Optional[str] = None
    ) -> list[IntegrationProviderOut]:
        return [
            IntegrationProviderOut.model_validate(d.public_dict())
            for d in list_integrations(category=category)
        ]

    # ----- connections -----

    async def list_connections(self, actor: Actor) -> list[TrackerConnectionOut]:
        rows = await self.repo.list_connections_for_user(actor.id)
        return [TrackerConnectionOut.model_validate(r) for r in rows]

    async def list_org_connections(
        self, actor: Actor
    ) -> list[TrackerConnectionOut]:
        self._require_admin(actor)
        rows = await self.repo.list_org_connections()
        return [TrackerConnectionOut.model_validate(r) for r in rows]

    async def list_effective(
        self, actor: Actor, *, category: Optional[str] = None
    ) -> list[EffectiveConnectionOut]:
        """One row per connectable/available (or stub) provider with source."""
        integrations = list_integrations(category=category)
        out: list[EffectiveConnectionOut] = []
        for integ in integrations:
            if integ.status != "available":
                out.append(
                    EffectiveConnectionOut(
                        provider_id=integ.id, source="none", connection=None
                    )
                )
                continue
            conn, source = await self.repo.resolve_effective(actor.id, integ.id)
            out.append(
                EffectiveConnectionOut(
                    provider_id=integ.id,
                    source=source,  # type: ignore[arg-type]
                    connection=(
                        TrackerConnectionOut.model_validate(conn) if conn else None
                    ),
                )
            )
        return out

    async def connect(
        self,
        body: TrackerConnectionCreate,
        actor: Actor,
        *,
        scope: Literal["user", "organization"] = "user",
    ) -> TrackerConnectionOut:
        if scope == SCOPE_ORG:
            self._require_admin(actor)

        try:
            provider = resolve_provider(body.provider_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

        credentials = dict(body.credentials or {})
        self._assert_required_fields(provider, credentials)
        try:
            probe = await provider.validate_connection(credentials)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — remote/network
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Could not reach {provider.display_name}: {exc}",
            ) from exc

        label = (body.label or "default").strip() or "default"
        encrypted = encrypt_credentials(credentials)

        if scope == SCOPE_ORG:
            existing = await self.repo.find_org_connection(provider.id, label)
        else:
            existing = await self.repo.find_user_connection(
                actor.id, provider.id, label
            )

        if existing:
            existing.credentials_encrypted = encrypted
            existing.display_label = probe.display_label
            existing.external_account_id = probe.external_account_id or ""
            existing.meta = dict(probe.meta or {})
            await self.session.flush()
            await self.session.commit()
            return TrackerConnectionOut.model_validate(existing)

        row = TrackerConnection(
            scope=scope,
            user_id=actor.id if scope == SCOPE_USER else None,
            created_by=actor.id,
            provider_id=provider.id,
            label=label,
            display_label=probe.display_label,
            credentials_encrypted=encrypted,
            meta=dict(probe.meta or {}),
            external_account_id=probe.external_account_id or "",
        )
        await self.repo.add_connection(row)
        await self.session.commit()
        return TrackerConnectionOut.model_validate(row)

    async def disconnect(
        self,
        connection_id: uuid.UUID,
        actor: Actor,
        *,
        expect_scope: Optional[Literal["user", "organization"]] = None,
    ) -> None:
        row = await self.repo.get_connection(connection_id)
        if not row:
            raise HTTPException(404, "Connection not found.")

        if row.scope == SCOPE_ORG:
            self._require_admin(actor)
            if expect_scope and expect_scope != SCOPE_ORG:
                raise HTTPException(404, "Connection not found.")
        elif row.scope == SCOPE_USER:
            if row.user_id != actor.id:
                raise HTTPException(404, "Connection not found.")
            if expect_scope and expect_scope != SCOPE_USER:
                raise HTTPException(404, "Connection not found.")
        else:
            raise HTTPException(400, f"Unknown connection scope: {row.scope}")

        await self.repo.delete_connection(row)
        await self.session.commit()

    # ----- idea links -----

    async def list_idea_links(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> list[IdeaTrackerLinkOut]:
        await self._require_idea(idea_id)
        _ = actor
        rows = await self.repo.list_links_for_idea(idea_id)
        return [IdeaTrackerLinkOut.model_validate(r) for r in rows]

    async def create_or_link(
        self,
        idea_id: uuid.UUID,
        body: IdeaTrackerLinkCreate,
        actor: Actor,
    ) -> IdeaTrackerLinkOut:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)

        if idea.status not in TRACKER_LINKABLE_STATUSES:
            raise HTTPException(
                400,
                "External integrations are available after an idea is accepted.",
            )

        conn = await self._resolve_connection_for_link(body, actor)
        try:
            provider = resolve_provider(conn.provider_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

        credentials = decrypt_credentials(conn.credentials_encrypted)
        title = (body.title or getattr(idea, "title", None) or "Idea").strip()
        description = (
            body.description
            if body.description is not None
            else self._default_description(idea)
        )
        idea_url = self._idea_url(idea_id)
        is_docs = getattr(provider, "integration_category", None) == "docs"
        remote_noun = "pages" if is_docs else "tasks"
        extra = dict(body.extra or {})
        # Docs adapters (Notion) get structured idea body for page blocks.
        if is_docs:
            if "problem" not in extra:
                extra["problem"] = str(getattr(idea, "problem", "") or "")
            if "solution" not in extra:
                extra["solution"] = str(getattr(idea, "solution", "") or "")

        try:
            if body.mode == "link":
                external_ref = (body.external_id_or_url or "").strip()
                if not external_ref:
                    raise HTTPException(
                        400, "external_id_or_url is required when mode=link."
                    )
                remote = await provider.resolve_existing(credentials, external_ref)
            else:
                if idea.status not in TRACKER_CREATABLE_STATUSES:
                    raise HTTPException(
                        400,
                        f"New remote {remote_noun} can be created while the "
                        "idea is accepted or in prototype.",
                    )
                remote = await provider.create_issue(
                    credentials,
                    CreateIssuePayload(
                        title=title,
                        description=description,
                        idea_id=str(idea_id),
                        idea_url=idea_url,
                        status_hint=str(getattr(idea, "status", "") or ""),
                        tags=[],
                        extra=extra,
                    ),
                )
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"{provider.display_name} request failed: {exc}",
            ) from exc

        link = IdeaTrackerLink(
            idea_id=idea_id,
            connection_id=conn.id,
            provider_id=conn.provider_id,
            external_id=remote.external_id,
            external_key=remote.key or "",
            external_url=remote.url or "",
            title=title,
            created_by=actor.id,
            meta={
                "raw_keys": list((remote.raw or {}).keys())[:40],
                "connection_scope": conn.scope,
            },
        )
        try:
            await self.repo.add_link(link)
            await self.session.commit()
        except Exception as exc:  # noqa: BLE001 — unique / DB errors
            await self.session.rollback()
            msg = str(exc).lower()
            if "unique" in msg or "duplicate" in msg:
                raise HTTPException(
                    409,
                    "This idea is already linked to that remote item.",
                ) from exc
            raise HTTPException(400, f"Could not save tracker link: {exc}") from exc
        return IdeaTrackerLinkOut.model_validate(link)

    async def unlink(
        self,
        idea_id: uuid.UUID,
        link_id: uuid.UUID,
        actor: Actor,
    ) -> None:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)
        link = await self.repo.get_link(link_id)
        if not link or link.idea_id != idea_id:
            raise HTTPException(404, "Tracker link not found.")
        await self.repo.delete_link(link)
        await self.session.commit()

    # ----- live remote tasks -----

    async def list_live_tasks(
        self, idea_id: uuid.UUID, actor: Actor
    ) -> list[LiveTrackerTaskOut]:
        idea = await self._require_idea(idea_id)
        _ = actor
        can_update = self._can_manage(idea, actor)
        rows = await self.repo.list_links_for_idea(idea_id)
        out: list[LiveTrackerTaskOut] = []
        for link in rows:
            out.append(
                await self._live_for_link(link, actor, can_update=can_update)
            )
        return out

    async def get_live_task(
        self,
        idea_id: uuid.UUID,
        link_id: uuid.UUID,
        actor: Actor,
    ) -> LiveTrackerTaskOut:
        idea = await self._require_idea(idea_id)
        link = await self.repo.get_link(link_id)
        if not link or link.idea_id != idea_id:
            raise HTTPException(404, "Tracker link not found.")
        return await self._live_for_link(
            link, actor, can_update=self._can_manage(idea, actor)
        )

    async def update_remote_task(
        self,
        idea_id: uuid.UUID,
        link_id: uuid.UUID,
        body: IdeaTrackerRemoteUpdate,
        actor: Actor,
    ) -> LiveTrackerTaskOut:
        idea = await self._require_idea(idea_id)
        self._assert_can_manage(idea, actor)
        link = await self.repo.get_link(link_id)
        if not link or link.idea_id != idea_id:
            raise HTTPException(404, "Tracker link not found.")

        conn, provider = await self._connection_and_provider_for_link(
            link, actor
        )
        credentials = decrypt_credentials(conn.credentials_encrypted)
        try:
            update_extra: dict[str, Any] = {}
            if body.append_content is not None:
                update_extra["append_content"] = body.append_content
            remote = await provider.update_task(
                credentials,
                link.external_id,
                UpdateTaskPayload(
                    status=body.status,
                    title=body.title,
                    priority=body.priority,
                    due_date=body.due_date,
                    assignee_ids=body.assignee_ids,
                    extra=update_extra,
                ),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"{provider.display_name} update failed: {exc}",
            ) from exc

        # Keep stored title/url in sync when the remote returns fresher data.
        changed = False
        if remote.title and remote.title != (link.title or ""):
            link.title = remote.title[:500]
            changed = True
        if remote.url and remote.url != (link.external_url or ""):
            link.external_url = remote.url[:1024]
            changed = True
        if remote.key and remote.key != (link.external_key or ""):
            link.external_key = remote.key[:255]
            changed = True
        if changed:
            await self.session.commit()

        return await self._live_out(
            link,
            remote,
            live=True,
            error=None,
            can_update=True,
        )

    async def _live_for_link(
        self,
        link: IdeaTrackerLink,
        actor: Actor,
        *,
        can_update: bool,
    ) -> LiveTrackerTaskOut:
        try:
            conn, provider = await self._connection_and_provider_for_link(
                link, actor
            )
            credentials = decrypt_credentials(conn.credentials_encrypted)
            remote = await provider.get_task(credentials, link.external_id)
            return await self._live_out(
                link,
                remote,
                live=True,
                error=None,
                can_update=can_update,
            )
        except HTTPException as exc:
            return await self._live_out(
                link,
                None,
                live=False,
                error=str(exc.detail),
                can_update=can_update,
            )
        except ValueError as exc:
            return await self._live_out(
                link,
                None,
                live=False,
                error=str(exc),
                can_update=can_update,
            )
        except Exception as exc:  # noqa: BLE001
            return await self._live_out(
                link,
                None,
                live=False,
                error=f"Live refresh failed: {exc}",
                can_update=can_update,
            )

    async def _connection_and_provider_for_link(
        self, link: IdeaTrackerLink, actor: Actor
    ) -> tuple[TrackerConnection, Any]:
        conn: Optional[TrackerConnection] = None
        if link.connection_id:
            # Prefer the connection used at link time (may be org default).
            conn = await self.repo.get_connection(link.connection_id)
        if not conn:
            conn, source = await self.repo.resolve_effective(
                actor.id, link.provider_id
            )
            if not conn or source == "none":
                raise HTTPException(
                    400,
                    f"No connection for '{link.provider_id}'. Connect it "
                    "under Integrations or ask an admin for an org default.",
                )
        try:
            provider = resolve_provider(conn.provider_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return conn, provider

    async def _email_user_map(
        self, emails: list[str]
    ) -> dict[str, uuid.UUID]:
        """Map lowercased emails → KonnektIdea user ids (best-effort)."""
        clean = sorted(
            {e.strip().lower() for e in emails if (e or "").strip()}
        )
        if not clean:
            return {}
        from sqlalchemy import func, select

        from app.models.user import User

        result = await self.session.execute(
            select(User.id, User.email).where(
                func.lower(User.email).in_(clean)
            )
        )
        return {
            str(email).strip().lower(): uid
            for uid, email in result.all()
            if email
        }

    def _assignee_out(
        self,
        a: Any,
        email_map: dict[str, uuid.UUID],
    ) -> RemoteAssigneeOut:
        email = getattr(a, "email", "") or ""
        hub_id = email_map.get(email.strip().lower()) if email else None
        return RemoteAssigneeOut(
            id=getattr(a, "id", "") or "",
            name=getattr(a, "name", "") or "",
            email=email,
            avatar_url=getattr(a, "avatar_url", "") or "",
            idea_hub_user_id=hub_id,
        )

    async def _live_out(
        self,
        link: IdeaTrackerLink,
        remote: Optional[RemoteTask],
        *,
        live: bool,
        error: Optional[str],
        can_update: bool,
    ) -> LiveTrackerTaskOut:
        if remote:
            emails = [
                a.email
                for a in [*remote.assignees, *remote.assignable]
                if a.email
            ]
            email_map = await self._email_user_map(emails)
            writable = can_update and live
            return LiveTrackerTaskOut(
                link_id=link.id,
                provider_id=link.provider_id,
                external_id=remote.external_id or link.external_id,
                external_key=remote.key or link.external_key or "",
                external_url=remote.url or link.external_url or "",
                stored_title=link.title or "",
                title=remote.title or link.title or "",
                status=remote.status or "",
                status_id=remote.status_id or "",
                status_color=remote.status_color or "",
                status_type=remote.status_type or "",
                priority=remote.priority or "",
                priority_id=remote.priority_id or "",
                priority_color=remote.priority_color or "",
                due_date=remote.due_date or "",
                url=remote.url or link.external_url or "",
                assignees=[
                    self._assignee_out(a, email_map) for a in remote.assignees
                ],
                assignable=[
                    self._assignee_out(a, email_map) for a in remote.assignable
                ],
                status_options=[
                    RemoteStatusOptionOut(
                        id=o.id, name=o.name, color=o.color, type=o.type
                    )
                    for o in remote.status_options
                ],
                priority_options=[
                    RemotePriorityOptionOut(
                        id=o.id, name=o.name, color=o.color
                    )
                    for o in remote.priority_options
                ],
                editable_fields=list(remote.editable_fields or []),
                live=live,
                error=error,
                can_update_status=writable,
                can_update=writable,
            )
        return LiveTrackerTaskOut(
            link_id=link.id,
            provider_id=link.provider_id,
            external_id=link.external_id,
            external_key=link.external_key or "",
            external_url=link.external_url or "",
            stored_title=link.title or "",
            title=link.title or "",
            status="",
            url=link.external_url or "",
            live=False,
            error=error,
            can_update_status=False,
            can_update=False,
        )

    # ----- helpers -----

    def _can_manage(self, idea: Any, actor: Actor) -> bool:
        is_owner = getattr(idea, "owner_id", None) == actor.id
        is_author = getattr(idea, "author_id", None) == actor.id
        co = set(getattr(idea, "co_author_ids", None) or [])
        return bool(
            is_owner
            or is_author
            or actor.id in co
            or actor.has_role("lead", "admin", "leadership")
        )

    async def _resolve_connection_for_link(
        self, body: IdeaTrackerLinkCreate, actor: Actor
    ) -> TrackerConnection:
        if body.connection_id:
            conn = await self.repo.get_usable_connection(
                body.connection_id, actor.id
            )
            if not conn:
                raise HTTPException(
                    404,
                    "Connection not found. Connect the provider under "
                    "Integrations, or use the organization default.",
                )
            return conn

        provider_id = (body.provider_id or "").strip()
        conn, source = await self.repo.resolve_effective(actor.id, provider_id)
        if not conn or source == "none":
            raise HTTPException(
                400,
                f"No connection for '{provider_id}'. Connect it under "
                "Integrations (personal) or ask an admin to set an "
                "organization default.",
            )
        return conn

    def _assert_required_fields(self, provider: Any, credentials: dict) -> None:
        for field in getattr(provider, "connect_fields", []) or []:
            if not getattr(field, "required", True):
                continue
            key = field.key
            val = credentials.get(key)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise HTTPException(
                    400, f"Missing required field: {field.label or key}"
                )

    def _assert_can_manage(self, idea: Any, actor: Actor) -> None:
        if self._can_manage(idea, actor):
            return
        raise HTTPException(
            403,
            "Only the owner, authors, a team lead or an administrator "
            "can manage external integration links.",
        )

    def _require_admin(self, actor: Actor) -> None:
        if not actor.has_role("admin"):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Administrator role required to manage organization "
                "integration defaults.",
            )

    async def _require_idea(self, idea_id: uuid.UUID) -> Any:
        idea = await self.spine.get_idea(idea_id)
        if not idea:
            raise HTTPException(404, "Idea not found.")
        return idea

    def _idea_url(self, idea_id: uuid.UUID) -> str:
        origin = (settings.FRONTEND_ORIGIN or "http://localhost:5173").rstrip("/")
        return f"{origin}/ideas/{idea_id}"

    def _default_description(self, idea: Any) -> str:
        parts = [
            "Created from KonnektIdea.",
            f"Title: {getattr(idea, 'title', '')}",
            f"Status: {getattr(idea, 'status', '')}",
        ]
        problem = str(getattr(idea, "problem", "") or "").strip()
        solution = str(getattr(idea, "solution", "") or "").strip()
        if problem:
            parts.extend(["", "## Problem", problem])
        if solution:
            parts.extend(["", "## Solution", solution])
        parts.append(self._idea_url(idea.id))
        return "\n".join(parts)
