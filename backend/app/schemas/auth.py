"""Pydantic schemas for authentication flows."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SendLoginOtpRequest(BaseModel):
    """Request a login verification code after password check.

    When the account has authenticator MFA enabled, set ``issue_email_otp``
    to false to skip SMTP and proceed with an authenticator code instead.
    """

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")
    issue_email_otp: bool = Field(
        True,
        description=(
            "When true, store and email a Redis OTP. Set false when the user "
            "will verify with an authenticator app (TOTP) instead."
        ),
        examples=[True],
    )


class SendLoginOtpResponse(BaseModel):
    """Confirmation after password check; email OTP may or may not have been sent."""

    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Masked email for display")
    resend_after_seconds: int = Field(
        ..., description="Seconds before another email code can be requested"
    )
    totp_enabled: bool = Field(
        False,
        description="True when the account may use an authenticator app at login",
        examples=[False],
    )
    email_otp_sent: bool = Field(
        True,
        description="True when a Redis email OTP was issued and mailed",
        examples=[True],
    )


class LoginRequest(BaseModel):
    """Login with email, password, and a 6-digit email OTP or TOTP code."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")
    otp: str = Field(..., pattern=r"^\d{6}$", description="6-digit verification code")
    otp_method: Literal["email", "totp"] | None = Field(
        None,
        description=(
            "Verification channel. ``email`` = Redis email OTP; ``totp`` = "
            "authenticator app. When omitted: use TOTP if the account has MFA "
            "enabled, otherwise email OTP."
        ),
        examples=["email"],
    )


class UserPublic(BaseModel):
    """Sanitized user returned to clients (no password)."""

    id: UUID
    email: str
    name: str
    title: str = ""
    team_id: UUID | None = None
    roles: list[str] = Field(default_factory=list)
    primary_role: str = "contributor"
    active_role: str = "contributor"
    status: str = "active"
    avatar: int = Field(1, description="Color preset index 1–8 for initials avatar")
    avatar_url: str | None = Field(
        None,
        description="Optional profile image URL (https or /uploads/avatars/…)",
        examples=["/uploads/avatars/u_abc.jpg"],
    )
    slug: str = ""
    totp_enabled: bool = Field(
        False,
        description="True when authenticator-app MFA is enrolled and confirmed",
        examples=[False],
    )
    has_password: bool = Field(
        True,
        description=(
            "True when password login is available (seed or password set). "
            "False for Microsoft SSO-only accounts (random unusable hash)."
        ),
        examples=[True],
    )

    model_config = {"from_attributes": True}


class TotpSetupResponse(BaseModel):
    """Pending TOTP enrollment material (secret + QR)."""

    secret: str = Field(
        ...,
        description="Base32 shared secret for manual entry in authenticator apps",
        examples=["JBSWY3DPEHPK3PXP"],
    )
    otpauth_uri: str = Field(
        ...,
        description="otpauth:// URI for QR scanning",
        examples=["otpauth://totp/Idea%20Hub:user@example.com?secret=…&issuer=Idea%20Hub"],
    )
    qr_png_base64: str = Field(
        ...,
        description="PNG QR of the otpauth URI as raw base64 (no data: prefix)",
    )
    expires_in_seconds: int = Field(
        ...,
        description="Seconds until the pending setup secret expires in Redis",
        examples=[600],
    )


class TotpConfirmRequest(BaseModel):
    """Confirm TOTP enrollment with a code from the authenticator app."""

    code: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="Current 6-digit TOTP code",
        examples=["123456"],
    )


class TotpDisableRequest(BaseModel):
    """Disable authenticator MFA (requires password + current code)."""

    password: str = Field(..., min_length=1, description="Current account password")
    code: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="Current 6-digit TOTP code",
        examples=["123456"],
    )


class TotpStatusResponse(BaseModel):
    """Public MFA status for the signed-in user (never includes the secret)."""

    totp_enabled: bool = Field(..., description="MFA is active for login")
    totp_pending_setup: bool = Field(
        ...,
        description="A setup secret is waiting in Redis for confirm",
    )
    has_password: bool = Field(
        ...,
        description=(
            "True when the account has a usable password path. "
            "SSO-only accounts are false."
        ),
        examples=[True],
    )
    mfa_available: bool = Field(
        ...,
        description=(
            "True when authenticator MFA enroll/disable is allowed "
            "(requires a usable password). Same as has_password."
        ),
        examples=[True],
    )


class UpdateMeRequest(BaseModel):
    """Partial update for the signed-in user's profile fields."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=160,
        description="Display name shown across the product",
        examples=["Priya Sharma"],
    )
    title: str | None = Field(
        None,
        max_length=160,
        description="Job title / role label",
        examples=["Senior Engineer"],
    )
    avatar: int | None = Field(
        None,
        ge=1,
        le=8,
        description="Avatar color preset (1–8)",
        examples=[3],
    )
    avatar_url: str | None = Field(
        None,
        max_length=512,
        description=(
            "Profile image URL. Empty string clears. "
            "Accepts https://… or a previously uploaded /uploads/avatars/… path."
        ),
    )


class ChangePasswordRequest(BaseModel):
    """Change password for the signed-in user (requires current password)."""

    current_password: str = Field(
        ..., min_length=1, description="Existing password for verification"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 characters)",
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Must match new_password",
    )


class LoginResponse(BaseModel):
    """OTP/password login result.

    When ``requires_role_selection`` is true, cookies are NOT set yet. The
    client must call ``POST /auth/complete-login`` with ``login_ticket`` and
    the chosen role. When false, ``user`` is present and JWT cookies are set.
    """

    message: str
    user: UserPublic | None = None
    requires_role_selection: bool = Field(
        False,
        description="True when the account holds multiple roles and must pick one",
    )
    # Opaque one-time ticket for complete-login; only set when the account has multiple roles.
    login_ticket: str | None = None
    roles: list[str] = Field(
        default_factory=list,
        description="Roles available for selection when requires_role_selection",
    )
    primary_role: str | None = Field(
        None,
        description="Account default role (hint for the picker UI)",
    )
    name: str | None = Field(
        None,
        description="Display name for the role-selection step",
    )


class CompleteLoginRequest(BaseModel):
    """Finish multi-role login by redeeming a ticket with a chosen role."""

    login_ticket: str = Field(
        ...,
        min_length=8,
        description="Ticket returned by POST /auth/login when role selection is required",
    )
    role: str = Field(
        ...,
        min_length=1,
        description="Role to activate for this session (must be one the user holds)",
        examples=["reviewer"],
    )


class LogoutResponse(BaseModel):
    """Logout confirmation."""

    message: str


class SwitchRoleRequest(BaseModel):
    """Switch the session's active role (must be one the user holds)."""

    role: str = Field(..., min_length=1, description="Role identifier to activate")


class SwitchRoleResponse(BaseModel):
    """Active role after a successful switch."""

    role: str
    user: UserPublic


class TokenPayload(BaseModel):
    """Decoded JWT access-token claims used internally."""

    sub: str
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    active_role: str | None = None
    type: str | None = None


class MessageResponse(BaseModel):
    """Generic message envelope."""

    message: str
    data: dict[str, Any] | None = None


class AuthProvidersResponse(BaseModel):
    """Public auth provider availability for the login UI.

    Used by the frontend to show/hide Microsoft SSO without exposing secrets.
    """

    password_otp: bool = Field(
        True,
        description="Email + password + OTP login is always available when the API is up.",
        examples=[True],
    )
    microsoft: bool = Field(
        ...,
        description=(
            "True when MICROSOFT_ENABLED is set and Azure app credentials "
            "(client id/secret, tenant, redirect URI) are configured."
        ),
        examples=[False],
    )
