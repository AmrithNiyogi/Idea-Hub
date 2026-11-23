# pylint: disable=too-many-lines  # cohesive module; splitting is a separate refactor
"""Admin configuration service (Phase 4).

Thin but real: categories, panels, scoring weights, timelines/SLAs,
point-value overlays, export inventory, reset hook, audit log.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.admin_defaults import (
    DEFAULT_POINT_OVERRIDES,
    DEFAULT_POOL,
    DEFAULT_SCORING,
    DEFAULT_TIMELINES,
)
from app.constants.lifecycle import ROLE_ORDER, VALID_ROLES
from app.dependencies.phase23_auth import Actor
from app.models.admin import AdminAudit, PlatformSetting, ReviewPanel
from app.models.agent import KompassAnswer, ProposalDecision
from app.models.category import Category
from app.models.collab import CollabRequest, TrackerCheckin, TrackerMilestone
from app.models.delivery import (
    DeliveryContributor,
    DeliveryTask,
    DeliveryUpdate,
    ImpactEntry,
    TimeGrantRequest,
    TimeLog,
)
from app.models.engagement import Comment, Follow, Vote
from app.models.idea import Idea, StatusHistory
from app.models.ideathon import Ideathon, IdeathonEntry, IdeathonHandoff
from app.models.problem import ProblemMeta
from app.models.recognition import RecognitionAward
from app.models.reopen import ReopenConditionSet
from app.models.review import Decision, Review
from app.models.user import Team, User
from app.schemas.admin import (
    AdminConfigOut,
    AdminPrimaryRoleIn,
    AdminRoleMutationOut,
    AdminUserDeleteOut,
    AdminUserOut,
    AuditOut,
    CategoryCreateIn,
    CategoryOut,
    CategoryUpdateIn,
    ExportOut,
    PanelCreateIn,
    PanelOut,
    PanelUpdateIn,
    PointOverridesIn,
    ResetOut,
    ScoringIn,
    TimelinesIn,
)

ROLE_LABELS: dict[str, str] = {
    "contributor": "Contributor",
    "reviewer": "Reviewer",
    "lead": "Team lead",
    "leadership": "Leadership",
    "admin": "Administrator",
}

# Colour keys accepted by admin category create/update (CSS tokens in tokens.css).
CATEGORY_COLOR_KEYS = frozenset(
    {
        "tech",
        "business",
        "process",
        "innovation",
        "amber",
        "green",
        "violet",
        "coral",
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(actor: Actor) -> None:
    if not actor.has_role("admin"):
        raise HTTPException(status_code=403, detail="Administrator role required")


def _color_from_key(color_key: str) -> str:
    key = color_key.strip().lower()
    if key not in CATEGORY_COLOR_KEYS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Choose a colour key: "
                + ", ".join(sorted(CATEGORY_COLOR_KEYS))
            ),
        )
    return f"var(--cat-{key})"


def _slugify(label: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "category"
    return base[:64]


def _role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def _sort_roles(roles: list[str]) -> list[str]:
    wanted = {str(r).lower() for r in roles}
    return [r for r in ROLE_ORDER if r in wanted]


def _user_admin_out(user: User) -> AdminUserOut:
    status = str(user.status or "active")
    return AdminUserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        title=user.title or "",
        roles=_sort_roles([str(r) for r in (user.roles or [])]),
        primary_role=str(user.primary_role or "contributor"),
        status=status,
        is_active=status == "active",
    )


def _user_holds_admin(user: User) -> bool:
    return "admin" in [str(r).lower() for r in (user.roles or [])]


def _clear_login_otp_keys(user_id: uuid.UUID) -> None:
    """Drop Redis OTP / cooldown keys so a disabled or deleted user cannot verify."""
    try:
        from app.db.session import get_redis
        from app.services.login_otp_service import _cooldown_key, _otp_key

        uid = str(user_id)
        get_redis().delete(_otp_key(uid), _cooldown_key(uid))
    except Exception:  # noqa: BLE001 — Redis optional in unit tests
        pass


class AdminService:
    # pylint: disable=too-many-public-methods  # one cohesive service/repo surface
    """Mutate platform settings and panels; emit audit rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_setting(self, key: str, default: dict[str, Any]) -> dict[str, Any]:
        row = await self.session.get(PlatformSetting, key)
        if row and isinstance(row.value, dict):
            if key == "scoring":
                # scoring stored as {"criteria": [...]}
                return row.value
            return {**default, **row.value}
        if key == "scoring":
            return {"criteria": list(DEFAULT_SCORING)}
        return dict(default)

    async def _set_setting(
        self,
        key: str,
        value: dict[str, Any],
        actor: Actor,
        section: str,
        summary: str,
        changes: list[dict[str, Any]],
    ) -> None:
        row = await self.session.get(PlatformSetting, key)
        if row is None:
            row = PlatformSetting(key=key, value=value, updated_by=actor.id)
            self.session.add(row)
        else:
            row.value = value
            row.updated_by = actor.id
            row.updated_at = _now()
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section=section,
                summary=summary,
                changes=changes,
            )
        )
        await self.session.commit()

    async def ensure_defaults(self) -> None:
        """Seed settings + one panel per category if missing."""
        for key, default in (
            ("timelines", DEFAULT_TIMELINES),
            ("scoring", {"criteria": DEFAULT_SCORING}),
            ("point_overrides", DEFAULT_POINT_OVERRIDES),
            ("pool", DEFAULT_POOL),
        ):
            existing = await self.session.get(PlatformSetting, key)
            if existing is None:
                self.session.add(PlatformSetting(key=key, value=dict(default)))

        cats = (await self.session.execute(select(Category))).scalars().all()
        for c in cats:
            existing = (
                await self.session.execute(
                    select(ReviewPanel).where(ReviewPanel.category_id == c.id)
                )
            ).scalar_one_or_none()
            if existing:
                continue
            reviewers = (
                await self.session.execute(
                    select(User).where(User.roles.contains(["reviewer"]))
                )
            ).scalars().all()
            # JSONB contains may not work on all dialects — fallback filter
            if not reviewers:
                all_u = (await self.session.execute(select(User))).scalars().all()
                reviewers = [
                    u
                    for u in all_u
                    if "reviewer" in (u.roles or []) or "admin" in (u.roles or [])
                ]
            member_ids = [str(u.id) for u in reviewers[:4]]
            chair = reviewers[0].id if reviewers else None
            self.session.add(
                ReviewPanel(
                    slug=f"panel_{c.slug}",
                    category_id=c.id,
                    name=f"{c.label} review panel",
                    member_ids=member_ids,
                    chair_id=chair,
                )
            )
        await self.session.commit()

    async def config(self) -> AdminConfigOut:
        await self.ensure_defaults()
        timelines = await self._get_setting("timelines", DEFAULT_TIMELINES)
        scoring_wrap = await self._get_setting(
            "scoring", {"criteria": DEFAULT_SCORING}
        )
        scoring = scoring_wrap.get("criteria", DEFAULT_SCORING)
        points = await self._get_setting("point_overrides", DEFAULT_POINT_OVERRIDES)
        pool = await self._get_setting("pool", DEFAULT_POOL)
        cats = (await self.session.execute(select(Category))).scalars().all()
        panels = (await self.session.execute(select(ReviewPanel))).scalars().all()
        return AdminConfigOut(
            timelines={k: int(v) for k, v in timelines.items()},
            scoring=list(scoring),
            point_overrides={k: int(v) for k, v in points.items()},
            pool=pool,
            categories=[CategoryOut.model_validate(c) for c in cats],
            panels=[
                PanelOut(
                    id=p.id,
                    slug=p.slug,
                    category_id=p.category_id,
                    name=p.name,
                    member_ids=[
                        uuid.UUID(str(x)) if not isinstance(x, uuid.UUID) else x
                        for x in (p.member_ids or [])
                    ],
                    chair_id=p.chair_id,
                )
                for p in panels
            ],
        )

    async def save_timelines(self, body: TimelinesIn, actor: Actor) -> dict[str, int]:
        _require_admin(actor)
        if body.pickup_days > body.decision_days:
            raise HTTPException(
                status_code=400,
                detail="Pickup cannot take longer than the whole decision window",
            )
        old = await self._get_setting("timelines", DEFAULT_TIMELINES)
        new = body.model_dump()
        changes = [
            {"field": k, "from": old.get(k), "to": v}
            for k, v in new.items()
            if old.get(k) != v
        ]
        await self._set_setting(
            "timelines",
            new,
            actor,
            "Timelines",
            "Updated review SLAs",
            changes,
        )
        return new

    async def save_scoring(self, body: ScoringIn, actor: Actor) -> list[dict[str, Any]]:
        _require_admin(actor)
        total = sum(c.weight for c in body.criteria)
        if total != 100:
            raise HTTPException(
                status_code=400, detail=f"Scoring weights must sum to 100 (got {total})"
            )
        criteria = [c.model_dump() for c in body.criteria]
        await self._set_setting(
            "scoring",
            {"criteria": criteria},
            actor,
            "Scoring",
            "Updated scoring criteria weights",
            [{"field": "criteria", "to": criteria}],
        )
        return criteria

    async def save_points(
        self, body: PointOverridesIn, actor: Actor
    ) -> dict[str, int]:
        _require_admin(actor)
        merged = {**DEFAULT_POINT_OVERRIDES, **body.overrides}
        await self._set_setting(
            "point_overrides",
            merged,
            actor,
            "Recognition",
            "Updated point value overlays (future ledger rows only)",
            [{"field": k, "to": v} for k, v in body.overrides.items()],
        )
        return {k: int(v) for k, v in merged.items()}

    async def _unique_category_slug(self, desired: str) -> str:
        base = _slugify(desired)
        slug = base
        n = 2
        while True:
            existing = (
                await self.session.execute(
                    select(Category.id).where(Category.slug == slug)
                )
            ).scalar_one_or_none()
            if existing is None:
                return slug
            suffix = f"-{n}"
            slug = (base[: max(1, 64 - len(suffix))] + suffix)[:64]
            n += 1

    async def _assert_reviewer(self, user_id: uuid.UUID) -> User:
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        roles = [str(r).lower() for r in (user.roles or [])]
        if "reviewer" not in roles and "admin" not in roles:
            raise HTTPException(
                status_code=400,
                detail="Only people with the Reviewer role can be added to a panel",
            )
        return user

    async def create_category(
        self, body: CategoryCreateIn, actor: Actor
    ) -> CategoryOut:
        """Create a category and its 1:1 review panel with the first reviewer.

        Side Effects:
            Inserts ``categories`` and ``review_panels`` rows and an audit entry.
            The new category is enabled and appears on Submit / Explore immediately.
        """
        _require_admin(actor)
        label = body.label.strip()
        description = body.description.strip()
        if len(description) < 10:
            raise HTTPException(
                status_code=400,
                detail="Describe the category in 10 to 160 characters",
            )
        dup = (
            await self.session.execute(
                select(Category).where(func.lower(Category.label) == label.lower())
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(
                status_code=400,
                detail="Another category already has this name",
            )
        color = _color_from_key(body.color_key)
        reviewer = await self._assert_reviewer(body.reviewer_id)
        slug = await self._unique_category_slug(body.slug or label)
        cat = Category(
            slug=slug,
            label=label,
            color=color,
            description=description,
            enabled=True,
        )
        self.session.add(cat)
        await self.session.flush()
        panel = ReviewPanel(
            slug=f"panel_{slug}"[:64],
            category_id=cat.id,
            name=f"{label} review panel",
            member_ids=[str(reviewer.id)],
            chair_id=reviewer.id,
        )
        self.session.add(panel)
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="Categories",
                summary=f'Added category "{label}"',
                changes=[
                    {"field": "Category", "from": "(none)", "to": label},
                    {
                        "field": "First reviewer",
                        "from": "(none)",
                        "to": reviewer.name,
                    },
                ],
            )
        )
        await self.session.commit()
        await self.session.refresh(cat)
        return CategoryOut.model_validate(cat)

    async def update_category(
        self, category_id: uuid.UUID, body: CategoryUpdateIn, actor: Actor
    ) -> CategoryOut:
        _require_admin(actor)
        cat = await self.session.get(Category, category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        if body.enabled is False and cat.enabled:
            enabled_count = int(
                (
                    await self.session.execute(
                        select(func.count())
                        .select_from(Category)
                        .where(Category.enabled.is_(True))
                    )
                ).scalar_one()
            )
            if enabled_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f'At least one category must stay enabled, so '
                        f'"{cat.label}" cannot be disabled.'
                    ),
                )
        if body.label is not None:
            other = (
                await self.session.execute(
                    select(Category).where(
                        func.lower(Category.label) == body.label.strip().lower(),
                        Category.id != cat.id,
                    )
                )
            ).scalar_one_or_none()
            if other:
                raise HTTPException(
                    status_code=400,
                    detail="Another category already has this name",
                )
        changes: list[dict[str, Any]] = []
        if body.color_key is not None:
            new_color = _color_from_key(body.color_key)
            if cat.color != new_color:
                changes.append(
                    {"field": "color", "from": cat.color, "to": new_color}
                )
                cat.color = new_color
        elif body.color is not None and cat.color != body.color:
            changes.append({"field": "color", "from": cat.color, "to": body.color})
            cat.color = body.color
        for field in ("label", "description", "enabled"):
            val = getattr(body, field)
            if val is None:
                continue
            if field in ("label", "description") and isinstance(val, str):
                val = val.strip()
            if getattr(cat, field) != val:
                changes.append(
                    {"field": field, "from": getattr(cat, field), "to": val}
                )
                setattr(cat, field, val)
        if changes:
            panel = (
                await self.session.execute(
                    select(ReviewPanel).where(ReviewPanel.category_id == cat.id)
                )
            ).scalar_one_or_none()
            if panel and body.label:
                panel.name = f"{body.label.strip()} review panel"
            self.session.add(
                AdminAudit(
                    actor_id=actor.id,
                    section="Categories",
                    summary=f"Updated category {cat.slug}",
                    changes=changes,
                )
            )
            await self.session.commit()
            await self.session.refresh(cat)
        return CategoryOut.model_validate(cat)

    async def create_panel(
        self, body: PanelCreateIn, actor: Actor
    ) -> PanelOut:
        """Create a panel for a category that does not already have one."""
        _require_admin(actor)
        cat = await self.session.get(Category, body.category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        existing = (
            await self.session.execute(
                select(ReviewPanel).where(ReviewPanel.category_id == cat.id)
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This category already has a review panel",
            )
        members: list[str] = []
        for uid in body.member_ids:
            await self._assert_reviewer(uid)
            sid = str(uid)
            if sid not in members:
                members.append(sid)
        chair = body.chair_id or body.member_ids[0]
        if str(chair) not in members:
            raise HTTPException(
                status_code=400, detail="Chair must be a member of the panel"
            )
        panel = ReviewPanel(
            slug=f"panel_{cat.slug}"[:64],
            category_id=cat.id,
            name=(body.name or f"{cat.label} review panel").strip(),
            member_ids=members,
            chair_id=chair,
        )
        self.session.add(panel)
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="Review panels",
                summary=f"Created panel for {cat.label}",
                changes=[{"field": "members", "to": len(members)}],
            )
        )
        await self.session.commit()
        await self.session.refresh(panel)
        return self._panel_out(panel)

    async def update_panel(
        self, panel_id: uuid.UUID, body: PanelUpdateIn, actor: Actor
    ) -> PanelOut:
        """Update panel name and/or replace membership in one request."""
        _require_admin(actor)
        panel = await self.session.get(ReviewPanel, panel_id)
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        changes: list[dict[str, Any]] = []
        if body.name is not None and body.name.strip() != panel.name:
            changes.append(
                {"field": "name", "from": panel.name, "to": body.name.strip()}
            )
            panel.name = body.name.strip()
        if body.member_ids is not None:
            members: list[str] = []
            for uid in body.member_ids:
                await self._assert_reviewer(uid)
                sid = str(uid)
                if sid not in members:
                    members.append(sid)
            if not members:
                raise HTTPException(
                    status_code=400, detail="A panel needs at least one reviewer"
                )
            old = [str(x) for x in (panel.member_ids or [])]
            if members != old:
                changes.append(
                    {
                        "field": "members",
                        "from": len(old),
                        "to": len(members),
                    }
                )
                panel.member_ids = members
        members_now = [str(x) for x in (panel.member_ids or [])]
        if body.chair_id is not None:
            if str(body.chair_id) not in members_now:
                raise HTTPException(
                    status_code=400, detail="Chair must be a member of the panel"
                )
            if panel.chair_id != body.chair_id:
                changes.append(
                    {
                        "field": "chair",
                        "from": str(panel.chair_id),
                        "to": str(body.chair_id),
                    }
                )
                panel.chair_id = body.chair_id
        elif panel.chair_id is None or str(panel.chair_id) not in members_now:
            panel.chair_id = uuid.UUID(members_now[0]) if members_now else None
        if changes:
            self.session.add(
                AdminAudit(
                    actor_id=actor.id,
                    section="Review panels",
                    summary=f"Updated {panel.name}",
                    changes=changes,
                )
            )
            await self.session.commit()
            await self.session.refresh(panel)
        return self._panel_out(panel)

    async def add_panel_member(
        self, panel_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
    ) -> PanelOut:
        _require_admin(actor)
        panel = await self.session.get(ReviewPanel, panel_id)
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        roles = [str(r).lower() for r in (user.roles or [])]
        if "reviewer" not in roles and "admin" not in roles:
            raise HTTPException(
                status_code=400,
                detail="Only people with the Reviewer role can be added to a panel",
            )
        members = [str(x) for x in (panel.member_ids or [])]
        uid = str(user_id)
        if uid not in members:
            members.append(uid)
            panel.member_ids = members
            if not panel.chair_id:
                panel.chair_id = user_id
            self.session.add(
                AdminAudit(
                    actor_id=actor.id,
                    section="Review panels",
                    summary=f"Added {user.name} to {panel.name}",
                    changes=[{"field": "members", "to": len(members)}],
                )
            )
            await self.session.commit()
            await self.session.refresh(panel)
        return self._panel_out(panel)

    async def remove_panel_member(
        self, panel_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
    ) -> PanelOut:
        _require_admin(actor)
        panel = await self.session.get(ReviewPanel, panel_id)
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        members = [str(x) for x in (panel.member_ids or [])]
        uid = str(user_id)
        if uid not in members:
            raise HTTPException(status_code=400, detail="User is not on this panel")
        if len(members) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the only member of a panel",
            )
        members = [m for m in members if m != uid]
        panel.member_ids = members
        if panel.chair_id == user_id:
            panel.chair_id = uuid.UUID(members[0])
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="Review panels",
                summary=f"Removed member from {panel.name}",
                changes=[{"field": "members", "to": len(members)}],
            )
        )
        await self.session.commit()
        await self.session.refresh(panel)
        return self._panel_out(panel)

    async def set_chair(
        self, panel_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
    ) -> PanelOut:
        _require_admin(actor)
        panel = await self.session.get(ReviewPanel, panel_id)
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        members = [str(x) for x in (panel.member_ids or [])]
        if str(user_id) not in members:
            raise HTTPException(
                status_code=400, detail="Chair must be a member of the panel"
            )
        old = panel.chair_id
        panel.chair_id = user_id
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="Review panels",
                summary=f"Changed chair of {panel.name}",
                changes=[{"field": "chair", "from": str(old), "to": str(user_id)}],
            )
        )
        await self.session.commit()
        await self.session.refresh(panel)
        return self._panel_out(panel)

    def _panel_out(self, panel: ReviewPanel) -> PanelOut:
        return PanelOut(
            id=panel.id,
            slug=panel.slug,
            category_id=panel.category_id,
            name=panel.name,
            member_ids=[
                uuid.UUID(str(x)) if not isinstance(x, uuid.UUID) else x
                for x in (panel.member_ids or [])
            ],
            chair_id=panel.chair_id,
        )

    async def audit_log(self, limit: int = 50) -> list[AuditOut]:
        rows = (
            await self.session.execute(
                select(AdminAudit)
                .order_by(AdminAudit.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [AuditOut.model_validate(r) for r in rows]

    async def list_users(
        self, actor: Actor, *, q: str | None = None
    ) -> list[AdminUserOut]:
        """List all users for Admin → People and roles (includes inactive).

        Args:
            actor: Caller; must hold Administrator.
            q: Optional case-insensitive filter on name, email, or title.

        Returns:
            Users ordered by name ascending.

        Raises:
            HTTPException: 403 when the actor is not an administrator.
        """
        _require_admin(actor)
        rows = (
            await self.session.execute(select(User).order_by(User.name.asc()))
        ).scalars().all()
        needle = (q or "").strip().lower()
        out: list[AdminUserOut] = []
        for u in rows:
            if needle:
                blob = f"{u.name} {u.email} {u.title or ''}".lower()
                if needle not in blob:
                    continue
            out.append(_user_admin_out(u))
        return out

    async def add_role(
        self, user_id: uuid.UUID, role: str, actor: Actor
    ) -> AdminRoleMutationOut:
        """Grant one role to a user (multi-role; matches idea-hub.html).

        Side Effects:
            Updates ``users.roles``, writes an admin audit row, commits.
        """
        _require_admin(actor)
        role = str(role).strip().lower()
        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Choose a role: "
                    + ", ".join(ROLE_ORDER)
                ),
            )
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        roles = _sort_roles([str(r) for r in (user.roles or [])])
        if role in roles:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{user.name} already holds the {_role_label(role)} role."
                ),
            )
        before = ", ".join(_role_label(r) for r in roles) or "(none)"
        roles = _sort_roles(roles + [role])
        user.roles = roles
        if user.primary_role not in roles:
            user.primary_role = roles[0]
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="People and roles",
                summary=f"Gave {user.name} the {_role_label(role)} role",
                changes=[
                    {
                        "field": f"{user.name} roles",
                        "from": before,
                        "to": ", ".join(_role_label(r) for r in roles),
                    }
                ],
            )
        )
        await self.session.commit()
        await self.session.refresh(user)
        return AdminRoleMutationOut(user=_user_admin_out(user))

    async def remove_role(
        self,
        user_id: uuid.UUID,
        role: str,
        actor: Actor,
        *,
        confirm: bool = False,
    ) -> AdminRoleMutationOut:
        """Remove one role; enforce last-role / last-admin / panel guards.

        When removing ``reviewer`` and the user sits on panels, callers must
        pass ``confirm=True`` after a 409 ``needs_confirm`` response. Panel
        seats are dropped and chairs reassigned to the remaining first member.

        Side Effects:
            Updates ``users.roles`` / ``primary_role``, may mutate panel
            membership, writes audit, commits.
        """
        _require_admin(actor)
        role = str(role).strip().lower()
        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=400,
                detail="Choose a role: " + ", ".join(ROLE_ORDER),
            )
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        roles = _sort_roles([str(r) for r in (user.roles or [])])
        if role not in roles:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{user.name} does not hold the {_role_label(role)} role."
                ),
            )
        if len(roles) <= 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Everyone needs at least one role, so the last role of "
                    f"{user.name} cannot be removed."
                ),
            )
        if user.primary_role == role:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{_role_label(role)} is the default role of {user.name}. "
                    "Set another role as the default first."
                ),
            )
        if role == "admin":
            admins = (
                await self.session.execute(select(User))
            ).scalars().all()
            admin_count = sum(
                1
                for u in admins
                if "admin" in [str(r).lower() for r in (u.roles or [])]
            )
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "There must always be at least one administrator, "
                        "so the last one cannot be removed."
                    ),
                )

        panels: list[ReviewPanel] = []
        panel_names: list[str] = []
        if role == "reviewer":
            uid = str(user_id)
            all_panels = (
                await self.session.execute(select(ReviewPanel))
            ).scalars().all()
            panels = [
                p
                for p in all_panels
                if uid in [str(x) for x in (p.member_ids or [])]
            ]
            panel_names = [p.name for p in panels]
            sole = [p for p in panels if len(p.member_ids or []) <= 1]
            if sole:
                names = " and the ".join(p.name for p in sole)
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{user.name} is the only member of the {names}. "
                        f"Add another reviewer to "
                        f"{'those panels' if len(sole) > 1 else 'that panel'} "
                        "first."
                    ),
                )
            if panels and not confirm:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            f"Removing the Reviewer role also removes "
                            f"{user.name} from: "
                            + ", ".join(panel_names)
                            + ". Confirm to continue."
                        ),
                        "needs_confirm": True,
                        "panels": panel_names,
                    },
                )

        before = ", ".join(_role_label(r) for r in roles)
        changes: list[dict[str, Any]] = []
        new_roles = [r for r in roles if r != role]
        user.roles = new_roles
        for panel in panels:
            members = [str(x) for x in (panel.member_ids or [])]
            before_n = len(members)
            members = [m for m in members if m != str(user_id)]
            panel.member_ids = members
            changes.append(
                {
                    "field": f"{panel.name} members",
                    "from": before_n,
                    "to": len(members),
                }
            )
            if panel.chair_id == user_id and members:
                panel.chair_id = uuid.UUID(members[0])
                changes.append(
                    {
                        "field": f"{panel.name} chair",
                        "from": user.name,
                        "to": members[0],
                    }
                )

        fell_back = actor.id == user_id and actor.active_role == role
        changes.insert(
            0,
            {
                "field": f"{user.name} roles",
                "from": before,
                "to": ", ".join(_role_label(r) for r in new_roles),
            },
        )
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="People and roles",
                summary=(
                    f"Removed the {_role_label(role)} role from {user.name}"
                ),
                changes=changes,
            )
        )
        await self.session.commit()
        await self.session.refresh(user)
        return AdminRoleMutationOut(
            user=_user_admin_out(user),
            fell_back=fell_back,
            panels_left=len(panels),
            panels=panel_names,
        )

    async def set_primary_role(
        self, user_id: uuid.UUID, body: AdminPrimaryRoleIn, actor: Actor
    ) -> AdminRoleMutationOut:
        """Set the user's default sign-in role (must already be held)."""
        _require_admin(actor)
        role = str(body.role).strip().lower()
        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=400,
                detail="Choose a role: " + ", ".join(ROLE_ORDER),
            )
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        roles = _sort_roles([str(r) for r in (user.roles or [])])
        if role not in roles:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{user.name} does not hold the {_role_label(role)} role."
                ),
            )
        if user.primary_role == role:
            return AdminRoleMutationOut(user=_user_admin_out(user))
        old = user.primary_role
        user.primary_role = role
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="People and roles",
                summary=(
                    f"Set the default role of {user.name} to {_role_label(role)}"
                ),
                changes=[
                    {
                        "field": f"{user.name} default role",
                        "from": _role_label(old),
                        "to": _role_label(role),
                    }
                ],
            )
        )
        await self.session.commit()
        await self.session.refresh(user)
        return AdminRoleMutationOut(user=_user_admin_out(user))

    async def _admin_counts(self) -> tuple[int, int]:
        """Return ``(all_admins, active_admins)`` across the directory."""
        rows = (await self.session.execute(select(User))).scalars().all()
        all_admins = 0
        active_admins = 0
        for u in rows:
            if not _user_holds_admin(u):
                continue
            all_admins += 1
            if str(u.status or "active") == "active":
                active_admins += 1
        return all_admins, active_admins

    async def _panels_for_user(
        self, user_id: uuid.UUID
    ) -> tuple[list[ReviewPanel], list[str]]:
        uid = str(user_id)
        all_panels = (
            await self.session.execute(select(ReviewPanel))
        ).scalars().all()
        panels = [
            p
            for p in all_panels
            if uid in [str(x) for x in (p.member_ids or [])]
        ]
        return panels, [p.name for p in panels]

    async def set_user_active(
        self, user_id: uuid.UUID, *, active: bool, actor: Actor
    ) -> AdminUserOut:
        """Enable or disable a user account (soft; reversible via ``status``).

        Disabled accounts keep all rows but cannot authenticate (password OTP
        or Microsoft SSO). Disabling clears any outstanding login OTP keys.

        Args:
            user_id: Target account.
            active: True to set ``status=active``, False for ``inactive``.
            actor: Caller; must hold Administrator.

        Returns:
            Updated admin directory row.

        Raises:
            HTTPException: 403 not admin; 404 missing; 400 self-target or
                last active administrator when disabling.
        """
        _require_admin(actor)
        if actor.id == user_id:
            raise HTTPException(
                status_code=400,
                detail="You cannot disable or enable your own account.",
            )
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        target_active = str(user.status or "active") == "active"
        if active and target_active:
            return _user_admin_out(user)
        if not active and not target_active:
            return _user_admin_out(user)

        if not active and _user_holds_admin(user):
            _all, active_admins = await self._admin_counts()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "There must always be at least one active administrator, "
                        "so the last active one cannot be disabled."
                    ),
                )

        before = user.status
        user.status = "active" if active else "inactive"
        if not active:
            _clear_login_otp_keys(user_id)

        verb = "Enabled" if active else "Disabled"
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="People and roles",
                summary=f"{verb} account {user.name} ({user.email})",
                changes=[
                    {
                        "field": f"{user.name} status",
                        "from": before,
                        "to": user.status,
                    }
                ],
            )
        )
        await self.session.commit()
        await self.session.refresh(user)
        return _user_admin_out(user)

    async def _detach_user_fks(
        self, user_id: uuid.UUID, *, reassign_to: uuid.UUID
    ) -> None:
        """Nullify, delete, or reassign rows that block hard-deleting ``user_id``.

        CASCADE FKs are left to the database. Nullable refs are SET NULL.
        Personal engagement rows are deleted. Content ownership that is NOT
        NULL is reassigned to ``reassign_to`` (the deleting administrator).
        """
        uid = user_id
        rid = reassign_to

        # Nullable → SET NULL
        await self.session.execute(
            update(AdminAudit).where(AdminAudit.actor_id == uid).values(actor_id=None)
        )
        await self.session.execute(
            update(CollabRequest)
            .where(CollabRequest.decided_by == uid)
            .values(decided_by=None)
        )
        await self.session.execute(
            update(Decision).where(Decision.owner_id == uid).values(owner_id=None)
        )
        await self.session.execute(
            update(DeliveryTask)
            .where(DeliveryTask.assignee_id == uid)
            .values(assignee_id=None)
        )
        await self.session.execute(
            update(DeliveryTask)
            .where(DeliveryTask.updated_by == uid)
            .values(updated_by=None)
        )
        await self.session.execute(
            update(Idea).where(Idea.owner_id == uid).values(owner_id=None)
        )
        await self.session.execute(
            update(Idea).where(Idea.reviewer_id == uid).values(reviewer_id=None)
        )
        await self.session.execute(
            update(Ideathon)
            .where(Ideathon.confirmed_by == uid)
            .values(confirmed_by=None)
        )
        await self.session.execute(
            update(ImpactEntry)
            .where(ImpactEntry.verified_by == uid)
            .values(verified_by=None)
        )
        await self.session.execute(
            update(KompassAnswer)
            .where(KompassAnswer.answered_by == uid)
            .values(answered_by=None)
        )
        await self.session.execute(
            update(PlatformSetting)
            .where(PlatformSetting.updated_by == uid)
            .values(updated_by=None)
        )
        await self.session.execute(
            update(ProblemMeta)
            .where(ProblemMeta.acknowledged_by == uid)
            .values(acknowledged_by=None)
        )
        await self.session.execute(
            update(ProblemMeta)
            .where(ProblemMeta.sponsor_id == uid)
            .values(sponsor_id=None)
        )
        await self.session.execute(
            update(ReopenConditionSet)
            .where(ReopenConditionSet.closed_by == uid)
            .values(closed_by=None)
        )
        await self.session.execute(
            update(ReopenConditionSet)
            .where(ReopenConditionSet.created_by == uid)
            .values(created_by=None)
        )
        await self.session.execute(
            update(ReviewPanel)
            .where(ReviewPanel.chair_id == uid)
            .values(chair_id=None)
        )
        await self.session.execute(
            update(StatusHistory)
            .where(StatusHistory.actor_id == uid)
            .values(actor_id=None)
        )
        await self.session.execute(
            update(Team).where(Team.lead_id == uid).values(lead_id=None)
        )
        await self.session.execute(
            update(TimeGrantRequest)
            .where(TimeGrantRequest.decided_by == uid)
            .values(decided_by=None)
        )
        await self.session.execute(
            update(TrackerMilestone)
            .where(TrackerMilestone.owner_id == uid)
            .values(owner_id=None)
        )

        # Personal / RESTRICT rows → DELETE
        await self.session.execute(delete(Comment).where(Comment.author_id == uid))
        await self.session.execute(delete(Follow).where(Follow.user_id == uid))
        await self.session.execute(delete(Vote).where(Vote.user_id == uid))
        await self.session.execute(delete(Review).where(Review.reviewer_id == uid))
        await self.session.execute(
            delete(DeliveryUpdate).where(DeliveryUpdate.user_id == uid)
        )
        await self.session.execute(delete(TimeLog).where(TimeLog.user_id == uid))
        await self.session.execute(
            delete(TimeGrantRequest).where(TimeGrantRequest.requested_by == uid)
        )
        await self.session.execute(
            delete(TrackerCheckin).where(TrackerCheckin.author_id == uid)
        )

        # Required ownership → reassign to deleting admin
        await self.session.execute(
            update(Idea).where(Idea.author_id == uid).values(author_id=rid)
        )
        await self.session.execute(
            update(TrackerMilestone)
            .where(TrackerMilestone.created_by == uid)
            .values(created_by=rid)
        )
        await self.session.execute(
            update(Decision).where(Decision.decider_id == uid).values(decider_id=rid)
        )
        await self.session.execute(
            update(DeliveryTask)
            .where(DeliveryTask.created_by == uid)
            .values(created_by=rid)
        )
        await self.session.execute(
            update(DeliveryContributor)
            .where(DeliveryContributor.added_by == uid)
            .values(added_by=rid)
        )
        await self.session.execute(
            update(IdeathonEntry)
            .where(IdeathonEntry.linked_by == uid)
            .values(linked_by=rid)
        )
        await self.session.execute(
            update(IdeathonHandoff)
            .where(IdeathonHandoff.sent_by == uid)
            .values(sent_by=rid)
        )
        await self.session.execute(
            update(Ideathon)
            .where(Ideathon.organiser_id == uid)
            .values(organiser_id=rid)
        )
        await self.session.execute(
            update(Ideathon).where(Ideathon.sponsor_id == uid).values(sponsor_id=rid)
        )
        await self.session.execute(
            update(ImpactEntry)
            .where(ImpactEntry.created_by == uid)
            .values(created_by=rid)
        )
        await self.session.execute(
            update(ProposalDecision)
            .where(ProposalDecision.decided_by == uid)
            .values(decided_by=rid)
        )
        await self.session.execute(
            update(RecognitionAward)
            .where(RecognitionAward.confirmed_by == uid)
            .values(confirmed_by=rid)
        )

    async def delete_user(
        self,
        user_id: uuid.UUID,
        actor: Actor,
        *,
        confirm: bool = False,
    ) -> AdminUserDeleteOut:
        """Hard-delete a user after FK-safe cleanup and guard checks.

        Guards mirror role-remove: cannot delete yourself, cannot delete the
        last administrator (any status), cannot leave a review panel empty.
        Sitting on panels requires ``confirm=True`` (409 ``needs_confirm``).

        Side Effects:
            Removes panel seats, detaches/reassigns FKs, deletes the user row,
            writes an audit row, clears Redis OTP keys, commits.
        """
        _require_admin(actor)
        if actor.id == user_id:
            raise HTTPException(
                status_code=400,
                detail="You cannot delete your own account.",
            )
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if _user_holds_admin(user):
            all_admins, _active = await self._admin_counts()
            if all_admins <= 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "There must always be at least one administrator, "
                        "so the last one cannot be deleted."
                    ),
                )

        panels, panel_names = await self._panels_for_user(user_id)
        sole = [p for p in panels if len(p.member_ids or []) <= 1]
        if sole:
            names = " and the ".join(p.name for p in sole)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{user.name} is the only member of the {names}. "
                    f"Add another reviewer to "
                    f"{'those panels' if len(sole) > 1 else 'that panel'} "
                    "first."
                ),
            )
        if panels and not confirm:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        f"Deleting {user.name} also removes them from: "
                        + ", ".join(panel_names)
                        + ". Confirm to continue."
                    ),
                    "needs_confirm": True,
                    "panels": panel_names,
                },
            )

        email = user.email
        name = user.name
        changes: list[dict[str, Any]] = [
            {"field": "account", "from": email, "to": "(deleted)"}
        ]

        for panel in panels:
            members = [str(x) for x in (panel.member_ids or [])]
            before_n = len(members)
            members = [m for m in members if m != str(user_id)]
            panel.member_ids = members
            changes.append(
                {
                    "field": f"{panel.name} members",
                    "from": before_n,
                    "to": len(members),
                }
            )
            if panel.chair_id == user_id and members:
                panel.chair_id = uuid.UUID(members[0])
                changes.append(
                    {
                        "field": f"{panel.name} chair",
                        "from": name,
                        "to": members[0],
                    }
                )

        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="People and roles",
                summary=f"Deleted account {name} ({email})",
                changes=changes,
            )
        )
        await self.session.flush()

        await self._detach_user_fks(user_id, reassign_to=actor.id)
        await self.session.delete(user)
        _clear_login_otp_keys(user_id)
        await self.session.commit()

        return AdminUserDeleteOut(
            id=user_id,
            email=email,
            name=name,
            panels_left=len(panels),
        )

    async def export_inventory(self) -> ExportOut:
        counts: dict[str, int] = {}
        for label, model in (
            ("users", User),
            ("categories", Category),
            ("ideas", Idea),
            ("panels", ReviewPanel),
        ):
            counts[label] = int(
                (
                    await self.session.execute(select(func.count()).select_from(model))
                ).scalar_one()
            )
        return ExportOut(generated_at=_now(), counts=counts)

    async def reset_demo_hook(self, actor: Actor) -> ResetOut:
        """Thin reset hook — records audit; actual reseed is a separate CLI.

        Does not wipe production data from this endpoint. Operators run
        ``python -m app.seed.demo`` after confirming.
        """
        _require_admin(actor)
        self.session.add(
            AdminAudit(
                actor_id=actor.id,
                section="Data",
                summary="Reset demo data requested (hook only — run seed CLI)",
                changes=[],
            )
        )
        await self.session.commit()
        return ResetOut(
            ok=True,
            message=(
                "Reset acknowledged. Run `python -m app.seed.demo` (and phase "
                "seeds) to reload demo data. This API does not truncate tables."
            ),
        )
