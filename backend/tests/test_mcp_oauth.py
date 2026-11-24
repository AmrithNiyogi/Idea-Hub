"""MCP OAuth helpers: resource canonicalisation, PKCE S256, challenge parsing, expiry."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from app.integrations import mcp_oauth


def test_canonical_resource_strips_slash_and_lowercases_host() -> None:
    assert mcp_oauth.canonical_resource("HTTPS://MCP.Example.com/mcp/") == "https://mcp.example.com/mcp"
    assert mcp_oauth.canonical_resource("https://mcp.example.com") == "https://mcp.example.com"


def test_pkce_challenge_is_s256_of_verifier() -> None:
    verifier, challenge = mcp_oauth.make_pkce()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert challenge == expected
    assert 43 <= len(verifier) <= 128


def test_challenge_param_reads_resource_metadata() -> None:
    header = 'Bearer resource_metadata="https://x.example/.well-known/oauth-protected-resource", scope="a b"'
    assert mcp_oauth._challenge_param(header, "resource_metadata") == (
        "https://x.example/.well-known/oauth-protected-resource"
    )
    assert mcp_oauth._challenge_param(header, "scope") == "a b"
    assert mcp_oauth._challenge_param(header, "missing") == ""


def test_authorize_url_carries_pkce_and_resource() -> None:
    url = mcp_oauth.authorize_url(
        as_meta={"authorization_endpoint": "https://auth.example/authorize"},
        client_id="cid",
        redirect_uri="https://api.example/cb",
        code_challenge="chal",
        state="st",
        resource="https://mcp.example.com/mcp",
        scope="",
    )
    q = parse_qs(urlparse(url).query)
    assert q["code_challenge_method"] == ["S256"]
    assert q["code_challenge"] == ["chal"]
    assert q["resource"] == ["https://mcp.example.com/mcp"]
    assert "scope" not in q


def test_is_expiring_handles_missing_and_near_expiry() -> None:
    assert mcp_oauth.is_expiring(None) is True
    soon = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
    later = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert mcp_oauth.is_expiring(soon) is True
    assert mcp_oauth.is_expiring(later) is False
