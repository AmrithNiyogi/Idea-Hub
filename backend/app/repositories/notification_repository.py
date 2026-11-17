"""Persistence helpers for the notifications inbox.

SQL strategy:
- List by ``user_id`` ordered by ``created_at DESC`` (supports topbar drawer).
- Unread count uses the composite index ``(user_id, read, created_at)``.
- Mark-all-read is a single filtered UPDATE for the recipient.

Idempotency:
- Inserts are append-only; callers own dedupe if needed.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    """Repository for notification inbox rows.

    Responsibilities:
    - Insert notification rows.
    - Query a user's inbox and unread count.
    - Mark one or all as read for a single recipient.

    Thread Safety:
    Bound to one ``AsyncSession``; not shared across requests.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: Notification) -> Notification:
        """Persist a new notification and flush to obtain its id.

        Args:
            row: Unsaved ``Notification`` instance.

        Returns:
            The same instance after flush (id populated).
        """
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_many(self, rows: Sequence[Notification]) -> int:
        """Bulk-insert notification rows.

        Args:
            rows: Unsaved notification instances.

        Returns:
            Number of rows added.
        """
        if not rows:
            return 0
        self.session.add_all(list(rows))
        await self.session.flush()
        return len(rows)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 40,
        unread_only: bool = False,
    ) -> Sequence[Notification]:
        """Return newest notifications for a recipient.

        Args:
            user_id: Recipient user id.
            limit: Max rows (caller-capped).
            unread_only: When True, filter ``read = false``.

        Returns:
            Ordered newest-first sequence.
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def unread_count(self, user_id: uuid.UUID) -> int:
        """Count unread notifications for a recipient."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
        )
        return int(result.scalar_one())

    async def get_for_user(
        self, notif_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        """Load one notification owned by ``user_id``, or None."""
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notif_id,
                Notification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_read(
        self, notif_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Mark a single owned notification as read.

        Returns:
            True when a row was updated.
        """
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.id == notif_id,
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
            .values(read=True)
        )
        return bool(getattr(result, "rowcount", 0))

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Mark every unread notification for the user as read.

        Returns:
            Number of rows updated.
        """
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
            .values(read=True)
        )
        return int(getattr(result, "rowcount", 0) or 0)
