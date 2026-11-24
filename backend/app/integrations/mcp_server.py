"""MCP server as an Integrations catalog entry (category ``mcp``).

A personal or org connection stores one MCP endpoint plus its auth header.
Groups attach a connection and then discover / call its tools, so the same
server (for example a meeting-notes MCP) can be reused across groups.

Only header-based auth is supported here. OAuth-only MCP servers need a
separate flow and are not covered by this provider.
"""

from __future__ import annotations

from typing import Any

from app.integrations import mcp_client
from app.trackers.base import ConnectField, ConnectionProbe

_NOT_TRACKER = "MCP servers do not hold tracker items; attach them to a group instead."


class McpServerProvider:
    """Connect/validate an MCP endpoint. Tracker-item methods are not applicable."""

    id = "mcp_server"
    display_name = "MCP server"
    description = (
        "Connect any MCP server over HTTPS (JSON-RPC). Attach it to a group to use "
        "its tools in that group's channels."
    )
    auth_mode = "api_token"
    integration_category = "mcp"
    connect_fields = [
        ConnectField(
            key="endpoint_url",
            label="Endpoint URL",
            placeholder="https://mcp.example.com/mcp",
            help_text="Must be HTTPS.",
        ),
        ConnectField(
            key="auth_header_name",
            label="Auth header name",
            required=False,
            placeholder="Authorization",
            advanced=True,
        ),
        ConnectField(
            key="auth_header_value",
            label="Auth header value",
            secret=True,
            required=False,
            placeholder="Bearer …",
            help_text="Leave empty if the server needs no auth.",
        ),
    ]

    async def validate_connection(self, credentials: dict[str, Any]) -> ConnectionProbe:
        endpoint = str(credentials.get("endpoint_url") or "").strip()
        mcp_client.require_https_endpoint(endpoint)
        header_name = str(credentials.get("auth_header_name") or "").strip() or "Authorization"
        header_value = str(credentials.get("auth_header_value") or "").strip()
        try:
            tools = await mcp_client.list_tools(
                endpoint, header_name=header_name, header_value=header_value
            )
        except Exception as exc:  # noqa: BLE001 — remote/network, surfaced to the user
            raise ValueError(f"Could not list tools from MCP server: {exc}") from exc
        host = endpoint.split("://", 1)[-1].split("/", 1)[0]
        return ConnectionProbe(
            display_label=host,
            external_account_id=endpoint,
            meta={"tool_count": len(tools)},
        )

    async def create_issue(self, *_args: Any, **_kwargs: Any) -> Any:
        raise ValueError(_NOT_TRACKER)

    async def resolve_existing(self, *_args: Any, **_kwargs: Any) -> Any:
        raise ValueError(_NOT_TRACKER)

    async def get_task(self, *_args: Any, **_kwargs: Any) -> Any:
        raise ValueError(_NOT_TRACKER)

    async def update_task(self, *_args: Any, **_kwargs: Any) -> Any:
        raise ValueError(_NOT_TRACKER)
