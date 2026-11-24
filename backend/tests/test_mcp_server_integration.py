"""MCP server appears in the Integrations catalog and rejects non-HTTPS endpoints."""

from __future__ import annotations

import asyncio

import pytest

from app.integrations.adapters import get_adapter
from app.integrations.registry import list_integrations


def test_mcp_category_lists_mcp_server() -> None:
    ids = {d.id for d in list_integrations(category="mcp")}
    assert "mcp_server" in ids


def test_mcp_server_requires_https() -> None:
    provider = get_adapter("mcp_server")
    with pytest.raises(ValueError):
        asyncio.run(provider.validate_connection({"endpoint_url": "http://insecure.example"}))
