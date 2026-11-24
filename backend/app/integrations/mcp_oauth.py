"""OAuth helpers for MCP servers that require sign-in (MCP authorization spec).

Flow: discover protected-resource metadata (RFC 9728) -> authorization-server
metadata (RFC 8414 / OIDC) -> register a client (RFC 7591, when the server offers
registration) -> authorization code + PKCE S256 with the RFC 8707 ``resource``
parameter -> token exchange and refresh.

Only the protocol steps live here. Persistence and the HTTP callback are in
``app.services.mcp_oauth_service``.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode, urlparse, urlunparse

import httpx

_TIMEOUT = 20.0
CLIENT_NAME = "IdeaKonnekt"


def canonical_resource(endpoint_url: str) -> str:
    """Canonical MCP server URI: lowercase scheme/host, no fragment, no trailing slash."""
    u = urlparse(endpoint_url.strip())
    path = u.path.rstrip("/")
    return urlunparse((u.scheme.lower(), u.netloc.lower(), path, "", "", ""))


def _well_known_resource_candidates(endpoint_url: str) -> list[str]:
    u = urlparse(endpoint_url)
    origin = f"{u.scheme}://{u.netloc}"
    path = u.path.rstrip("/")
    out = []
    if path:
        out.append(f"{origin}/.well-known/oauth-protected-resource{path}")
    out.append(f"{origin}/.well-known/oauth-protected-resource")
    return out


def _as_metadata_candidates(issuer: str) -> list[str]:
    u = urlparse(issuer)
    origin = f"{u.scheme}://{u.netloc}"
    path = u.path.rstrip("/")
    if not path:
        return [
            f"{origin}/.well-known/oauth-authorization-server",
            f"{origin}/.well-known/openid-configuration",
        ]
    return [
        f"{origin}/.well-known/oauth-authorization-server{path}",
        f"{origin}/.well-known/openid-configuration{path}",
        f"{origin}{path}/.well-known/openid-configuration",
    ]


async def _get_json(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    try:
        res = await client.get(url, headers={"Accept": "application/json"})
    except httpx.HTTPError:
        return None
    if res.status_code != 200:
        return None
    try:
        data = res.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


async def discover(endpoint_url: str) -> dict[str, Any]:
    """Return ``{"resource": ..., "as_metadata": ..., "scope": str}`` or raise ValueError."""
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resource_meta: dict[str, Any] | None = None
        challenge_scope = ""
        # 1) Server tells us where its metadata is via WWW-Authenticate on a 401.
        try:
            probe = await client.post(
                endpoint_url,
                json={"jsonrpc": "2.0", "id": 0, "method": "ping"},
                headers={"Accept": "application/json, text/event-stream"},
            )
        except httpx.HTTPError as exc:
            raise ValueError(f"Could not reach MCP server: {exc}") from exc
        if probe.status_code == 401:
            challenge = probe.headers.get("www-authenticate", "")
            meta_url = _challenge_param(challenge, "resource_metadata")
            challenge_scope = _challenge_param(challenge, "scope")
            if meta_url:
                resource_meta = await _get_json(client, meta_url)
        # 2) Otherwise probe the well-known locations.
        if resource_meta is None:
            for url in _well_known_resource_candidates(endpoint_url):
                resource_meta = await _get_json(client, url)
                if resource_meta and resource_meta.get("authorization_servers"):
                    break
        if not resource_meta or not resource_meta.get("authorization_servers"):
            raise ValueError(
                "This MCP server does not advertise sign-in. Use a token/header connection instead."
            )

        issuer = str(resource_meta["authorization_servers"][0])
        as_meta: dict[str, Any] | None = None
        for url in _as_metadata_candidates(issuer):
            as_meta = await _get_json(client, url)
            if as_meta and as_meta.get("authorization_endpoint") and as_meta.get("token_endpoint"):
                break
            as_meta = None
        if as_meta is None:
            raise ValueError("Could not read the sign-in server's metadata.")

        methods = as_meta.get("code_challenge_methods_supported") or []
        if "S256" not in methods:
            raise ValueError("The sign-in server does not support PKCE (S256).")

        scope = challenge_scope or " ".join(resource_meta.get("scopes_supported") or [])
        return {
            "resource": canonical_resource(endpoint_url),
            "as_metadata": as_meta,
            "scope": scope,
        }


def _challenge_param(header: str, name: str) -> str:
    """Pull ``name="value"`` out of a WWW-Authenticate header (simple, quoted values)."""
    marker = f'{name}="'
    idx = header.find(marker)
    if idx < 0:
        return ""
    start = idx + len(marker)
    end = header.find('"', start)
    return header[start:end] if end > start else ""


async def register_client(as_meta: dict[str, Any], redirect_uri: str) -> str:
    """Dynamic client registration (RFC 7591). Raises ValueError if the server has none."""
    endpoint = as_meta.get("registration_endpoint")
    if not endpoint:
        raise ValueError(
            "This sign-in server needs a pre-registered client, which is not supported yet."
        )
    body = {
        "client_name": CLIENT_NAME,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            res = await client.post(str(endpoint), json=body)
        except httpx.HTTPError as exc:
            raise ValueError(f"Client registration failed: {exc}") from exc
    if res.status_code not in (200, 201):
        raise ValueError(f"Client registration was refused ({res.status_code}).")
    client_id = str(res.json().get("client_id") or "")
    if not client_id:
        raise ValueError("Client registration returned no client_id.")
    return client_id


def make_pkce() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` for S256."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def authorize_url(
    *,
    as_meta: dict[str, Any],
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
    resource: str,
    scope: str,
) -> str:
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "resource": resource,
    }
    if scope:
        params["scope"] = scope
    return f"{as_meta['authorization_endpoint']}?{urlencode(params, quote_via=quote)}"


def _token_result(data: dict[str, Any]) -> dict[str, Any]:
    access = str(data.get("access_token") or "")
    if not access:
        raise ValueError("Sign-in server returned no access token.")
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access_token": access,
        "refresh_token": str(data.get("refresh_token") or ""),
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
    }


async def exchange_code(
    *,
    token_endpoint: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    code_verifier: str,
    resource: str,
) -> dict[str, Any]:
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
        "resource": resource,
    }
    return await _token_request(token_endpoint, form)


async def refresh_tokens(
    *,
    token_endpoint: str,
    refresh_token: str,
    client_id: str,
    resource: str,
) -> dict[str, Any]:
    form = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "resource": resource,
    }
    result = await _token_request(token_endpoint, form)
    # Servers may omit a new refresh token; keep the old one in that case.
    if not result["refresh_token"]:
        result["refresh_token"] = refresh_token
    return result


async def _token_request(token_endpoint: str, form: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            res = await client.post(
                token_endpoint,
                data=form,
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise ValueError(f"Token request failed: {exc}") from exc
    if res.status_code != 200:
        raise ValueError(f"Sign-in server refused the token request ({res.status_code}).")
    return _token_result(res.json())


def is_expiring(expires_at: str | None, *, skew_seconds: int = 60) -> bool:
    """True when the access token is missing an expiry or expires within ``skew_seconds``."""
    if not expires_at:
        return True
    try:
        exp = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    return exp <= datetime.now(timezone.utc) + timedelta(seconds=skew_seconds)
