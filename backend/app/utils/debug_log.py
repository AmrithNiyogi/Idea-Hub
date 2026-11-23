"""Debug logging for agent auth: what arrived (headers, cookies, body) and what we sent out.

Token values are masked: the scheme, the first 12 and last 6 characters, and the length. Enough to
tell whether a token arrived and which form it took, without writing the credential to the log.
Enabled by ``AGENT_INTERNAL_DEBUG_LOG=true``. Off by default.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import Request

from app.config.settings import settings

logger = logging.getLogger("agent.debug")
SENSITIVE = {"authorization", "x-authorization", "cookie", "set-cookie"}
BODY_LIMIT = 500


def mask(value: str) -> str:
    """Keep the scheme (Bearer) and a few edge characters. Never the middle of a credential."""
    if settings.AGENT_INTERNAL_DEBUG_UNMASKED:
        return value
    scheme = ""
    raw = value.strip()
    if raw.lower().startswith("bearer "):
        scheme, raw = "Bearer ", raw[7:].strip()
    if len(raw) <= 20:
        return f"{scheme}*** (len {len(raw)})"
    return f"{scheme}{raw[:12]}...{raw[-6:]} (len {len(raw)})"


def describe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Headers with credentials masked. Cookie values are masked too, names are kept."""
    out: dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() == "cookie":
            pairs = [p.strip() for p in value.split(";") if p.strip()]
            out[name] = "; ".join(
                f"{p.split('=', 1)[0]}={mask(p.split('=', 1)[1]) if '=' in p else ''}" for p in pairs
            )
        elif name.lower() in SENSITIVE:
            out[name] = mask(value)
        else:
            out[name] = value
    return out


async def log_incoming_request(request: Request) -> None:
    """Router dependency: log what the caller sent, before any auth check runs."""
    if not settings.AGENT_INTERNAL_DEBUG_LOG:
        return
    body = (await request.body())[:BODY_LIMIT].decode("utf-8", errors="replace")
    logger.warning(
        "INCOMING %s %s query=%s client=%s\n  headers=%s\n  cookies=%s\n  body=%s",
        request.method,
        request.url.path,
        dict(request.query_params),
        request.client.host if request.client else None,
        describe_headers(request.headers),
        sorted(request.cookies.keys()),
        body or "<none>",
    )


def log_outgoing_run(url: str, headers: Mapping[str, str], body: Mapping[str, object]) -> None:
    """Log what the Hub sends to the Kompass execute endpoint."""
    if not settings.AGENT_INTERNAL_DEBUG_LOG:
        return
    logger.warning(
        "OUTGOING POST %s\n  headers=%s\n  body=%s",
        url,
        describe_headers(headers),
        str(body)[:BODY_LIMIT],
    )
