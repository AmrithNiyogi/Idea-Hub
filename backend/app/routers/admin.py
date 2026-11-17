"""Admin configuration HTTP API — Phase 4.

Exposes platform settings (timelines, scoring, points), category CRUD
(soft-disable), review-panel membership, and People and roles (list users,
grant/remove roles, set primary). Mutate endpoints require Administrator.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.admin import (
    AdminConfigOut,
    AdminPrimaryRoleIn,
    AdminRoleIn,
    AdminRoleMutationOut,
    AdminUserOut,
    AuditOut,
    CategoryCreateIn,
    CategoryOut,
    CategoryUpdateIn,
    ExportOut,
    PanelChairIn,
    PanelCreateIn,
    PanelMemberIn,
    PanelOut,
    PanelUpdateIn,
    PointOverridesIn,
    ResetOut,
    ScoringIn,
    TimelinesIn,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/config",
    response_model=AdminConfigOut,
    summary="Full admin config snapshot",
    description=(
        "Returns timelines, scoring criteria, point overlays, categories, "
        "and review panels. Ensures default settings and one panel per "
        "category when missing."
    ),
)
async def get_config(session: DbSession, actor: RequireActor) -> AdminConfigOut:
    return await AdminService(session).config()


@router.put(
    "/timelines",
    response_model=dict,
    summary="Save review SLA timelines",
)
async def save_timelines(
    body: TimelinesIn, session: DbSession, actor: RequireActor
) -> dict:
    return await AdminService(session).save_timelines(body, actor)


@router.put(
    "/scoring",
    response_model=list,
    summary="Save scoring criteria weights (must sum to 100)",
)
async def save_scoring(
    body: ScoringIn, session: DbSession, actor: RequireActor
) -> list:
    return await AdminService(session).save_scoring(body, actor)


@router.put(
    "/points",
    response_model=dict,
    summary="Save recognition point-value overlays",
)
async def save_points(
    body: PointOverridesIn, session: DbSession, actor: RequireActor
) -> dict:
    return await AdminService(session).save_points(body, actor)


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category and its review panel",
    description=(
        "Creates an enabled category and a dedicated review panel seeded "
        "with the chosen first reviewer as member and chair. The category "
        "appears on Submit and Explore immediately."
    ),
    responses={
        400: {"description": "Validation failed (duplicate name, colour, reviewer)"},
        403: {"description": "Administrator role required"},
    },
)
async def create_category(
    body: CategoryCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> CategoryOut:
    return await AdminService(session).create_category(body, actor)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryOut,
    summary="Update a category",
    description=(
        "Partial update of label, description, colour, or enabled flag. "
        "Disabling is a soft delete: the category leaves Submit; existing "
        "ideas keep their label. At least one category must stay enabled."
    ),
    responses={
        400: {"description": "Cannot disable the last enabled category"},
        404: {"description": "Category not found"},
    },
)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdateIn,
    session: DbSession,
    actor: RequireActor,
) -> CategoryOut:
    return await AdminService(session).update_category(category_id, body, actor)


@router.post(
    "/panels",
    response_model=PanelOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review panel for a category without one",
    description=(
        "Categories normally get a panel on create. Use this when a "
        "category is missing its panel (one panel per category)."
    ),
    responses={
        400: {"description": "Category already has a panel or invalid members"},
        404: {"description": "Category not found"},
    },
)
async def create_panel(
    body: PanelCreateIn,
    session: DbSession,
    actor: RequireActor,
) -> PanelOut:
    return await AdminService(session).create_panel(body, actor)


@router.put(
    "/panels/{panel_id}",
    response_model=PanelOut,
    summary="Update panel name and/or membership",
    description=(
        "Replace name, member list, and/or chair in one request. "
        "Member list is a full replacement when provided."
    ),
)
async def update_panel(
    panel_id: uuid.UUID,
    body: PanelUpdateIn,
    session: DbSession,
    actor: RequireActor,
) -> PanelOut:
    return await AdminService(session).update_panel(panel_id, body, actor)


@router.post(
    "/panels/{panel_id}/members",
    response_model=PanelOut,
    summary="Add a reviewer to a panel",
)
async def add_member(
    panel_id: uuid.UUID,
    body: PanelMemberIn,
    session: DbSession,
    actor: RequireActor,
) -> PanelOut:
    return await AdminService(session).add_panel_member(
        panel_id, body.user_id, actor
    )


@router.delete(
    "/panels/{panel_id}/members/{user_id}",
    response_model=PanelOut,
    summary="Remove a panel member",
)
async def remove_member(
    panel_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
) -> PanelOut:
    return await AdminService(session).remove_panel_member(panel_id, user_id, actor)


@router.put(
    "/panels/{panel_id}/chair",
    response_model=PanelOut,
    summary="Set panel chair",
)
async def set_chair(
    panel_id: uuid.UUID,
    body: PanelChairIn,
    session: DbSession,
    actor: RequireActor,
) -> PanelOut:
    return await AdminService(session).set_chair(panel_id, body.user_id, actor)


@router.get(
    "/users",
    response_model=list[AdminUserOut],
    summary="List users for People and roles",
    description=(
        "Administrator-only directory of all users (including inactive) with "
        "id, email, name, title, roles, primary_role, status, and is_active. "
        "Optional ``q`` filters by name, email, or title. Distinct from "
        "``GET /users``, which returns active users for pickers."
    ),
    responses={
        403: {"description": "Administrator role required"},
    },
)
async def list_admin_users(
    session: DbSession,
    actor: RequireActor,
    q: str | None = Query(
        None,
        description="Case-insensitive filter on name, email, or title.",
    ),
) -> list[AdminUserOut]:
    return await AdminService(session).list_users(actor, q=q)


@router.post(
    "/users/{user_id}/roles",
    response_model=AdminRoleMutationOut,
    summary="Grant a role to a user",
    description=(
        "Adds one role from the platform role set "
        "(contributor, reviewer, lead, leadership, admin). "
        "Multi-role: existing roles are kept. Audited under People and roles."
    ),
    responses={
        400: {"description": "Unknown role, duplicate role, or user missing"},
        403: {"description": "Administrator role required"},
        404: {"description": "User not found"},
    },
)
async def add_user_role(
    user_id: uuid.UUID,
    body: AdminRoleIn,
    session: DbSession,
    actor: RequireActor,
) -> AdminRoleMutationOut:
    return await AdminService(session).add_role(user_id, body.role, actor)


@router.delete(
    "/users/{user_id}/roles/{role}",
    response_model=AdminRoleMutationOut,
    summary="Remove a role from a user",
    description=(
        "Removes one held role. Guards: cannot remove the last role, cannot "
        "remove the default role without changing primary first, cannot remove "
        "the last administrator, cannot leave a review panel with zero members. "
        "Removing Reviewer while the user sits on panels requires "
        "``confirm=true`` query; otherwise returns 409 with "
        "``needs_confirm`` and panel names."
    ),
    responses={
        400: {"description": "Validation / last-role / last-admin / sole panel member"},
        403: {"description": "Administrator role required"},
        404: {"description": "User not found"},
        409: {"description": "Confirm required to drop Reviewer panel seats"},
    },
)
async def remove_user_role(
    user_id: uuid.UUID,
    role: str,
    session: DbSession,
    actor: RequireActor,
    confirm: bool = Query(
        False,
        description="Confirm dropping Reviewer seats on review panels.",
    ),
) -> AdminRoleMutationOut:
    return await AdminService(session).remove_role(
        user_id, role, actor, confirm=confirm
    )


@router.put(
    "/users/{user_id}/primary-role",
    response_model=AdminRoleMutationOut,
    summary="Set a user's default (primary) role",
    description=(
        "Sets ``primary_role`` used at sign-in. The role must already be in "
        "the user's roles list."
    ),
    responses={
        400: {"description": "Role not held or invalid"},
        403: {"description": "Administrator role required"},
        404: {"description": "User not found"},
    },
)
async def set_user_primary_role(
    user_id: uuid.UUID,
    body: AdminPrimaryRoleIn,
    session: DbSession,
    actor: RequireActor,
) -> AdminRoleMutationOut:
    return await AdminService(session).set_primary_role(user_id, body, actor)


@router.get(
    "/audit",
    response_model=list[AuditOut],
    summary="Admin audit log",
)
async def audit(
    session: DbSession,
    actor: RequireActor,
    limit: int = Query(50, ge=1, le=200),
) -> list[AuditOut]:
    return await AdminService(session).audit_log(limit)


@router.get(
    "/export",
    response_model=ExportOut,
    summary="Export inventory counts (thin hook)",
)
async def export_inventory(session: DbSession, actor: RequireActor) -> ExportOut:
    return await AdminService(session).export_inventory()


@router.post(
    "/reset",
    response_model=ResetOut,
    summary="Reset demo data hook (does not truncate; run seed CLI)",
)
async def reset_demo(session: DbSession, actor: RequireActor) -> ResetOut:
    return await AdminService(session).reset_demo_hook(actor)
