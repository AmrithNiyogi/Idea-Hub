"""Signed-in account settings — profile fields, password, avatar upload.

Responsibilities:
- Update display name, title, avatar color preset, and avatar_url.
- Change password with bcrypt after verifying the current credential.
- Persist uploaded avatar files under a local uploads directory.

Collaborators:
- User ORM model
- auth_service.hash_password / verify_password

Must never:
- Expose password hashes
- Allow changing email or roles through this path
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, UpdateMeRequest, UserPublic
from app.services.auth_service import hash_password, user_to_public, verify_password

logger = logging.getLogger("idea_hub.account")

ALLOWED_AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MiB
_HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def uploads_root() -> Path:
    """Absolute path for persisted user uploads (avatars)."""
    root = Path(settings.UPLOAD_DIR)
    if not root.is_absolute():
        # Resolve relative to backend/ working directory (uvicorn cwd).
        root = Path.cwd() / root
    return root.resolve()


def avatar_public_url(relative_name: str) -> str:
    """Build the public URL path served by StaticFiles at /uploads."""
    return f"/uploads/avatars/{relative_name}"


async def update_me(
    session: AsyncSession,
    user: User,
    body: UpdateMeRequest,
    *,
    active_role: str | None = None,
) -> UserPublic:
    """Apply partial profile updates for the signed-in user.

    Args:
        session: Active DB session (caller commits).
        user: ORM user to mutate.
        body: Fields to update; omitted fields are left unchanged.
        active_role: Session active role for the response payload.

    Returns:
        UserPublic: Updated public user shape.

    Raises:
        HTTPException: 400 when avatar preset or URL is invalid.
    """
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Display name cannot be empty",
            )
        user.name = name

    if body.title is not None:
        user.title = body.title.strip()

    if body.avatar is not None:
        if body.avatar < 1 or body.avatar > 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avatar color preset must be between 1 and 8",
            )
        user.avatar = body.avatar

    if body.avatar_url is not None:
        url = body.avatar_url.strip()
        if url == "":
            user.avatar_url = None
        elif url.startswith("/uploads/avatars/"):
            user.avatar_url = url
        elif _HTTP_URL_RE.match(url) and len(url) <= 512:
            user.avatar_url = url
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="avatar_url must be an http(s) URL or a /uploads/avatars/ path",
            )

    await session.flush()
    await session.refresh(user)
    return user_to_public(user, active_role=active_role)


async def change_password(
    session: AsyncSession,
    user: User,
    body: ChangePasswordRequest,
) -> None:
    """Verify current password and replace with a new bcrypt hash.

    Args:
        session: Active DB session (caller commits).
        user: ORM user whose credentials are updated.
        body: Current + new password (new must match confirm).

    Raises:
        HTTPException: 400 on mismatch / weak new password; 401 on bad current.
    """
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password",
        )
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    user.password_hash = hash_password(body.new_password)
    user.has_password = True
    await session.flush()
    logger.info("Password changed for user_id=%s", user.id)


async def save_avatar_upload(
    session: AsyncSession,
    user: User,
    file: UploadFile,
    *,
    active_role: str | None = None,
) -> UserPublic:
    """Validate and store an avatar image; set user.avatar_url.

    Args:
        session: Active DB session (caller commits).
        user: Signed-in user.
        file: Multipart image upload.
        active_role: Session active role for the response.

    Returns:
        UserPublic: User with updated avatar_url.

    Raises:
        HTTPException: 400 for missing/invalid type or oversize payload.
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_AVATAR_TYPES.get(content_type)
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be JPEG, PNG, WebP, or GIF",
        )

    data = await file.read(MAX_AVATAR_BYTES + 1)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty avatar file",
        )
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be 2 MB or smaller",
        )

    avatars_dir = uploads_root() / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # Remove previous local upload if we own it.
    if user.avatar_url and user.avatar_url.startswith("/uploads/avatars/"):
        old = uploads_root() / "avatars" / Path(user.avatar_url).name
        try:
            if old.is_file() and old.resolve().parent == avatars_dir.resolve():
                old.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove old avatar %s", old)

    filename = f"{user.id}_{uuid.uuid4().hex[:12]}{ext}"
    dest = avatars_dir / filename
    dest.write_bytes(data)

    user.avatar_url = avatar_public_url(filename)
    await session.flush()
    await session.refresh(user)
    return user_to_public(user, active_role=active_role)
