"""Seed collaboration groups, channels, and sample chat messages.

Idempotent by stable group names. Safe to re-run after spine demo seed::

    cd backend && uv run python -m app.seed.groups
    # or via full demo: uv run python -m app.seed.demo
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.groups import (
    GroupChannel,
    GroupInvite,
    GroupMember,
    GroupMessage,
    HubGroup,
)
from app.models.idea import Idea
from app.models.user import User
from app.services.groups_service import DEFAULT_CHANNELS, dm_pair_key

logger = logging.getLogger("idea_hub.seed.groups")

# Stable names used for idempotency (do not rename lightly).
PARKING_NAME = "Parking lot — pre-build chat"
RUNBOOK_GROUP_NAME = "Runbook draft team"

DEFAULT_CHANNEL_SPECS = DEFAULT_CHANNELS


async def _users_by_slug(session: AsyncSession) -> dict[str, User]:
    users: dict[str, User] = {}
    for u in (await session.execute(select(User))).scalars().all():
        if getattr(u, "slug", None):
            users[u.slug] = u
        else:
            key = (u.email or "").split("@")[0]
            users[key] = u
    return users


async def _get_group_by_name(
    session: AsyncSession, name: str
) -> Optional[HubGroup]:
    return (
        await session.execute(select(HubGroup).where(HubGroup.name == name))
    ).scalar_one_or_none()


async def _ensure_channels(
    session: AsyncSession, group: HubGroup, created_by: uuid.UUID
) -> dict[str, GroupChannel]:
    by_slug: dict[str, GroupChannel] = {}
    existing = (
        await session.execute(
            select(GroupChannel).where(GroupChannel.group_id == group.id)
        )
    ).scalars().all()
    for ch in existing:
        by_slug[ch.slug] = ch

    for slug, name, desc, order in DEFAULT_CHANNEL_SPECS:
        if slug in by_slug:
            continue
        row = GroupChannel(
            group_id=group.id,
            slug=slug,
            name=name,
            description=desc,
            kind="text",
            sort_order=order,
            created_by=created_by,
        )
        session.add(row)
        await session.flush()
        by_slug[slug] = row
    return by_slug


async def _ensure_member(
    session: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> None:
    existing = (
        await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return
    session.add(
        GroupMember(group_id=group_id, user_id=user_id, role=role)
    )


async def _is_member(
    session: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    row = (
        await session.execute(
            select(GroupMember.id).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def _channel_has_user_messages(
    session: AsyncSession, channel_id: uuid.UUID
) -> bool:
    row = (
        await session.execute(
            select(GroupMessage.id)
            .where(
                GroupMessage.channel_id == channel_id,
                GroupMessage.message_type == "user",
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


async def _add_messages(
    session: AsyncSession,
    channel: GroupChannel,
    messages: list[tuple[uuid.UUID, str, str, int]],
) -> None:
    """messages: (author_id, body, message_type, minutes_ago)."""
    if await _channel_has_user_messages(session, channel.id):
        return
    now = datetime.now(timezone.utc)
    for author_id, body, mtype, mins in messages:
        session.add(
            GroupMessage(
                channel_id=channel.id,
                author_id=author_id,
                body=body,
                message_type=mtype,
                meta={"seed": True},
                created_at=now - timedelta(minutes=mins),
            )
        )


async def seed_groups(session: AsyncSession) -> dict[str, str]:
    """Create sample groups + chat. Returns map of seed key → group id."""
    users = await _users_by_slug(session)
    priya = users.get("priya")
    marcus = users.get("marcus")
    elena = users.get("elena")
    tomas = users.get("tomas")
    sam = users.get("sam")
    if not priya or not marcus:
        logger.warning("Groups seed skipped — demo users missing")
        return {}

    created: dict[str, str] = {}

    # ----- 1) Group without an idea (pre-build discussion) -----
    parking = await _get_group_by_name(session, PARKING_NAME)
    if not parking:
        parking = HubGroup(
            name=PARKING_NAME,
            description=(
                "Catch ideas and half-formed thoughts before they become "
                "formal submissions. No idea linked yet."
            ),
            idea_id=None,
            created_by=priya.id,
        )
        session.add(parking)
        await session.flush()
        logger.info("Created group: %s", PARKING_NAME)
    else:
        logger.info("Group already present: %s", PARKING_NAME)

    await _ensure_member(session, parking.id, priya.id, "owner")
    member_specs: list[tuple[User, str]] = [(marcus, "member")]
    if elena:
        member_specs.append((elena, "member"))
    if tomas:
        member_specs.append((tomas, "admin"))
    if sam:
        member_specs.append((sam, "member"))
    for u, role in member_specs:
        await _ensure_member(session, parking.id, u.id, role)

    channels = await _ensure_channels(session, parking, priya.id)
    general = channels["general"]
    await _add_messages(
        session,
        general,
        [
            (
                priya.id,
                "Opened this space so we can talk through ideas before filing "
                "them. Drop anything half-baked here.",
                "user",
                180,
            ),
            (
                marcus.id,
                "Nice. I've been chewing on something about incident runbooks — "
                "not ready for Explore yet.",
                "user",
                165,
            ),
            (
                elena.id if elena else priya.id,
                "Park it in #blockers if something is stopping a write-up, "
                "otherwise keep bouncing in #general.",
                "user",
                150,
            ),
            (
                tomas.id if tomas else marcus.id,
                "I'll lurk and nudge when something looks ready to submit.",
                "user",
                140,
            ),
        ],
    )
    if "blockers" in channels:
        await _add_messages(
            session,
            channels["blockers"],
            [
                (
                    marcus.id,
                    "Need a clearer owner for who reviews auto-drafted "
                    "runbooks before we pitch it.",
                    "user",
                    90,
                ),
                (
                    priya.id,
                    "Elena volunteered for first review on similar ideas — "
                    "ping her when the draft is ready.",
                    "user",
                    75,
                ),
            ],
        )
    created["parking"] = str(parking.id)

    # ----- 2) Optional group linked to a seeded accepted idea -----
    runbook_idea = (
        await session.execute(
            select(Idea).where(
                Idea.title.ilike("%runbook%"),
                Idea.status.in_(("accepted", "prototype", "implemented")),
            ).limit(1)
        )
    ).scalar_one_or_none()

    if runbook_idea:
        linked = await _get_group_by_name(session, RUNBOOK_GROUP_NAME)
        if not linked:
            # Prefer unique idea link — skip create if idea already linked
            existing_link = (
                await session.execute(
                    select(HubGroup).where(HubGroup.idea_id == runbook_idea.id)
                )
            ).scalar_one_or_none()
            if existing_link:
                linked = existing_link
                logger.info(
                    "Idea already linked to group %s", existing_link.name
                )
            else:
                linked = HubGroup(
                    name=RUNBOOK_GROUP_NAME,
                    description=(
                        "Delivery chat for the auto-draft runbooks idea. "
                        "Linked from KonnektIdea."
                    ),
                    idea_id=runbook_idea.id,
                    created_by=marcus.id,
                )
                session.add(linked)
                await session.flush()
                logger.info("Created linked group: %s", RUNBOOK_GROUP_NAME)
        else:
            if not linked.idea_id:
                linked.idea_id = runbook_idea.id
            logger.info("Group already present: %s", RUNBOOK_GROUP_NAME)

        await _ensure_member(session, linked.id, marcus.id, "owner")
        linked_members: list[tuple[User, str]] = [(priya, "member")]
        if elena:
            linked_members.append((elena, "admin"))
        if tomas:
            linked_members.append((tomas, "member"))
        for u, role in linked_members:
            await _ensure_member(session, linked.id, u.id, role)

        ch = await _ensure_channels(session, linked, marcus.id)
        await _add_messages(
            session,
            ch["general"],
            [
                (
                    marcus.id,
                    "Idea is accepted — using this group for day-to-day "
                    "build chat instead of long comment threads.",
                    "user",
                    240,
                ),
                (
                    elena.id if elena else marcus.id,
                    "Keep decisions in #decisions so review history stays "
                    "easy to find.",
                    "user",
                    220,
                ),
                (
                    tomas.id if tomas else priya.id,
                    "I'll check in twice a week. Ping #blockers if scope "
                    "creeps past a draft generator.",
                    "user",
                    200,
                ),
                (
                    marcus.id,
                    "First spike: parse incident timeline → markdown outline. "
                    "PR coming later today.",
                    "user",
                    90,
                ),
            ],
        )
        if "decisions" in ch:
            await _add_messages(
                session,
                ch["decisions"],
                [
                    (
                        elena.id if elena else marcus.id,
                        "**Decision:** Human approval is mandatory before any "
                        "runbook is published. Auto-draft only.",
                        "user",
                        210,
                    ),
                    (
                        marcus.id,
                        "Agreed — UI will show Approve / Request edits, never "
                        "auto-publish.",
                        "user",
                        200,
                    ),
                ],
            )
        created["runbook"] = str(linked.id)
    else:
        logger.info("No runbook idea found — skipped linked group")

    # ----- 3) Pending invite (Dana must Accept/Decline) -----
    dana = users.get("dana")
    if dana and not await _is_member(session, parking.id, dana.id):
        pending = (
            await session.execute(
                select(GroupInvite).where(
                    GroupInvite.group_id == parking.id,
                    GroupInvite.invitee_id == dana.id,
                    GroupInvite.status == "pending",
                )
            )
        ).scalar_one_or_none()
        if not pending:
            session.add(
                GroupInvite(
                    group_id=parking.id,
                    invitee_id=dana.id,
                    invited_by=priya.id,
                    role="member",
                    status="pending",
                )
            )
            logger.info("Seeded pending invite: dana → %s", PARKING_NAME)
        created["invite_dana"] = str(parking.id)

    # ----- 4) 1:1 DM (priya ↔ marcus) -----
    key = dm_pair_key(priya.id, marcus.id)
    dm = (
        await session.execute(
            select(HubGroup).where(
                HubGroup.kind == "dm", HubGroup.dm_pair_key == key
            )
        )
    ).scalar_one_or_none()
    if not dm:
        dm = HubGroup(
            name=marcus.name or "Direct message",
            kind="dm",
            dm_pair_key=key,
            created_by=priya.id,
        )
        session.add(dm)
        await session.flush()
        session.add(GroupMember(group_id=dm.id, user_id=priya.id, role="member"))
        session.add(GroupMember(group_id=dm.id, user_id=marcus.id, role="member"))
        chat = GroupChannel(
            group_id=dm.id,
            slug="dm",
            name="Chat",
            description="Direct message",
            kind="text",
            sort_order=0,
            created_by=priya.id,
        )
        session.add(chat)
        await session.flush()
        await _add_messages(
            session,
            chat,
            [
                (priya.id, "Got a minute to sync on the runbook draft?", "user", 30),
                (marcus.id, "Yep — pushing the spike now.", "user", 25),
            ],
        )
        logger.info("Seeded DM: priya ↔ marcus")
    created["dm_priya_marcus"] = str(dm.id)

    await session.flush()
    return created


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    async with AsyncSessionLocal() as session:
        result = await seed_groups(session)
        await session.commit()
        if result:
            print(f"Groups seed ok: {', '.join(result)}")
        else:
            print("Groups seed produced nothing (users missing?)")


if __name__ == "__main__":
    asyncio.run(run())
