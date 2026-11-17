"""Unit tests for Admin People and roles helpers / validation paths."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.dependencies.phase23_auth import Actor
from app.schemas.admin import AdminPrimaryRoleIn
from app.services.admin_service import (
    AdminService,
    _role_label,
    _sort_roles,
    _user_admin_out,
)


def test_sort_roles_orders_by_platform_order() -> None:
    assert _sort_roles(["admin", "contributor", "lead"]) == [
        "contributor",
        "lead",
        "admin",
    ]


def test_role_label_known_and_unknown() -> None:
    assert _role_label("leadership") == "Leadership"
    assert _role_label("custom") == "custom"


def test_user_admin_out_active_flag() -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="a@example.com",
        name="A",
        title="Engineer",
        roles=["contributor", "reviewer"],
        primary_role="reviewer",
        status="active",
    )
    out = _user_admin_out(user)  # type: ignore[arg-type]
    assert out.is_active is True
    assert out.roles == ["contributor", "reviewer"]
    assert out.primary_role == "reviewer"


@pytest.mark.asyncio
async def test_list_users_requires_admin() -> None:
    session = MagicMock()
    svc = AdminService(session)
    actor = Actor(id=uuid.uuid4(), roles=["contributor"], active_role="contributor")
    with pytest.raises(HTTPException) as ei:
        await svc.list_users(actor)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_add_role_rejects_duplicate() -> None:
    uid = uuid.uuid4()
    user = SimpleNamespace(
        id=uid,
        email="p@example.com",
        name="Priya",
        title="",
        roles=["contributor", "lead"],
        primary_role="contributor",
        status="active",
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=user)
    svc = AdminService(session)
    actor = Actor(id=uuid.uuid4(), roles=["admin"], active_role="admin")
    with pytest.raises(HTTPException) as ei:
        await svc.add_role(uid, "lead", actor)
    assert ei.value.status_code == 400
    assert "already holds" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_set_primary_requires_held_role() -> None:
    uid = uuid.uuid4()
    user = SimpleNamespace(
        id=uid,
        email="p@example.com",
        name="Priya",
        title="",
        roles=["contributor"],
        primary_role="contributor",
        status="active",
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=user)
    svc = AdminService(session)
    actor = Actor(id=uuid.uuid4(), roles=["admin"], active_role="admin")
    with pytest.raises(HTTPException) as ei:
        await svc.set_primary_role(
            uid, AdminPrimaryRoleIn(role="admin"), actor
        )
    assert ei.value.status_code == 400
