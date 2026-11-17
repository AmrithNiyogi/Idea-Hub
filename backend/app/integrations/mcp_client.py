"""Minimal MCP HTTP/JSON-RPC client for custom team-space tools.

MVP supports Streamable-HTTP / JSON-RPC style endpoints that accept::

    POST {endpoint}
    {"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
    {"jsonrpc":"2.0","id":2,"method":"tools/call",
     "params":{"name":"schedule_meeting","arguments":{…}}}

SSE and stdio transports are out of scope; store them as ``transport=stub``
and document the expected tool contract in docs/TEAM_SPACE.md.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

import httpx


def require_https_endpoint(url: str) -> str:
    raw = (url or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in ("https", "http"):
        raise ValueError("MCP endpoint must be http(s)://")
    if parsed.scheme == "http" and parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise ValueError("Non-local MCP endpoints must use https://")
    if not parsed.netloc:
        raise ValueError("MCP endpoint URL is incomplete.")
    return raw


def auth_headers(
    *,
    header_name: str = "Authorization",
    header_value: str = "",
) -> dict[str, str]:
    name = (header_name or "Authorization").strip() or "Authorization"
    value = (header_value or "").strip()
    if not value:
        return {"Content-Type": "application/json", "Accept": "application/json"}
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        name: value,
    }


async def jsonrpc_call(
    endpoint_url: str,
    method: str,
    params: Optional[dict[str, Any]] = None,
    *,
    headers: Optional[dict[str, str]] = None,
    request_id: int = 1,
    timeout: float = 20.0,
) -> Any:
    """POST a JSON-RPC 2.0 request; return ``result`` or raise ValueError."""
    url = require_https_endpoint(endpoint_url)
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers or {})
    if resp.status_code >= 400:
        raise ValueError(f"MCP HTTP {resp.status_code}: {(resp.text or '')[:300]}")
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"MCP response was not JSON: {exc}") from exc
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise ValueError(f"MCP error: {msg}")
    if isinstance(data, dict) and "result" in data:
        return data["result"]
    return data


async def list_tools(
    endpoint_url: str,
    *,
    header_name: str = "Authorization",
    header_value: str = "",
) -> list[dict[str, Any]]:
    """Call ``tools/list`` and normalize to ``[{name, description, inputSchema}]``."""
    headers = auth_headers(header_name=header_name, header_value=header_value)
    result = await jsonrpc_call(
        endpoint_url, "tools/list", {}, headers=headers, request_id=1
    )
    tools_raw: Any
    if isinstance(result, dict):
        tools_raw = result.get("tools") or result.get("result") or []
    elif isinstance(result, list):
        tools_raw = result
    else:
        tools_raw = []
    out: list[dict[str, Any]] = []
    for t in tools_raw:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name") or "").strip()
        if not name:
            continue
        out.append(
            {
                "name": name,
                "description": str(t.get("description") or ""),
                "inputSchema": t.get("inputSchema") or t.get("input_schema") or {},
            }
        )
    return out


async def call_tool(
    endpoint_url: str,
    name: str,
    arguments: Optional[dict[str, Any]] = None,
    *,
    header_name: str = "Authorization",
    header_value: str = "",
) -> Any:
    """Call ``tools/call`` for ``name`` with ``arguments``."""
    headers = auth_headers(header_name=header_name, header_value=header_value)
    return await jsonrpc_call(
        endpoint_url,
        "tools/call",
        {"name": name, "arguments": arguments or {}},
        headers=headers,
        request_id=2,
    )


# Built-in tool names Idea Hub understands when a custom MCP exposes them.
KNOWN_TEAM_TOOLS = (
    "schedule_meeting",
    "list_channels",
    "post_channel_message",
)

STUB_TOOL_CATALOG: list[dict[str, Any]] = [
    {
        "name": "schedule_meeting",
        "description": (
            "Schedule a team meeting for an Idea Hub team space. "
            "Args: title, starts_at (ISO-8601), ends_at?, description?, "
            "join_url?, channel_slug?, notify_teams?"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "starts_at": {"type": "string", "format": "date-time"},
                "ends_at": {"type": "string", "format": "date-time"},
                "description": {"type": "string"},
                "join_url": {"type": "string"},
                "channel_slug": {"type": "string"},
                "notify_teams": {"type": "boolean"},
            },
            "required": ["title", "starts_at"],
        },
    },
    {
        "name": "post_channel_message",
        "description": "Post a message into an idea team channel by slug.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_slug": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["channel_slug", "body"],
        },
    },
]
