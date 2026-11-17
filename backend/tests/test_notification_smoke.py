"""Notification service smoke — helpers, inbox, fan-out with mocks."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config.settings import settings
from app.services import notification_service as ns


def test_as_uuid_and_uniq() -> None:
    uid = uuid.uuid4()
    assert ns._as_uuid(uid) == uid
    assert ns._as_uuid(str(uid)) == uid
    assert ns._as_uuid("not-a-uuid") is None
    assert ns._as_uuid(None) is None
    assert ns._uniq([uid, None, uid, uuid.uuid4()])[0] == uid
    assert len(ns._uniq([uid, uid])) == 1


def test_mandatory_ids_for_idea() -> None:
    author = uuid.uuid4()
    owner = uuid.uuid4()
    co = uuid.uuid4()
    reviewer = uuid.uuid4()
    idea = SimpleNamespace(
        author_id=author,
        owner_id=owner,
        co_author_ids=[str(co)],
        reviewer_id=reviewer,
    )
    svc = ns.NotificationService(AsyncMock())
    ids = svc.mandatory_ids_for_idea(idea, extra=[owner])
    assert author in ids and owner in ids and co in ids and reviewer in ids
    ids2 = svc.mandatory_ids_for_idea(idea, include_reviewer=False)
    assert reviewer not in ids2


def test_exclude_set() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    assert ns.NotificationService._exclude_set(None) == set()
    assert ns.NotificationService._exclude_set(a) == {a}
    assert ns.NotificationService._exclude_set([a, b]) == {a, b}


@pytest.mark.asyncio
async def test_inbox_helpers(async_session: AsyncMock) -> None:
    svc = ns.NotificationService(async_session)
    svc.repo = MagicMock()
    svc.repo.list_for_user = AsyncMock(return_value=[])
    svc.repo.unread_count = AsyncMock(return_value=3)
    svc.repo.mark_read = AsyncMock(return_value=True)
    svc.repo.mark_all_read = AsyncMock(return_value=2)

    inbox = await svc.list_inbox(uuid.uuid4())
    assert inbox.unread_count == 3
    unread = await svc.unread(uuid.uuid4())
    assert unread.unread_count == 3
    marked = await svc.mark_read(uuid.uuid4(), uuid.uuid4())
    assert marked.updated == 1
    all_marked = await svc.mark_all_read(uuid.uuid4())
    assert all_marked.updated == 2


@pytest.mark.asyncio
async def test_resolve_and_notify_idea(async_session: AsyncMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NOTIFY_EMAIL_ENABLED", False)
    author = uuid.uuid4()
    follower = uuid.uuid4()
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        title="Ship it",
        author_id=author,
        owner_id=None,
        co_author_ids=[],
        reviewer_id=None,
    )
    svc = ns.NotificationService(async_session)
    svc.repo = MagicMock()
    svc.repo.add_many = AsyncMock()
    svc.follower_ids = AsyncMock(return_value=[follower, author])

    recipients = await svc.resolve_recipients(idea, exclude=author)
    assert follower in recipients
    assert author not in recipients

    n = await svc.notify_idea(
        idea,
        kind="status",
        text="updated",
        exclude=author,
        send_email=False,
    )
    assert n >= 1
    svc.repo.add_many.assert_awaited()


@pytest.mark.asyncio
async def test_module_helpers_delegate(async_session: AsyncMock) -> None:
    idea = SimpleNamespace(
        id=uuid.uuid4(),
        title="t",
        author_id=uuid.uuid4(),
        owner_id=None,
        co_author_ids=[],
        reviewer_id=None,
    )
    with patch.object(
        ns.NotificationService, "notify_idea", AsyncMock(return_value=2)
    ) as m:
        assert await ns.notify_idea(async_session, idea, kind="x", text="y") == 2
        m.assert_awaited()
    with patch.object(
        ns.NotificationService, "notify_users", AsyncMock(return_value=1)
    ) as m2:
        assert (
            await ns.notify_users(
                async_session, [uuid.uuid4()], kind="x", text="y", href="/"
            )
            == 1
        )
        m2.assert_awaited()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_email_batch_swallows_smtp_errors(
    async_session: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "NOTIFY_EMAIL_ENABLED", True)
    uid = uuid.uuid4()
    user = SimpleNamespace(id=uid, email="a@b.c", name="A")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [user]
    async_session.execute.return_value = result

    svc = ns.NotificationService(async_session)
    svc.follower_ids = AsyncMock(return_value=[])
    with patch(
        "app.services.notification_service.send_event_notification_email",
        side_effect=RuntimeError("smtp"),
    ):
        await svc._email_batch(
            [uid],
            kind="decision",
            text="x",
            href="/",
            idea_id=None,
            idea_title="t",
            meta={},
        )
