"""Microsoft Entra ID (Azure AD) OIDC — authorize, callback, id_token validation.

Architecture:
  - Authorization Code + PKCE-optional confidential client (client secret).
  - State + nonce stored in Redis; OTP is skipped for SSO (same JWT cookies).
  - Does not replace password+OTP; runs alongside it.

Must never:
  - Log client secrets or raw id_tokens.
  - Issue cookies without a validated email claim.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import get_redis
from app.models.user import User
from app.services import auth_service

logger = logging.getLogger("idea_hub.microsoft_oidc")


def frontend_success_url(redirect_path: str) -> str:
    """Build the post-SSO frontend URL from env + optional relative path.

    Uses ``MICROSOFT_FRONTEND_SUCCESS_URL`` origin when set; falls back to
    ``FRONTEND_ORIGIN``. Relative ``redirect_path`` values (e.g. ``/explore``)
    are appended to that origin. Bare ``/`` uses the success URL as configured
    (including any trailing slash).

    Args:
        redirect_path: Same-app relative path from OAuth state (must start with ``/``).

    Returns:
        Absolute frontend URL for the 302 Location header.
    """
    success = (settings.MICROSOFT_FRONTEND_SUCCESS_URL or "").strip()
    fallback = settings.FRONTEND_ORIGIN.rstrip("/")
    if success:
        parsed = urlparse(success)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else fallback
    else:
        origin = fallback
    path = redirect_path if redirect_path.startswith("/") else f"/{redirect_path}"
    if path in ("/", ""):
        return success.rstrip("/") + "/" if success else f"{origin}/"
    return f"{origin}{path}"

_OIDC_SCOPES = "openid profile email User.Read"
_STATE_KEY_PREFIX = "ms_oauth_state:"
_DISCOVERY_CACHE: dict[str, Any] = {"tenant": None, "doc": None, "fetched_at": 0.0}
_DISCOVERY_TTL_SECONDS = 3600
_JWKS_CACHE: dict[str, Any] = {"uri": None, "keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def microsoft_sso_ready() -> bool:
    """Return True when Microsoft SSO is enabled and fully configured.

    Returns:
        bool: True only if enabled flag is set and all required Azure
            credentials / redirect URI are non-empty.
    """
    return bool(
        settings.MICROSOFT_ENABLED
        and settings.MICROSOFT_CLIENT_ID.strip()
        and settings.MICROSOFT_CLIENT_SECRET.strip()
        and settings.MICROSOFT_TENANT_ID.strip()
        and settings.MICROSOFT_REDIRECT_URI.strip()
    )


def require_microsoft_configured() -> None:
    """Raise 503 when Microsoft SSO is disabled or missing credentials.

    Raises:
        HTTPException: 503 with a clear configuration message.
    """
    if not microsoft_sso_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft sign-in is not configured",
        )


def _authority_base() -> str:
    tenant = settings.MICROSOFT_TENANT_ID.strip() or "common"
    return f"https://login.microsoftonline.com/{tenant}/v2.0"


def _state_key(state: str) -> str:
    return f"{_STATE_KEY_PREFIX}{state}"


def _sanitize_redirect(redirect: str | None) -> str:
    """Allow only same-app relative paths (open-redirect safe)."""
    if not redirect:
        return "/"
    candidate = redirect.strip()
    if not candidate.startswith("/") or candidate.startswith("//") or "\\" in candidate:
        return "/"
    return candidate


async def _fetch_openid_configuration() -> dict[str, Any]:
    """Load and cache the Entra ID OpenID discovery document.

    Raises:
        HTTPException: 503 if discovery fails.
    """
    tenant = settings.MICROSOFT_TENANT_ID.strip() or "common"
    now = time.monotonic()
    if (
        _DISCOVERY_CACHE["doc"] is not None
        and _DISCOVERY_CACHE["tenant"] == tenant
        and now - float(_DISCOVERY_CACHE["fetched_at"]) < _DISCOVERY_TTL_SECONDS
    ):
        return _DISCOVERY_CACHE["doc"]  # type: ignore[return-value]

    url = f"{_authority_base()}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            doc = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Microsoft OIDC discovery failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft identity discovery is unavailable",
        ) from exc

    _DISCOVERY_CACHE["tenant"] = tenant
    _DISCOVERY_CACHE["doc"] = doc
    _DISCOVERY_CACHE["fetched_at"] = now
    return doc


async def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    """Load and cache JWKS for id_token signature verification."""
    now = time.monotonic()
    if (
        _JWKS_CACHE["keys"] is not None
        and _JWKS_CACHE["uri"] == jwks_uri
        and now - float(_JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS
    ):
        return _JWKS_CACHE["keys"]  # type: ignore[return-value]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(jwks_uri)
            resp.raise_for_status()
            keys = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Microsoft JWKS fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft signing keys are unavailable",
        ) from exc

    _JWKS_CACHE["uri"] = jwks_uri
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def _store_oauth_state(*, state: str, nonce: str, redirect: str) -> None:
    """Persist OAuth state+nonce in Redis for callback correlation.

    Raises:
        HTTPException: 503 if Redis is unavailable.
    """
    payload = json.dumps(
        {"nonce": nonce, "redirect": redirect, "created_at": int(time.time())}
    )
    try:
        get_redis().setex(
            _state_key(state),
            settings.MICROSOFT_SSO_STATE_TTL_SECONDS,
            payload,
        )
    except RedisError as exc:
        logger.error("Redis error storing Microsoft OAuth state: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is temporarily unavailable",
        ) from exc


def _consume_oauth_state(state: str) -> dict[str, Any]:
    """Load and delete OAuth state; fail closed on missing/expired state.

    Raises:
        HTTPException: 400 invalid/expired state, 503 Redis down.
    """
    try:
        client = get_redis()
        key = _state_key(state)
        raw = client.get(key)
        if raw:
            client.delete(key)
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired Microsoft sign-in state",
            )
        return json.loads(raw)
    except HTTPException:
        raise
    except (RedisError, json.JSONDecodeError, TypeError) as exc:
        logger.error("Redis error consuming Microsoft OAuth state: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is temporarily unavailable",
        ) from exc


async def build_authorize_redirect_url(*, redirect: str | None = None) -> str:
    """Create Microsoft authorize URL and stash state/nonce in Redis.

    Args:
        redirect: Optional frontend path to land on after SSO (relative only).

    Returns:
        str: Absolute Microsoft authorize URL for a 302 redirect.

    Raises:
        HTTPException: 503 if not configured or discovery/Redis fails.
    """
    require_microsoft_configured()
    client_id = settings.MICROSOFT_CLIENT_ID.strip()
    # Prefix-only: catches Secret-ID / typo misconfig without leaking the secret.
    logger.info(
        "microsoft_login: client_id_prefix=%s tenant=%s",
        client_id[:8],
        settings.MICROSOFT_TENANT_ID.strip()[:8],
    )
    doc = await _fetch_openid_configuration()
    authorization_endpoint = doc.get("authorization_endpoint")
    if not authorization_endpoint:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft authorize endpoint missing from discovery",
        )

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    safe_redirect = _sanitize_redirect(redirect)
    _store_oauth_state(state=state, nonce=nonce, redirect=safe_redirect)

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI.strip(),
        "response_mode": "query",
        "scope": _OIDC_SCOPES,
        "state": state,
        "nonce": nonce,
    }
    return f"{authorization_endpoint}?{urlencode(params)}"


def _jwk_for_token(id_token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Microsoft id_token header",
        ) from exc
    kid = header.get("kid")
    for key in jwks.get("keys") or []:
        if key.get("kid") == kid:
            return key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Microsoft signing key not found for id_token",
    )


def _issuer_allowed(token_iss: str, discovery_issuer: str) -> bool:
    """Accept single-tenant exact issuer or multi-tenant Entra v2 issuer shapes.

    ``common`` / ``organizations`` / ``consumers`` authorities embed the user's
    real tenant GUID in ``iss``, which will not equal the discovery document's
    ``{tenantid}`` template. Comparing only to discovery ``issuer`` would reject
    every successful multi-tenant login.

    Args:
        token_iss: ``iss`` claim from the validated id_token.
        discovery_issuer: ``issuer`` field from OpenID discovery (may contain
            the literal ``{tenantid}`` placeholder for multi-tenant authorities).

    Returns:
        bool: True when the token issuer is trusted for the configured tenant.
    """
    tenant = (settings.MICROSOFT_TENANT_ID or "common").strip().lower()
    if token_iss == discovery_issuer:
        return True
    # Discovery for common/organizations often returns a templated issuer.
    if "{tenantid}" in discovery_issuer.lower() and re.match(
        r"^https://login\.microsoftonline\.com/[0-9a-fA-F-]+/v2\.0$",
        token_iss,
    ):
        return True
    if tenant in {"common", "organizations", "consumers"}:
        return bool(
            re.match(
                r"^https://login\.microsoftonline\.com/[0-9a-fA-F-]+/v2\.0$",
                token_iss,
            )
        )
    expected = f"https://login.microsoftonline.com/{tenant}/v2.0"
    return token_iss == expected


def _validate_id_token(
    id_token: str,
    *,
    jwks: dict[str, Any],
    issuer: str,
    nonce: str,
) -> dict[str, Any]:
    """Verify signature, audience, issuer, exp, and nonce on the id_token.

    Raises:
        HTTPException: 401 on any validation failure.
    """
    key = _jwk_for_token(id_token, jwks)
    try:
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=settings.MICROSOFT_CLIENT_ID.strip(),
            options={"verify_iss": False, "verify_at_hash": False},
        )
    except JWTError as exc:
        logger.warning("Microsoft id_token validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Microsoft id_token",
        ) from exc

    token_iss = str(claims.get("iss") or "")
    if not _issuer_allowed(token_iss, issuer):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft id_token issuer is not trusted",
        )

    token_nonce = claims.get("nonce")
    if not token_nonce or not secrets.compare_digest(str(token_nonce), nonce):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft id_token nonce mismatch",
        )
    return claims


def _email_from_claims(claims: dict[str, Any]) -> str:
    """Extract a usable email from OIDC claims (email or preferred_username)."""
    for key in ("email", "preferred_username", "upn"):
        value = claims.get(key)
        if isinstance(value, str) and "@" in value:
            return value.strip().lower()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Microsoft account did not return an email address",
    )


def _display_name_from_claims(claims: dict[str, Any], email: str) -> str:
    name = claims.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()[:160]
    local = email.split("@", 1)[0]
    cleaned = re.sub(r"[._+-]+", " ", local).strip()
    return (cleaned.title() if cleaned else "Microsoft User")[:160]


async def _exchange_code_for_tokens(
    code: str, *, token_endpoint: str
) -> dict[str, Any]:
    """Exchange authorization code for tokens at the Entra token endpoint.

    Raises:
        HTTPException: 401 on token exchange failure.
    """
    data = {
        "client_id": settings.MICROSOFT_CLIENT_ID.strip(),
        "client_secret": settings.MICROSOFT_CLIENT_SECRET.strip(),
        "code": code,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI.strip(),
        "grant_type": "authorization_code",
        "scope": _OIDC_SCOPES,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        logger.error("Microsoft token exchange network error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft token endpoint is unavailable",
        ) from exc

    if resp.status_code >= 400:
        logger.warning(
            "Microsoft token exchange failed status=%s body=%s",
            resp.status_code,
            resp.text[:300],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft authorization code exchange failed",
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Microsoft token response",
        ) from exc


async def complete_microsoft_login(
    session: AsyncSession,
    *,
    code: str | None,
    state: str | None,
    error: str | None = None,
    error_description: str | None = None,
) -> tuple[User, str]:
    """Finish the OIDC callback: validate tokens, upsert user, return redirect.

    Args:
        session: Async DB session (caller commits via upsert).
        code: Authorization code from Microsoft.
        state: Opaque state returned by Microsoft (must match Redis).
        error: OAuth error code if Microsoft rejected consent/login.
        error_description: Human-readable OAuth error detail.

    Returns:
        tuple[User, str]: Persisted user and safe frontend redirect path.

    Raises:
        HTTPException: 400/401/503 on configuration, OAuth, or validation errors.
    """
    require_microsoft_configured()

    if error:
        detail = error_description or error
        logger.warning("Microsoft OAuth error: %s", detail)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Microsoft sign-in failed: {detail}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Microsoft authorization code or state",
        )

    stored = _consume_oauth_state(state)
    nonce = str(stored.get("nonce") or "")
    redirect = _sanitize_redirect(
        stored.get("redirect") if isinstance(stored.get("redirect"), str) else "/"
    )
    if not nonce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Microsoft sign-in state payload",
        )

    doc = await _fetch_openid_configuration()
    token_endpoint = doc.get("token_endpoint")
    jwks_uri = doc.get("jwks_uri")
    issuer = doc.get("issuer")
    if not token_endpoint or not jwks_uri or not issuer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft OIDC discovery document is incomplete",
        )

    token_payload = await _exchange_code_for_tokens(code, token_endpoint=token_endpoint)
    id_token = token_payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft response missing id_token",
        )

    jwks = await _fetch_jwks(jwks_uri)
    claims = _validate_id_token(
        id_token, jwks=jwks, issuer=str(issuer), nonce=nonce
    )
    email = _email_from_claims(claims)
    name = _display_name_from_claims(claims, email)

    user = await auth_service.upsert_microsoft_user(
        session, email=email, name=name
    )
    logger.info("Microsoft SSO login ok for %s", email)
    return user, redirect
