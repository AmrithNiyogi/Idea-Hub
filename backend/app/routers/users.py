"""User routes — current profile, account settings, and lightweight directories."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.dependencies.auth import DbSession, RequireUser
from app.models.category import Category
from app.models.user import Team, User
from app.schemas.auth import (
    ChangePasswordRequest,
    MessageResponse,
    UpdateMeRequest,
    UserPublic,
)
from app.services import account_service
from app.services.auth_service import user_to_public

router = APIRouter(tags=["users"])


@router.get(
    "/users/me",
    response_model=UserPublic,
    summary="Current authenticated user",
    description="Return the signed-in user including roles, active_role, and avatar fields.",
)
async def me(current: RequireUser, session: DbSession) -> UserPublic:
    """Return the signed-in user with roles and active_role from the JWT."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_to_public(user, active_role=current.active_role)


@router.patch(
    "/users/me",
    response_model=UserPublic,
    summary="Update own profile",
    description=(
        "Partial update of display name, job title, avatar color preset (1–8), "
        "and/or avatar_url. Email and roles are not editable here."
    ),
    responses={
        400: {"description": "Validation error (empty name, bad avatar, bad URL)"},
        401: {"description": "Not authenticated"},
    },
)
async def update_me(
    body: UpdateMeRequest,
    current: RequireUser,
    session: DbSession,
) -> UserPublic:
    """Update the signed-in user's profile fields."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await account_service.update_me(
        session, user, body, active_role=current.active_role
    )
    await session.commit()
    return result


@router.post(
    "/users/me/password",
    response_model=MessageResponse,
    summary="Change own password",
    description=(
        "Verify current_password, then replace with bcrypt-hashed new_password. "
        "confirm_password must match new_password (min 8 characters)."
    ),
    responses={
        400: {"description": "Mismatch or new password invalid"},
        401: {"description": "Current password incorrect or not authenticated"},
    },
)
async def change_my_password(
    body: ChangePasswordRequest,
    current: RequireUser,
    session: DbSession,
) -> MessageResponse:
    """Change the signed-in user's password."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    await account_service.change_password(session, user, body)
    await session.commit()
    return MessageResponse(message="Password updated")


@router.post(
    "/users/me/avatar",
    response_model=UserPublic,
    summary="Upload profile avatar",
    description=(
        "Multipart image upload (JPEG/PNG/WebP/GIF, max 2 MB). "
        "Stored under uploads/avatars/ and exposed at /uploads/avatars/…."
    ),
    responses={
        400: {"description": "Invalid type, empty, or oversize file"},
        401: {"description": "Not authenticated"},
    },
)
async def upload_my_avatar(
    current: RequireUser,
    session: DbSession,
    file: UploadFile = File(..., description="Avatar image file"),
) -> UserPublic:
    """Upload and set the signed-in user's avatar image."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await account_service.save_avatar_upload(
        session, user, file, active_role=current.active_role
    )
    await session.commit()
    return result


@router.get("/users", response_model=list[UserPublic], summary="List users")
async def list_users(session: DbSession, _: RequireUser) -> list[UserPublic]:
    """Return active users (for co-author / owner pickers)."""
    result = await session.execute(
        select(User).where(User.status == "active").order_by(User.name.asc())
    )
    return [user_to_public(u) for u in result.scalars().all()]


@router.get("/users/{user_id}", response_model=UserPublic, summary="Get user")
async def get_user(
    user_id: UUID, session: DbSession, _: RequireUser
) -> UserPublic:
    """Return a single user by id."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_public(user)


@router.get("/teams", summary="List teams")
async def list_teams(session: DbSession, _: RequireUser) -> list[dict]:
    """Return teams for filters / display."""
    result = await session.execute(select(Team).order_by(Team.name.asc()))
    return [
        {"id": t.id, "slug": t.slug, "name": t.name, "lead_id": t.lead_id}
        for t in result.scalars().all()
    ]


@router.get("/categories", summary="List categories")
async def list_categories(session: DbSession) -> list[dict]:
    """Return enabled idea categories (public for submit form)."""
    result = await session.execute(
        select(Category)
        .where(Category.enabled.is_(True))
        .order_by(Category.label.asc())
    )
    return [
        {
            "id": c.id,
            "slug": c.slug,
            "label": c.label,
            "color": c.color,
            "description": c.description,
        }
        for c in result.scalars().all()
    ]
