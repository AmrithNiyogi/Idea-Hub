"""MCP sign-in: start/complete the OAuth flow and keep access tokens fresh.

The OAuth ``state`` value is Fernet-encrypted and carries the PKCE verifier, the
user id and an expiry, so no server-side storage is needed between the redirect
and the callback.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.dependencies.phase23_auth import Actor
from app.integrations import mcp_client, mcp_oauth
from app.models.tracker import TrackerConnection
from app.repositories.tracker_repository import TrackerRepository
from app.schemas.trackers import TrackerConnectionOut
from app.trackers.crypto import decrypt_credentials, encrypt_credentials

PROVIDER_ID = "mcp_server"
SCOPE_USER = "user"
STATE_TTL = timedelta(minutes=10)


def redirect_uri() -> str:
    base = settings.PUBLIC_API_URL.rstrip("/")
    return f"{base}{settings.API_PREFIX}/integrations/mcp/oauth/callback"


def frontend_return_url(params: str) -> str:
    return f"{settings.FRONTEND_ORIGIN.rstrip('/')}/integrations/{PROVIDER_ID}?{params}"


class McpOAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TrackerRepository(session)

    async def start(self, endpoint_url: str, label: str, actor: Actor) -> str:
        """Return the authorization URL the browser should open."""
        endpoint = endpoint_url.strip()
        try:
            info = await mcp_oauth.discover(endpoint)
            callback = redirect_uri()
            client_id = await mcp_oauth.register_client(info["as_metadata"], callback)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

        verifier, challenge = mcp_oauth.make_pkce()
        state_payload: dict[str, Any] = {
            "uid": str(actor.id),
            "label": label,
            "endpoint": endpoint,
            "resource": info["resource"],
            "client_id": client_id,
            "token_endpoint": str(info["as_metadata"]["token_endpoint"]),
            "redirect_uri": callback,
            "verifier": verifier,
            "exp": (datetime.now(timezone.utc) + STATE_TTL).isoformat(),
        }
        return mcp_oauth.authorize_url(
            as_meta=info["as_metadata"],
            client_id=client_id,
            redirect_uri=callback,
            code_challenge=challenge,
            state=encrypt_credentials(state_payload),
            resource=info["resource"],
            scope=info["scope"],
        )

    async def complete(self, code: str, state: str, actor: Actor) -> str:
        """Exchange the code, save the connection, and return the frontend URL to show."""
        try:
            payload = decrypt_credentials(state)
            expires = datetime.fromisoformat(str(payload["exp"]))
        except (ValueError, KeyError, TypeError):
            return frontend_return_url("error=sign_in_expired")
        if expires < datetime.now(timezone.utc):
            return frontend_return_url("error=sign_in_expired")
        if str(payload.get("uid")) != str(actor.id):
            return frontend_return_url("error=sign_in_wrong_user")

        try:
            tokens = await mcp_oauth.exchange_code(
                token_endpoint=str(payload["token_endpoint"]),
                code=code,
                redirect_uri=str(payload["redirect_uri"]),
                client_id=str(payload["client_id"]),
                code_verifier=str(payload["verifier"]),
                resource=str(payload["resource"]),
            )
        except ValueError:
            return frontend_return_url("error=token_exchange_failed")

        creds = self._oauth_creds(payload, tokens)
        try:
            tools = await mcp_client.list_tools(
                creds["endpoint_url"],
                header_name="Authorization",
                header_value=f"Bearer {creds['access_token']}",
            )
        except Exception:  # noqa: BLE001 — remote/network
            return frontend_return_url("error=server_unreachable")

        await self._save(
            actor=actor,
            label=str(payload["label"] or "default"),
            creds=creds,
            tool_count=len(tools),
        )
        return frontend_return_url("connected=1")

    async def auth_for(self, conn: TrackerConnection) -> tuple[str, str, str]:
        """Return ``(endpoint_url, header_name, header_value)`` for a stored MCP connection.

        Refreshes OAuth tokens when they are near expiry and persists the new tokens.
        """
        creds = decrypt_credentials(conn.credentials_encrypted)
        endpoint = str(creds.get("endpoint_url") or "")
        if creds.get("auth_mode") != "oauth":
            return (
                endpoint,
                str(creds.get("auth_header_name") or "Authorization"),
                str(creds.get("auth_header_value") or ""),
            )

        if mcp_oauth.is_expiring(str(creds.get("expires_at") or "") or None):
            if not creds.get("refresh_token"):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "MCP sign-in expired. Sign in again under Integrations.",
                )
            try:
                tokens = await mcp_oauth.refresh_tokens(
                    token_endpoint=str(creds["token_endpoint"]),
                    refresh_token=str(creds["refresh_token"]),
                    client_id=str(creds["client_id"]),
                    resource=str(creds["resource"]),
                )
            except ValueError as exc:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "MCP sign-in expired. Sign in again under Integrations.",
                ) from exc
            creds.update(tokens)
            conn.credentials_encrypted = encrypt_credentials(creds)
            await self.session.flush()

        return endpoint, "Authorization", f"Bearer {creds['access_token']}"

    @staticmethod
    def _oauth_creds(payload: dict[str, Any], tokens: dict[str, Any]) -> dict[str, Any]:
        return {
            "auth_mode": "oauth",
            "endpoint_url": str(payload["endpoint"]),
            "resource": str(payload["resource"]),
            "client_id": str(payload["client_id"]),
            "token_endpoint": str(payload["token_endpoint"]),
            **tokens,
        }

    async def _save(
        self, *, actor: Actor, label: str, creds: dict[str, Any], tool_count: int
    ) -> TrackerConnectionOut:
        host = str(creds["endpoint_url"]).split("://", 1)[-1].split("/", 1)[0]
        encrypted = encrypt_credentials(creds)
        existing = await self.repo.find_user_connection(actor.id, PROVIDER_ID, label)
        if existing:
            existing.credentials_encrypted = encrypted
            existing.display_label = host
            existing.external_account_id = str(creds["endpoint_url"])
            existing.meta = {"tool_count": tool_count}
            await self.session.flush()
            row = existing
        else:
            row = TrackerConnection(
                scope=SCOPE_USER,
                user_id=actor.id,
                created_by=actor.id,
                provider_id=PROVIDER_ID,
                label=label,
                display_label=host,
                credentials_encrypted=encrypted,
                meta={"tool_count": tool_count},
                external_account_id=str(creds["endpoint_url"]),
            )
            await self.repo.add_connection(row)
        await self.session.commit()
        return TrackerConnectionOut.model_validate(row)
