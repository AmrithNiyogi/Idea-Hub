"""Create, list, and mark notifications; fan-out with follow subscription.

Audience rules (idea-scoped events):
1. **Followers** of the idea always receive in-app notifications for subsequent
   important events (subscription model: Follow = subscribe).
2. **Mandatory roles** (author, co-authors, owner, reviewer/assignee, and any
   ``extra`` ids passed by the caller — e.g. panel members, hours requester)
   always receive even if they unfollowed.
3. The acting user is excluded.
4. Unfollowed users who are not mandatory receive nothing.

Email:
- Sent only for kinds in ``EMAIL_KINDS`` when ``NOTIFY_EMAIL_ENABLED``.
- Delivered to ``NOTIFY_EMAIL_OVERRIDE`` (fallback ``OTP_EMAIL_OVERRIDE``);
  intended recipient + idea context appear in the body.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.constants.notification_kinds import EMAIL_KINDS, KIND_LABELS
from app.models.engagement import Follow
from app.models.idea import Idea
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notifications import (
    MarkReadOut,
    NotificationListOut,
    NotificationOut,
    UnreadCountOut,
)
from app.services.email_adapter import send_event_notification_email

logger = logging.getLogger("idea_hub.notifications")


def _as_uuid(raw: Any) -> uuid.UUID | None:
    if raw is None:
        return None
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(str(raw))
    except (TypeError, ValueError):
        return None


def _uniq(ids: Iterable[uuid.UUID | None]) -> list[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    out: list[uuid.UUID] = []
    for i in ids:
        if i is None or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out


class NotificationService:
    """Inbox reads plus domain-event fan-out with follow subscription.

    Responsibilities:
    - Resolve recipients from followers ∪ mandatory roles.
    - Persist inbox rows.
    - Optionally send high-signal email via the shared SMTP stack.

    Collaborators:
    - NotificationRepository
    - Follow / User / Idea models
    - email_adapter.send_event_notification_email

    Side Effects:
    - Writes ``notifications`` rows (caller commits, or this service flushes).
    - May open SMTP when email is enabled for the kind.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    # ---- inbox API ----

    async def list_inbox(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 40,
        unread_only: bool = False,
    ) -> NotificationListOut:
        """Return newest notifications plus total unread count for the badge."""
        rows = await self.repo.list_for_user(
            user_id, limit=limit, unread_only=unread_only
        )
        unread = await self.repo.unread_count(user_id)
        return NotificationListOut(
            items=[NotificationOut.model_validate(r) for r in rows],
            unread_count=unread,
        )

    async def unread(self, user_id: uuid.UUID) -> UnreadCountOut:
        """Lightweight unread count for the bell badge."""
        return UnreadCountOut(unread_count=await self.repo.unread_count(user_id))

    async def mark_read(
        self, user_id: uuid.UUID, notif_id: uuid.UUID
    ) -> MarkReadOut:
        """Mark one owned notification read and commit."""
        updated = 1 if await self.repo.mark_read(notif_id, user_id) else 0
        await self.session.commit()
        return MarkReadOut(ok=True, updated=updated)

    async def mark_all_read(self, user_id: uuid.UUID) -> MarkReadOut:
        """Mark every unread notification for the user and commit."""
        updated = await self.repo.mark_all_read(user_id)
        await self.session.commit()
        return MarkReadOut(ok=True, updated=updated)

    # ---- audience / fan-out ----

    async def follower_ids(self, idea_id: uuid.UUID) -> list[uuid.UUID]:
        """Return user ids currently following the idea (subscription set)."""
        result = await self.session.execute(
            select(Follow.user_id).where(Follow.idea_id == idea_id)
        )
        return list(result.scalars().all())

    def mandatory_ids_for_idea(
        self,
        idea: Idea,
        *,
        extra: Sequence[uuid.UUID] | None = None,
        include_reviewer: bool = True,
    ) -> list[uuid.UUID]:
        """Role-based recipients who always get alerts (even if unfollowed).

        Includes author, co-authors, owner, and optionally the assigned reviewer,
        plus any caller-supplied extras (panel members, hours requester, …).
        """
        co = [_as_uuid(x) for x in (idea.co_author_ids or [])]
        ids = [
            idea.author_id,
            idea.owner_id,
            *co,
            idea.reviewer_id if include_reviewer else None,
            *(extra or ()),
        ]
        return _uniq(ids)

    @staticmethod
    def _exclude_set(
        exclude: uuid.UUID | Sequence[uuid.UUID] | None,
    ) -> set[uuid.UUID]:
        if exclude is None:
            return set()
        if isinstance(exclude, uuid.UUID):
            return {exclude}
        return {u for u in exclude if isinstance(u, uuid.UUID)}

    async def resolve_recipients(
        self,
        idea: Idea,
        *,
        exclude: uuid.UUID | Sequence[uuid.UUID] | None = None,
        extra: Sequence[uuid.UUID] | None = None,
        include_reviewer: bool = True,
        followers_only_extras: bool = False,
    ) -> list[uuid.UUID]:
        """Union of followers and mandatory roles, minus ``exclude``.

        Args:
            idea: Subject idea (follow table keyed by ``idea.id``).
            exclude: Actor(s) who caused the event (never notified of own action).
            extra: Additional mandatory ids (e.g. panel members, requester).
            include_reviewer: Include ``idea.reviewer_id`` in mandatory set.
            followers_only_extras: Unused placeholder kept for call clarity.

        Returns:
            Deduplicated recipient user ids.
        """
        del followers_only_extras  # reserved for future split routing
        skip = self._exclude_set(exclude)
        followers = await self.follower_ids(idea.id)
        mandatory = self.mandatory_ids_for_idea(
            idea, extra=extra, include_reviewer=include_reviewer
        )
        return [
            u
            for u in _uniq([*followers, *mandatory, *(extra or ())])
            if u not in skip
        ]

    async def notify_users(
        self,
        user_ids: Sequence[uuid.UUID],
        *,
        kind: str,
        text: str,
        href: str,
        idea_id: uuid.UUID | None = None,
        idea_title: str | None = None,
        exclude: uuid.UUID | Sequence[uuid.UUID] | None = None,
        meta: dict[str, Any] | None = None,
        send_email: bool | None = None,
        flush_only: bool = True,
    ) -> int:
        """Persist one notification per user and optionally email.

        Does not commit by default (``flush_only=True``) so callers can include
        fan-out in the same transaction as the domain write.

        Args:
            user_ids: Explicit recipient set (already filtered by caller).
            kind: Stable event class.
            text: Inbox / email body summary.
            href: App-relative path.
            idea_id: Optional idea foreign key.
            idea_title: Used in email subject/body when present.
            exclude: Drop these ids if still present.
            meta: Optional JSON extras stored on the row.
            send_email: Override; default uses ``EMAIL_KINDS``.
            flush_only: When True, flush without commit.

        Returns:
            Number of inbox rows created.
        """
        skip = self._exclude_set(exclude)
        recipients = [u for u in _uniq(user_ids) if u not in skip]
        if not recipients:
            return 0

        rows = [
            Notification(
                user_id=uid,
                kind=kind,
                idea_id=idea_id,
                text=text,
                href=href or "/",
                read=False,
                meta=meta or {},
            )
            for uid in recipients
        ]
        await self.repo.add_many(rows)

        should_email = (
            bool(send_email)
            if send_email is not None
            else kind in EMAIL_KINDS
        )
        if should_email and settings.NOTIFY_EMAIL_ENABLED:
            await self._email_batch(
                recipients,
                kind=kind,
                text=text,
                href=href,
                idea_id=idea_id,
                idea_title=idea_title,
                meta=meta or {},
            )

        if not flush_only:
            await self.session.commit()
        return len(rows)

    async def notify_idea(
        self,
        idea: Idea,
        *,
        kind: str,
        text: str,
        href: str | None = None,
        exclude: uuid.UUID | Sequence[uuid.UUID] | None = None,
        extra: Sequence[uuid.UUID] | None = None,
        include_reviewer: bool = True,
        meta: dict[str, Any] | None = None,
        send_email: bool | None = None,
        flush_only: bool = True,
    ) -> int:
        """Fan-out to followers ∪ mandatory roles for an idea event.

        This is the primary entry point for domain hooks. Followers receive
        because they subscribed; mandatory roles always receive.
        """
        recipients = await self.resolve_recipients(
            idea,
            exclude=exclude,
            extra=extra,
            include_reviewer=include_reviewer,
        )
        link = href or f"/ideas/{idea.id}"
        return await self.notify_users(
            recipients,
            kind=kind,
            text=text,
            href=link,
            idea_id=idea.id,
            idea_title=idea.title,
            exclude=None,  # already excluded
            meta=meta,
            send_email=send_email,
            flush_only=flush_only,
        )

    async def _email_batch(
        self,
        user_ids: Sequence[uuid.UUID],
        *,
        kind: str,
        text: str,
        href: str,
        idea_id: uuid.UUID | None,
        idea_title: str | None,
        meta: dict[str, Any],
    ) -> None:
        """Load users and send one SMTP message per recipient (override To)."""
        if not user_ids:
            return
        result = await self.session.execute(
            select(User).where(User.id.in_(list(user_ids)))
        )
        users = {u.id: u for u in result.scalars().all()}
        follower_set: set[uuid.UUID] = set()
        if idea_id is not None:
            follower_set = set(await self.follower_ids(idea_id))

        label = KIND_LABELS.get(kind, kind.replace("_", " ").title())
        for uid in user_ids:
            user = users.get(uid)
            if not user:
                continue
            is_follower = uid in follower_set
            try:
                send_event_notification_email(
                    intended_email=user.email,
                    user_name=user.name,
                    kind=kind,
                    kind_label=label,
                    summary=text,
                    href=href,
                    idea_title=idea_title,
                    is_follower=is_follower,
                    meta=meta,
                )
            except Exception:  # noqa: BLE001 — never fail the domain txn on SMTP
                logger.exception(
                    "Notification email failed kind=%s user=%s", kind, uid
                )


async def notify_idea(
    session: AsyncSession,
    idea: Idea,
    *,
    kind: str,
    text: str,
    href: str | None = None,
    exclude: uuid.UUID | Sequence[uuid.UUID] | None = None,
    extra: Sequence[uuid.UUID] | None = None,
    include_reviewer: bool = True,
    meta: dict[str, Any] | None = None,
    send_email: bool | None = None,
) -> int:
    """Module-level helper so services can call without constructing a class."""
    return await NotificationService(session).notify_idea(
        idea,
        kind=kind,
        text=text,
        href=href,
        exclude=exclude,
        extra=extra,
        include_reviewer=include_reviewer,
        meta=meta,
        send_email=send_email,
        flush_only=True,
    )


async def notify_users(
    session: AsyncSession,
    user_ids: Sequence[uuid.UUID],
    *,
    kind: str,
    text: str,
    href: str,
    idea_id: uuid.UUID | None = None,
    idea_title: str | None = None,
    exclude: uuid.UUID | Sequence[uuid.UUID] | None = None,
    meta: dict[str, Any] | None = None,
    send_email: bool | None = None,
) -> int:
    """Module-level helper for non-idea or precomputed recipient sets."""
    return await NotificationService(session).notify_users(
        user_ids,
        kind=kind,
        text=text,
        href=href,
        idea_id=idea_id,
        idea_title=idea_title,
        exclude=exclude,
        meta=meta,
        send_email=send_email,
        flush_only=True,
    )
