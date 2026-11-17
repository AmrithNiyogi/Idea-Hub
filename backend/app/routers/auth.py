"""Authentication routes — OTP/TOTP login, Microsoft OIDC SSO, MFA, refresh, logout."""

from __future__ import annotations

import logging
import uuid
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.config.settings import settings
from app.dependencies.auth import DbSession, RequireUser
from app.models.user import User
from app.schemas.auth import (
    AuthProvidersResponse,
    CompleteLoginRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MessageResponse,
    SendLoginOtpRequest,
    SendLoginOtpResponse,
    SwitchRoleRequest,
    SwitchRoleResponse,
    TotpConfirmRequest,
    TotpDisableRequest,
    TotpSetupResponse,
    TotpStatusResponse,
)
from app.services import (
    auth_service,
    login_otp_service,
    login_ticket_service,
    microsoft_oidc_service,
    totp_service,
)
from app.services.email_adapter import send_login_otp_email
from app.utils.cookies import clear_auth_cookies, set_auth_cookies

logger = logging.getLogger("idea_hub.routers.auth")

router = APIRouter(prefix="/auth", tags=["authentication"])


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}{'*' * max(len(local) - 2, 1)}@{domain}"


def _frontend_login_error_url(message: str) -> str:
    """Build a frontend /login URL carrying a short SSO error for the UI."""
    origin = settings.FRONTEND_ORIGIN.rstrip("/")
    return f"{origin}/login?error={quote(message[:200])}"


@router.get(
    "/providers",
    response_model=AuthProvidersResponse,
    summary="List available authentication providers",
    description=(
        "Public probe used by the login page. Reports whether password+OTP "
        "and Microsoft Entra ID SSO are available. Never exposes secrets."
    ),
    responses={200: {"description": "Provider flags"}},
)
async def auth_providers() -> AuthProvidersResponse:
    """Return which login methods the API can currently offer."""
    return AuthProvidersResponse(
        password_otp=True,
        microsoft=microsoft_oidc_service.microsoft_sso_ready(),
    )


@router.get(
    "/microsoft/login",
    summary="Start Microsoft Entra ID sign-in",
    description=(
        "302 redirect to Microsoft authorize. Stores state+nonce in Redis. "
        "Optional ``redirect`` query is a same-app relative path returned to "
        "after successful SSO. Returns 503 when Azure credentials are missing."
    ),
    responses={
        302: {"description": "Redirect to Microsoft authorize URL"},
        503: {"description": "Microsoft sign-in is not configured"},
    },
)
async def microsoft_login(
    redirect: str | None = Query(
        default=None,
        description="Frontend path after SSO (must be relative, e.g. / or /explore)",
        examples=["/"],
    ),
) -> RedirectResponse:
    """Begin Microsoft OIDC authorization-code flow (skips OTP)."""
    url = await microsoft_oidc_service.build_authorize_redirect_url(
        redirect=redirect
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/microsoft/callback",
    summary="Microsoft Entra ID OAuth callback",
    description=(
        "Exchanges the authorization code, validates the id_token (signature, "
        "audience, issuer, nonce), upserts the user by email, sets the same "
        "httpOnly JWT cookies as OTP login, and redirects to the frontend."
    ),
    responses={
        302: {"description": "Redirect to frontend with session cookies set"},
        503: {"description": "Microsoft sign-in is not configured"},
    },
)
async def microsoft_callback(
    session: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    """Complete Microsoft SSO and issue JWT cookies (no OTP step)."""
    try:
        user, redirect_path = await microsoft_oidc_service.complete_microsoft_login(
            session,
            code=code,
            state=state,
            error=error,
            error_description=error_description,
        )
    except HTTPException as exc:
        detail = (
            exc.detail if isinstance(exc.detail, str) else "Microsoft sign-in failed"
        )
        return RedirectResponse(
            url=_frontend_login_error_url(detail),
            status_code=status.HTTP_302_FOUND,
        )

    tokens = auth_service.issue_login_tokens(user)
    dest = microsoft_oidc_service.frontend_success_url(redirect_path)
    response = RedirectResponse(url=dest, status_code=status.HTTP_302_FOUND)
    set_auth_cookies(
        response,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )
    logger.info("Microsoft SSO cookies set for %s → %s", user.email, redirect_path)
    return response


@router.post(
    "/send-login-otp",
    response_model=SendLoginOtpResponse,
    summary="Validate password and optionally email a login OTP",
    description=(
        "Always verifies email+password. When ``issue_email_otp`` is true "
        "(default), stores a Redis OTP and emails it via SMTP. When the "
        "account has authenticator MFA, clients may set ``issue_email_otp`` "
        "false and verify with TOTP on ``POST /login`` instead. Response "
        "always reports ``totp_enabled`` so the UI can show method tabs."
    ),
)
async def send_login_otp(
    body: SendLoginOtpRequest,
    session: DbSession,
) -> SendLoginOtpResponse:
    """Validate credentials; optionally issue and email an OTP.

    On SMTP failure the stored OTP is discarded (Kompass admin fail-closed).
    """
    user = await auth_service.authenticate_credentials(
        session, body.email, body.password
    )
    totp_on = bool(user.totp_enabled)
    want_email = body.issue_email_otp
    if not want_email and not totp_on:
        # No authenticator enrolled — email OTP is required.
        want_email = True

    email_sent = False
    if want_email:
        otp = login_otp_service.issue_otp(str(user.id))
        if not send_login_otp_email(email=user.email, otp=otp, user_name=user.name):
            login_otp_service.discard_otp(str(user.id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not send verification code",
            )
        email_sent = True
        message = "A verification code has been sent"
    else:
        message = "Password verified. Enter your authenticator code."

    return SendLoginOtpResponse(
        message=message,
        email=_mask_email(user.email),
        resend_after_seconds=settings.LOGIN_OTP_RESEND_COOLDOWN_SECONDS,
        totp_enabled=totp_on,
        email_otp_sent=email_sent,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with password + email OTP or authenticator code",
    description=(
        "After password check, verifies either the Redis email OTP "
        "(``otp_method=email``) or the enrolled TOTP secret "
        "(``otp_method=totp``). When ``otp_method`` is omitted, TOTP is used "
        "if MFA is enabled, otherwise email OTP. "
        "Single-role accounts get JWT cookies immediately. Multi-role "
        "accounts receive a ``login_ticket`` and must call "
        "``POST /auth/complete-login`` before cookies are set."
    ),
)
async def login(
    body: LoginRequest,
    response: Response,
    session: DbSession,
) -> LoginResponse:
    """Authenticate with password and second factor; set cookies or defer for role pick."""
    user = await auth_service.authenticate_credentials(
        session, body.email, body.password
    )
    method = body.otp_method
    if method is None:
        method = "totp" if user.totp_enabled else "email"
    if method == "totp":
        totp_service.verify_user_totp(user, body.otp)
    else:
        login_otp_service.verify_otp(str(user.id), body.otp)

    roles = auth_service.resolve_user_roles(user)
    if len(roles) > 1:
        ticket = login_ticket_service.issue_ticket(str(user.id))
        logger.info(
            "Login OTP ok for %s method=%s; awaiting role selection (%d roles)",
            user.email,
            method,
            len(roles),
        )
        return LoginResponse(
            message="Choose a role to continue",
            requires_role_selection=True,
            login_ticket=ticket,
            roles=roles,
            primary_role=user.primary_role,
            name=user.name,
        )

    active = roles[0] if roles else auth_service.default_active_role(user)
    tokens = auth_service.issue_login_tokens(user, active_role=active)
    set_auth_cookies(
        response,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )
    logger.info("Login successful for %s method=%s role=%s", user.email, method, active)
    return LoginResponse(
        message="Login successful",
        user=tokens["user"],
        requires_role_selection=False,
        roles=roles,
        primary_role=user.primary_role,
        name=user.name,
    )


@router.post(
    "/complete-login",
    response_model=LoginResponse,
    summary="Complete multi-role login after OTP",
    description=(
        "Redeems the one-time ``login_ticket`` from ``POST /auth/login`` with "
        "the chosen role and sets access + refresh JWT cookies. Single-role "
        "logins never need this step."
    ),
    responses={
        401: {"description": "Ticket expired or account disabled"},
        403: {"description": "Role not held by the user"},
    },
)
async def complete_login(
    body: CompleteLoginRequest,
    response: Response,
    session: DbSession,
) -> LoginResponse:
    """Issue session cookies after the user picks an active role."""
    user_id = login_ticket_service.consume_ticket(body.login_ticket)
    tokens = await auth_service.complete_login_with_role(
        session, uuid.UUID(user_id), body.role
    )
    set_auth_cookies(
        response,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )
    user = tokens["user"]
    logger.info(
        "Complete-login for %s role=%s",
        user.email,
        user.active_role,
    )
    return LoginResponse(
        message="Login successful",
        user=user,
        requires_role_selection=False,
        roles=list(user.roles or []),
        primary_role=user.primary_role,
        name=user.name,
    )


@router.get(
    "/mfa/totp/status",
    response_model=TotpStatusResponse,
    summary="Authenticator MFA status for the signed-in user",
)
async def totp_status(
    current: RequireUser,
    session: DbSession,
) -> TotpStatusResponse:
    """Return whether TOTP is enabled / pending (never the secret)."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = totp_service.mfa_status(user)
    return TotpStatusResponse(**data)


@router.post(
    "/mfa/totp/setup",
    response_model=TotpSetupResponse,
    summary="Begin authenticator MFA enrollment",
    description=(
        "Generates a TOTP secret, stores it temporarily in Redis, and returns "
        "the secret, otpauth URI, and a PNG QR (base64) for Google / Microsoft "
        "Authenticator. Call confirm with a valid code to enable MFA."
    ),
    responses={
        400: {"description": "MFA already enabled"},
        401: {"description": "Not authenticated"},
        503: {"description": "Redis unavailable"},
    },
)
async def totp_setup(
    current: RequireUser,
    session: DbSession,
) -> TotpSetupResponse:
    """Start TOTP enrollment for the signed-in user."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await totp_service.begin_setup(session, user)
    return TotpSetupResponse(**data)


@router.post(
    "/mfa/totp/confirm",
    response_model=MessageResponse,
    summary="Confirm authenticator MFA enrollment",
    description=(
        "Verifies a 6-digit code against the pending Redis secret, encrypts "
        "the secret onto the user row, and sets totp_enabled=true."
    ),
    responses={
        400: {"description": "Setup expired or already enabled"},
        401: {"description": "Invalid code or not authenticated"},
    },
)
async def totp_confirm(
    body: TotpConfirmRequest,
    current: RequireUser,
    session: DbSession,
) -> MessageResponse:
    """Enable MFA after a successful authenticator challenge."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    await totp_service.confirm_setup(session, user, body.code)
    return MessageResponse(message="Authenticator MFA enabled")


@router.post(
    "/mfa/totp/disable",
    response_model=MessageResponse,
    summary="Disable authenticator MFA",
    description=(
        "Requires the current password and a valid authenticator code. "
        "Clears the encrypted secret and totp_enabled. Locked-out users "
        "must ask an admin to clear MFA (see docs/MFA_TOTP.md)."
    ),
    responses={
        400: {"description": "MFA not enabled"},
        401: {"description": "Bad password/code or not authenticated"},
    },
)
async def totp_disable(
    body: TotpDisableRequest,
    current: RequireUser,
    session: DbSession,
) -> MessageResponse:
    """Disable authenticator MFA for the signed-in user."""
    user = current.orm or await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    await totp_service.disable_totp(
        session, user, password=body.password, code=body.code
    )
    return MessageResponse(message="Authenticator MFA disabled")


@router.post("/refresh", summary="Refresh access token")
async def refresh(
    request: Request,
    response: Response,
    session: DbSession,
) -> dict:
    """Mint a new access token from the refresh cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )
    access, user = await auth_service.refresh_access_token(session, refresh_token)
    set_auth_cookies(response, access_token=access)
    return {"message": "Token refreshed", "user": user}


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout (clear cookies)",
)
async def logout(response: Response) -> LogoutResponse:
    """Clear authentication cookies."""
    clear_auth_cookies(response)
    return LogoutResponse(message="Logged out")


@router.post(
    "/switch-role",
    response_model=SwitchRoleResponse,
    summary="Switch active role for the session",
)
async def switch_role(
    body: SwitchRoleRequest,
    response: Response,
    session: DbSession,
    current: RequireUser,
) -> SwitchRoleResponse:
    """Re-issue access token with a new active_role the user holds."""
    user = current.orm or await auth_service.get_user_by_id(session, current.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await auth_service.switch_role(
        session, user, body.role, current.active_role
    )
    set_auth_cookies(response, access_token=result["access_token"])
    return SwitchRoleResponse(role=result["role"], user=result["user"])
