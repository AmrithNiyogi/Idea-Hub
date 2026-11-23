"""AI Studio / Kompass ``POST /api/v2/runs/execute`` HTTP client.

Responsibilities:
- Call the staging (or configured) API Gateway execute contract used by
  chatbot-admin / ``aistudio-chatbot-ui-v2``.
- Send tenant + project-slug headers; optionally forward ``X-Authorization``
  for tool auth (never expose this token to the browser).
- Preserve ``conversation_id`` across chat turns when the caller supplies it;
  surface the id returned by the engine when starting a new thread.

Collaborators:
- ``app.config.settings.Settings`` for base URL / tenant / project / tokens.
- ``httpx.AsyncClient`` for outbound HTTP.

This module must never log secrets (tool auth token, Authorization).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.config.settings import settings
from app.utils.debug_log import log_outgoing_run
from app.utils.jsonish import as_dict

logger = logging.getLogger(__name__)

ENGINE = "aistudio-runs-execute-v2"

# Hub roster / simulate surface → Settings attribute holding the Kompass agent id/slug.
HUB_AGENT_ENV_KEYS: dict[str, str] = {
    "submit-assist": "AISTUDIO_AGENT_SUBMIT_ASSIST",
    "help": "AISTUDIO_AGENT_HELP",
    "idea-optimizer": "AISTUDIO_AGENT_IDEA_OPTIMIZER",
    "review-intelligence": "AISTUDIO_AGENT_REVIEW_INTELLIGENCE",
    "coding-agent-build": "AISTUDIO_AGENT_CODING_BUILD",
    "ideathon-rank": "AISTUDIO_AGENT_IDEATHON_RANK",
    "ideathon-cluster": "AISTUDIO_AGENT_IDEATHON_CLUSTER",
    "ideathon-pitch": "AISTUDIO_AGENT_IDEATHON_PITCH",
    "ideathon-draft": "AISTUDIO_AGENT_IDEATHON_DRAFT",
}


@dataclass
class ExecuteResult:
    """Normalized execute outcome for IdeaKonnekt adapters.

    Attributes:
        success: True when a usable result was obtained.
        result: Raw assistant payload (str, dict, or list) from the engine.
        result_text: String form of ``result`` when available.
        conversation_id: Thread id returned or echoed by the engine.
        run_id: Optional run id (useful after 202 poll).
        error: Human-readable error when ``success`` is False.
        raw: Full JSON body (or last poll payload) for debugging.
        metadata: Nested metadata object when present.
    """

    success: bool
    result: Any = None
    result_text: str = ""
    conversation_id: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def aistudio_configured() -> bool:
    """Return True when base URL, tenant, and project-slug are set.

    ``X-Authorization`` / tool token is optional (admin UI note: only needed
    when a tool must authenticate). Per-agent ids are checked separately via
    ``resolve_kompass_agent_id``.
    """
    return bool(
        (settings.AISTUDIO_API_BASE_URL or "").strip()
        and (settings.AISTUDIO_TENANT_ID or "").strip()
        and (settings.AISTUDIO_PROJECT_SLUG or "").strip()
    )


def use_live_execute() -> bool:
    """Return True when live ``runs/execute`` should be used instead of stubs.

    Live mode requires ``SIMULATE_AGENTS=false`` and a configured AI Studio
    gateway (base URL + tenant + project-slug).
    """
    return (not settings.SIMULATE_AGENTS) and aistudio_configured()


def resolve_kompass_agent_id(hub_agent_key: str) -> Optional[str]:
    """Map an IdeaKonnekt surface key to the Kompass ``agent_id`` / slug.

    Args:
        hub_agent_key: One of ``submit-assist``, ``help``, ``idea-optimizer``,
            ``review-intelligence``, ``coding-agent-build``.

    Returns:
        Configured Kompass agent id/slug, or None if unset.
    """
    attr = HUB_AGENT_ENV_KEYS.get(hub_agent_key)
    if not attr:
        return None
    value = getattr(settings, attr, "") or ""
    value = str(value).strip()
    return value or None


def _base_url() -> str:
    return (settings.AISTUDIO_API_BASE_URL or "").rstrip("/")


def build_execute_headers(tool_auth_token: str | None = None) -> dict[str, str]:
    """Build outbound headers for ``POST /api/v2/runs/execute``.

    Returns:
        Headers including ``X-Tenant-ID``, ``project-slug``, and optional
        ``X-Authorization`` when ``AISTUDIO_TOOL_AUTH_TOKEN`` is set.
    """
    headers: dict[str, str] = {
        "accept": "*/*",
        "Content-Type": "application/json",
        "X-Tenant-ID": (settings.AISTUDIO_TENANT_ID or "").strip(),
        "project-slug": (settings.AISTUDIO_PROJECT_SLUG or "").strip(),
    }
    token = (tool_auth_token or settings.AISTUDIO_TOOL_AUTH_TOKEN or "").strip()
    if token:
        # The engine forwards this to tools as `Authorization`; the Hub reads only the Bearer form.
        headers["X-Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    return headers


def _dig_conversation_id(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("conversation_id", "conversationId"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    data = payload.get("data")
    if isinstance(data, dict):
        return _dig_conversation_id(data)
    return None


def _dig_run_id(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("run_id", "id"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    data = payload.get("data")
    if isinstance(data, dict):
        return _dig_run_id(data)
    return None


def _unwrap_source(payload: dict[str, Any]) -> dict[str, Any]:
    outer = payload.get("data") if isinstance(payload.get("data"), dict) else None
    inner = (
        outer.get("data")
        if outer and isinstance(outer.get("data"), dict)
        else outer
    )
    source = inner if isinstance(inner, dict) else payload
    return source if isinstance(source, dict) else payload


def normalize_execution_payload(payload: Any) -> ExecuteResult:
    """Normalize gateway / engine JSON into ``ExecuteResult``.

    Mirrors ``aistudio-chatbot-ui-v2`` ``ApiClient._normalizeExecutionResponse``
    field preference order (result / output / answer / final_output / content).
    """
    if not isinstance(payload, dict):
        return ExecuteResult(
            success=False,
            error="Invalid response payload from AI Studio.",
            raw={},
        )

    source = _unwrap_source(payload)
    result = (
        source.get("result")
        if "result" in source
        else source.get("output")
        if "output" in source
        else source.get("answer")
        if "answer" in source
        else source.get("final_output")
        if "final_output" in source
        else source.get("content")
        if isinstance(source.get("content"), str)
        else None
    )

    error = (
        source.get("error")
        or source.get("error_message")
        or (
            source.get("message")
            if source.get("success") is False and isinstance(source.get("message"), str)
            else None
        )
    )
    if error is not None and not isinstance(error, str):
        error = str(error)

    success = (
        bool(source["success"])
        if isinstance(source.get("success"), bool)
        else bool(not error and result is not None and result != "")
    )

    if isinstance(result, str):
        result_text = result
    elif result is None:
        result_text = ""
    else:
        try:
            result_text = json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            result_text = str(result)

    metadata = as_dict(source.get("metadata"))

    return ExecuteResult(
        success=success,
        result=result,
        result_text=result_text,
        conversation_id=_dig_conversation_id(payload) or _dig_conversation_id(source),
        run_id=_dig_run_id(payload) or _dig_run_id(source),
        error=error if isinstance(error, str) else None,
        raw=payload,
        metadata=metadata,
    )


def parse_structured_result(result: Any) -> dict[str, Any]:
    """Best-effort parse of agent output into a dict (JSON object).

    Args:
        result: Raw execute ``result`` (str or already-parsed object).

    Returns:
        A dict when the payload is/contains a JSON object; otherwise ``{}``.
    """
    if isinstance(result, dict):
        return result
    if not isinstance(result, str):
        return {}
    text = result.strip()
    if not text:
        return {}
    # Strip common markdown fences.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try first {...} slice.
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                parsed = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        else:
            return {}
    return as_dict(parsed)


async def execute_flow(
    *,
    slug: str,
    inputs: dict[str, Any],
    timeout_seconds: Optional[float] = None,
    tool_auth_token: Optional[str] = None,
) -> ExecuteResult:
    """POST ``/api/v1/flows/execute/{slug}`` and return the flow's output.

    The flow's Output node sets the keys of ``result``. A run that did not complete,
    or that reported errors, comes back as an unsuccessful ``ExecuteResult``.
    """
    if not aistudio_configured():
        return ExecuteResult(success=False, error="AI Studio execute is not configured.")
    if not (slug or "").strip():
        return ExecuteResult(success=False, error="Workflow slug is empty.")

    url = f"{_base_url()}/api/v1/flows/execute/{slug.strip()}"
    body: dict[str, Any] = {"inputs": inputs}
    timeout = timeout_seconds
    if timeout is None:
        timeout = float(settings.AISTUDIO_EXECUTE_TIMEOUT_SECONDS or 120)

    headers = build_execute_headers(tool_auth_token)
    log_outgoing_run(url, headers, body)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=body)

    if response.status_code >= 400:
        return ExecuteResult(
            success=False,
            error=_error_detail(response) or f"Flow execute failed: HTTP {response.status_code}",
            raw=_safe_json(response),
        )

    payload = response.json() if response.content else {}
    if not isinstance(payload, dict):
        return ExecuteResult(success=False, error="Flow returned an unreadable reply.")
    data_obj = payload.get("data")
    envelope = data_obj if isinstance(data_obj, dict) else payload
    status = str(envelope.get("status") or "completed").lower()
    errors = envelope.get("errors") or []
    if status != "completed" or errors:
        detail = str(errors[0]) if errors else f"Flow ended with status: {status}"
        return ExecuteResult(success=False, error=detail, raw=payload)
    output = envelope.get("output")
    if not isinstance(output, dict):
        return ExecuteResult(success=False, error="Flow returned no output object.", raw=payload)
    return ExecuteResult(
        success=True,
        result=output,
        result_text=json.dumps(output, ensure_ascii=False),
        raw=payload,
    )


def _input_text(payload: Any) -> str:
    """Kompass expects the run ``input`` as a string; structured input goes as a JSON string."""
    return payload if isinstance(payload, str) else json.dumps(payload)


async def execute_run(
    *,
    agent_id: str,
    input_payload: Any,
    conversation_id: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    tool_auth_token: Optional[str] = None,
) -> ExecuteResult:
    """POST ``/api/v2/runs/execute`` and normalize the reply.

    Args:
        agent_id: Kompass agent id or slug (not the IdeaKonnekt roster id).
        input_payload: Value for body ``input`` (string or JSON-serializable).
        conversation_id: Optional prior thread id; omit to let the engine create one.
        tool_auth_token: Sent as X-Authorization for this run only. Pass the signed-in
            user's access token; falls back to AISTUDIO_TOOL_AUTH_TOKEN when omitted.
        timeout_seconds: Override request timeout (defaults to settings).

    Returns:
        ``ExecuteResult`` with ``conversation_id`` when the engine provides one.

    Raises:
        httpx.HTTPError: On transport failures after retries are exhausted
            (caller should catch and fall back or surface a 502).

    Side Effects:
        Outbound HTTPS to ``AISTUDIO_API_BASE_URL``. Does not persist state.
    """
    if not aistudio_configured():
        return ExecuteResult(
            success=False,
            error=(
                "AI Studio execute is not configured "
                "(need AISTUDIO_API_BASE_URL, AISTUDIO_TENANT_ID, AISTUDIO_PROJECT_SLUG)."
            ),
        )
    if not (agent_id or "").strip():
        return ExecuteResult(success=False, error="Kompass agent_id is empty.")

    # Agent route, not runs/execute: only this one binds the caller's X-Authorization into tools.
    url = f"{_base_url()}/api/v1/agents/{agent_id.strip()}/execute"
    body: dict[str, Any] = {"task": _input_text(input_payload)}
    if conversation_id and str(conversation_id).strip():
        body["session_id"] = str(conversation_id).strip()

    timeout = timeout_seconds
    if timeout is None:
        timeout = float(settings.AISTUDIO_EXECUTE_TIMEOUT_SECONDS or 120)

    headers = build_execute_headers(tool_auth_token)
    log_outgoing_run(url, headers, body)
    logger.info(
        "aistudio execute agent_id=%s conversation=%s project_slug_set=%s",
        agent_id.strip(),
        bool(body.get("conversation_id")),
        bool(headers.get("project-slug")),
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=body)

        if response.status_code == 202:
            pending = response.json() if response.content else {}
            run_id = _dig_run_id(pending)
            if not run_id:
                return ExecuteResult(
                    success=False,
                    error="Run accepted (202) but no run_id was returned.",
                    raw=as_dict(pending),
                )
            return await _poll_run(client, run_id, headers=headers)

        if response.status_code >= 400:
            detail = _error_detail(response)
            return ExecuteResult(
                success=False,
                error=detail or f"AI Studio execute failed: HTTP {response.status_code}",
                raw=_safe_json(response),
            )

        data = response.json() if response.content else {}
        normalized = normalize_execution_payload(as_dict(data))
        # Agent execute replies carry no conversation id; echo the session the caller sent.
        normalized.conversation_id = normalized.conversation_id or (conversation_id or None)
        return normalized


async def _poll_run(
    client: httpx.AsyncClient,
    run_id: str,
    *,
    headers: dict[str, str],
    max_attempts: int = 60,
    interval_ms: int = 2000,
) -> ExecuteResult:
    """Poll ``GET /api/v2/runs/{run_id}`` until terminal or timeout."""
    import asyncio

    pending_statuses = {"pending", "running", "in_progress", "queued", "started"}
    url = f"{_base_url()}/api/v2/runs/{run_id}"
    last: dict[str, Any] = {}

    for attempt in range(max_attempts):
        response = await client.get(url, headers=headers)
        if response.status_code >= 400:
            return ExecuteResult(
                success=False,
                error=_error_detail(response) or f"Poll failed: HTTP {response.status_code}",
                run_id=run_id,
                raw=_safe_json(response),
            )
        payload = response.json() if response.content else {}
        last = as_dict(payload)
        normalized = normalize_execution_payload(last)
        normalized.run_id = normalized.run_id or run_id

        status_raw = last.get("status")
        data = last.get("data")
        if status_raw is None and isinstance(data, dict):
            status_raw = data.get("status")
        status = str(status_raw).lower() if status_raw is not None else None

        if normalized.result is not None or normalized.error:
            return normalized
        if status and status not in pending_statuses:
            if not normalized.success and not normalized.error:
                normalized.error = f"Run ended with status: {status_raw}"
            return normalized

        if attempt < max_attempts - 1:
            await asyncio.sleep(interval_ms / 1000.0)

    return ExecuteResult(
        success=False,
        error="Run did not complete in time.",
        run_id=run_id,
        raw=last,
        conversation_id=_dig_conversation_id(last),
    )


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"detail": data}
    except Exception:
        return {"detail": (response.text or "")[:500]}


def _error_detail(response: httpx.Response) -> Optional[str]:
    data = _safe_json(response)
    for key in ("detail", "message", "error"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list) and val:
            return str(val[0])
    return None
