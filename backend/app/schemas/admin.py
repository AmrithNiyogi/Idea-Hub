"""Admin request/response schemas (Phase 4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TimelinesIn(BaseModel):
    pickup_days: int = Field(..., ge=1, le=30)
    decision_days: int = Field(..., ge=1, le=60)
    stale_prototype_days: int = Field(..., ge=1, le=90)
    needs_info_days: int = Field(..., ge=1, le=60)
    owner_assign_days: int = Field(..., ge=1, le=30)


class ScoringCriterionIn(BaseModel):
    key: str
    label: str
    low: str = ""
    high: str = ""
    weight: int = Field(..., ge=0, le=100)


class ScoringIn(BaseModel):
    criteria: list[ScoringCriterionIn]


class PointOverridesIn(BaseModel):
    overrides: dict[str, int]


class CategoryCreateIn(BaseModel):
    """Create a category and its dedicated review panel.

    ``color_key`` maps to CSS tokens (``var(--cat-{key})``). ``slug`` is
    optional; when omitted the server derives a unique slug from ``label``.
    ``reviewer_id`` becomes the panel's first member and chair.
    """

    label: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Display name shown on Submit and Explore.",
        examples=["Ops Automation"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=160,
        description="Short blurb shown on the Submit category picker.",
        examples=["Internal tooling and runbooks for ops teams."],
    )
    color_key: str = Field(
        ...,
        description=(
            "Colour token key: tech, business, process, innovation, "
            "amber, green, violet, or coral."
        ),
        examples=["amber"],
    )
    reviewer_id: uuid.UUID = Field(
        ...,
        description="First panel reviewer (must hold the Reviewer role).",
    )
    slug: Optional[str] = Field(
        None,
        min_length=2,
        max_length=64,
        description="Optional stable key; auto-derived from label when omitted.",
        examples=["ops-automation"],
    )


class CategoryUpdateIn(BaseModel):
    """Partial category update. Omitted fields are left unchanged."""

    label: Optional[str] = Field(None, min_length=2, max_length=40)
    description: Optional[str] = Field(None, min_length=10, max_length=160)
    enabled: Optional[bool] = Field(
        None,
        description=(
            "Soft-delete / deactivate. Disabled categories leave Submit; "
            "existing ideas keep their label. At least one must stay enabled."
        ),
    )
    color: Optional[str] = Field(
        None,
        description="Raw CSS colour value (e.g. var(--cat-amber)).",
    )
    color_key: Optional[str] = Field(
        None,
        description="Preferred colour token key; overrides ``color`` when set.",
    )


class CategoryOut(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    color: str
    description: str
    enabled: bool

    model_config = {"from_attributes": True}


class PanelCreateIn(BaseModel):
    """Create a review panel for a category that does not yet have one."""

    category_id: uuid.UUID = Field(
        ..., description="Category that will own this panel (1:1)."
    )
    name: Optional[str] = Field(
        None,
        max_length=160,
        description="Panel display name; defaults to “{category} review panel”.",
    )
    member_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="Initial members; each must hold Reviewer (or Admin).",
    )
    chair_id: Optional[uuid.UUID] = Field(
        None,
        description="Chair; must be in member_ids. Defaults to the first member.",
    )


class PanelUpdateIn(BaseModel):
    """Partial panel update (name and/or membership replace)."""

    name: Optional[str] = Field(None, min_length=2, max_length=160)
    member_ids: Optional[list[uuid.UUID]] = Field(
        None,
        min_length=1,
        description="Full replacement member list when provided.",
    )
    chair_id: Optional[uuid.UUID] = Field(
        None,
        description="Chair; must be a member after the update.",
    )


class PanelMemberIn(BaseModel):
    user_id: uuid.UUID


class PanelChairIn(BaseModel):
    user_id: uuid.UUID


class PanelOut(BaseModel):
    id: uuid.UUID
    slug: str
    category_id: uuid.UUID
    name: str
    member_ids: list[uuid.UUID]
    chair_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    section: str
    summary: str
    changes: list[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminConfigOut(BaseModel):
    timelines: dict[str, int]
    scoring: list[dict[str, Any]]
    point_overrides: dict[str, int]
    pool: dict[str, Any]
    categories: list[CategoryOut]
    panels: list[PanelOut]


class ExportOut(BaseModel):
    """Thin export hook — returns counts + generated_at, not a full dump."""

    generated_at: datetime
    counts: dict[str, int]
    note: str = (
        "Full JSON export of collections is a follow-up; this endpoint "
        "returns inventory counts for the reset/export admin tab."
    )


class ResetOut(BaseModel):
    ok: bool
    message: str


class AdminUserOut(BaseModel):
    """Directory row for the Admin → People and roles panel."""

    id: uuid.UUID = Field(..., description="User UUID.")
    email: str = Field(..., description="Login email.", examples=["priya@dotkonnekt.example"])
    name: str = Field(..., description="Display name.")
    title: str = Field("", description="Job title shown under the name.")
    roles: list[str] = Field(
        ...,
        description="Full role set held by this person (multi-role).",
        examples=[["contributor", "lead"]],
    )
    primary_role: str = Field(
        ...,
        description="Default role used at sign-in when no active role is chosen.",
        examples=["contributor"],
    )
    status: str = Field(
        ...,
        description="Account status string (typically ``active`` or ``inactive``).",
        examples=["active"],
    )
    is_active: bool = Field(
        ...,
        description="True when ``status`` is ``active``.",
        examples=[True],
    )

    model_config = {"from_attributes": True}


class AdminRoleIn(BaseModel):
    """Grant one role from ``VALID_ROLES`` to a user."""

    role: str = Field(
        ...,
        description=(
            "Role to add: contributor, reviewer, lead, leadership, or admin."
        ),
        examples=["reviewer"],
    )


class AdminPrimaryRoleIn(BaseModel):
    """Set the user's default (primary) role; must already be in their roles."""

    role: str = Field(
        ...,
        description="Role to make primary; must already be held by the user.",
        examples=["lead"],
    )


class AdminRoleMutationOut(BaseModel):
    """Result of add / remove / set-primary role mutations."""

    user: AdminUserOut
    fell_back: bool = Field(
        False,
        description="True when the actor's active session role was removed (informational).",
    )
    panels_left: int = Field(
        0,
        description="Number of review panels the user was removed from (remove Reviewer).",
    )
    needs_confirm: bool = Field(
        False,
        description="Unused on success; present for schema stability with 409 payloads.",
    )
    panels: list[str] = Field(
        default_factory=list,
        description="Panel names involved when removing Reviewer (409 or success).",
    )
