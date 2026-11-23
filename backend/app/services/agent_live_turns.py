"""Live IdeaKonnekt chat/agent turns via AI Studio ``runs/execute``.

When ``SIMULATE_AGENTS=false`` and AI Studio env is configured, Submit assist,
Help, Idea Optimizer, and Review Intelligence call Kompass agents over HTTP.
Response shapes match the simulate schemas so React clients stay stable.

conversation_id lifecycle:
- Client may omit on the first turn; the engine creates a thread and returns id.
- Client must echo ``conversation_id`` on later turns for the same chat thread.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import HTTPException

from app.services import aistudio_execute_client as studio
from app.services import agent_simulate_service as simulate

logger = logging.getLogger(__name__)

LIVE_ENGINE = studio.ENGINE
LIVE_NOTICE = "Live — AI Studio runs/execute"


def _live_meta(*, conversation_id: Optional[str] = None) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "simulated": False,
        "engine": LIVE_ENGINE,
        "mode": "live",
        "notice": LIVE_NOTICE,
    }
    if conversation_id:
        meta["conversation_id"] = conversation_id
    return meta


def _http_error(exc: Exception) -> HTTPException:
    logger.warning("AI Studio execute failed: %s", type(exc).__name__)
    return HTTPException(
        status_code=502,
        detail="AI Studio agent execute failed. Try again or enable SIMULATE_AGENTS.",
    )


async def submit_assist_turn(
    *,
    draft: dict[str, Any],
    message: str,
    awaiting_field: Optional[str] = None,
    conversation_id: Optional[str] = None,
    taxonomy: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Run Submit assist via Kompass or fall back to local simulation.

    Args:
        draft: Current form values.
        message: Latest user chat text.
        awaiting_field: Optional soft focus from a prior turn.
        conversation_id: Prior AI Studio conversation id for this thread.

    Returns:
        Turn payload matching ``SubmitAssistTurnOut`` (+ ``conversation_id``).
    """
    if not studio.use_live_execute():
        out = simulate.submit_assist_turn(
            draft=draft, message=message, awaiting_field=awaiting_field
        )
        if conversation_id:
            out["conversation_id"] = conversation_id
        return out

    agent_id = studio.resolve_kompass_agent_id("submit-assist")
    if not agent_id:
        # No live agent yet: keep the chat working on the local simulation, and say so.
        out = simulate.submit_assist_turn(
            draft=draft, message=message, awaiting_field=awaiting_field
        )
        out["simulated"] = True
        if conversation_id:
            out["conversation_id"] = conversation_id
        return out

    payload = {
        "draft": draft or {},
        "message": message or "",
        "awaiting_field": awaiting_field,
        "taxonomy": taxonomy or [],
    }
    try:
        result = await studio.execute_run(
            agent_id=agent_id,
            input_payload=json.dumps(payload, ensure_ascii=False),
            conversation_id=conversation_id,
        )
    except Exception as exc:  # noqa: BLE001 — surface as gateway failure
        raise _http_error(exc) from exc

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail=result.error or "Submit assist agent returned an error.",
        )

    structured = studio.parse_structured_result(result.result)
    reply = (
        str(structured.get("reply") or "").strip()
        or result.result_text
        or "No response received."
    )
    patches = structured.get("patches")
    if not isinstance(patches, dict):
        patches = {}
    awaiting = structured.get("awaiting_field", awaiting_field)
    if awaiting is not None:
        awaiting = str(awaiting) if awaiting else None
    done = bool(structured.get("done", False))
    field_prompt = structured.get("field_prompt")
    if field_prompt is not None:
        field_prompt = str(field_prompt)

    out = {
        **_live_meta(conversation_id=result.conversation_id or conversation_id),
        "reply": reply,
        "patches": patches,
        "awaiting_field": awaiting,
        "field_prompt": field_prompt,
        "done": done,
    }
    return out


MAX_FOLLOWUPS = 3


def clean_followups(raw: Any) -> list[str]:
    """Keep up to three non-empty, de-duplicated follow-up questions from an agent reply.

    Args:
        raw: The ``followups`` value from the agent's structured output.

    Returns:
        At most three question strings, in their original order.
    """
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) == MAX_FOLLOWUPS:
            break
    return out


async def help_turn(
    *,
    message: str,
    conversation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Run Help guide via Kompass or fall back to local FAQ map."""
    if not studio.use_live_execute():
        out = simulate.help_turn(message=message)
        if conversation_id:
            out["conversation_id"] = conversation_id
        return out

    agent_id = studio.resolve_kompass_agent_id("help")
    if not agent_id:
        raise HTTPException(
            status_code=503,
            detail="AISTUDIO_AGENT_HELP is not configured.",
        )

    try:
        result = await studio.execute_run(
            agent_id=agent_id,
            input_payload=message,
            conversation_id=conversation_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail=result.error or "Help agent returned an error.",
        )

    structured = studio.parse_structured_result(result.result)
    reply = (
        str(structured.get("reply") or "").strip()
        or result.result_text
        or "No response received."
    )
    topic = str(structured.get("topic") or "live")
    links_raw = structured.get("links")
    links: list[dict[str, str]] = []
    if isinstance(links_raw, list):
        for item in links_raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            href = str(item.get("href") or "").strip()
            if label and href:
                links.append({"label": label, "href": href})

    return {
        **_live_meta(conversation_id=result.conversation_id or conversation_id),
        "topic": topic,
        "reply": reply,
        "links": links,
        "followups": clean_followups(structured.get("followups")),
    }


async def idea_optimize_turn(
    *,
    idea: dict[str, Any],
    message: str,
    messages: Optional[list[dict[str, Any]]] = None,
    conversation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Run author Idea Optimizer via Kompass or fall back to local heuristics."""
    if not studio.use_live_execute():
        out = simulate.idea_optimize_turn(
            idea=idea, message=message, messages=messages
        )
        if conversation_id:
            out["conversation_id"] = conversation_id
        return out

    agent_id = studio.resolve_kompass_agent_id("idea-optimizer")
    if not agent_id:
        raise HTTPException(
            status_code=503,
            detail="AISTUDIO_AGENT_IDEA_OPTIMIZER is not configured.",
        )

    payload = {
        "idea": idea or {},
        "message": message or "",
        "messages": messages or [],
    }
    try:
        result = await studio.execute_run(
            agent_id=agent_id,
            input_payload=json.dumps(payload, ensure_ascii=False),
            conversation_id=conversation_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail=result.error or "Idea optimizer agent returned an error.",
        )

    structured = studio.parse_structured_result(result.result)
    reply = (
        str(structured.get("reply") or "").strip()
        or result.result_text
        or "No response received."
    )
    field_patches = structured.get("field_patches")
    if not isinstance(field_patches, dict):
        field_patches = {}
    focus = structured.get("focus_fields")
    focus_fields = (
        [str(x) for x in focus]
        if isinstance(focus, list)
        else []
    )

    return {
        **_live_meta(conversation_id=result.conversation_id or conversation_id),
        "reply": reply,
        "field_patches": field_patches,
        "focus_fields": focus_fields,
    }


async def review_intelligence_turn(
    *,
    idea_context: dict[str, Any],
    conversation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Execute Review Intelligence via Kompass; returns raw structured output.

    Args:
        idea_context: Idea + comments/votes/similar snapshot for the agent.
        conversation_id: Optional thread id (usually one-shot; rarely reused).

    Returns:
        Dict with ``output`` (parsed agent JSON or ``{"reply": text}``),
        ``summary``, and ``conversation_id``.

    Raises:
        HTTPException: When live mode is on but agent env / execute fails.
    """
    agent_id = studio.resolve_kompass_agent_id("review-intelligence")
    if not agent_id:
        raise HTTPException(
            status_code=503,
            detail="AISTUDIO_AGENT_REVIEW_INTELLIGENCE is not configured.",
        )
    try:
        result = await studio.execute_run(
            agent_id=agent_id,
            input_payload=json.dumps(idea_context, ensure_ascii=False, default=str),
            conversation_id=conversation_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail=result.error or "Review intelligence agent returned an error.",
        )

    structured = studio.parse_structured_result(result.result)
    output = structured if structured else {"reply": result.result_text}
    return {
        "output": output,
        "summary": "Live Review Intelligence brief via AI Studio",
        "conversation_id": result.conversation_id or conversation_id,
        "engine": LIVE_ENGINE,
        "simulated": False,
    }
