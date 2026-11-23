"""Ideathon Draft agent: suggest challenge statements from a theme, at create time.

Responsibilities:
- Build the run input for the Kompass ``ideakonnekt-ideathon-draft`` agent.
- Read its reply and keep only usable challenge statements (20 to 300 characters, at most 3),
  the same rules the create form enforces.

Collaborators:
- ``aistudio_execute_client`` for the HTTP call, agent id resolution and reply parsing.

Side Effects:
- Outbound call to the Kompass execute endpoint. Nothing is written to the database.
- The result is a proposal. The organiser edits or discards it before creating anything.

Expected agent reply: a JSON object ``{"names": ["...", ...], "challenges": ["How might we ...", ...]}``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ideathon import Ideathon
from app.services import aistudio_execute_client as studio

HUB_AGENT_KEY = "ideathon-draft"
MIN_LEN = 20
MAX_LEN = 300
MAX_CHALLENGES = 3
MAX_NAMES = 4
MAX_EXISTING = 20  # most recent ideathons sent as context
NAME_MAX_LEN = 80  # the create form's Name field limit


async def existing_context(session: AsyncSession) -> list[dict[str, Any]]:
    """Titles, themes and challenges of the most recent ideathons, so the draft avoids repeats.

    Sponsors and organisers are left out: the agent only needs the wording.
    """
    rows = (
        await session.execute(
            select(Ideathon.title, Ideathon.theme, Ideathon.challenges)
            .order_by(Ideathon.start_at.desc())
            .limit(MAX_EXISTING)
        )
    ).all()
    return [
        {"title": title, "theme": theme, "challenges": [str(c) for c in (challenges or [])]}
        for title, theme, challenges in rows
    ]


def build_draft_input(theme: str, existing: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run input for the draft agent: the theme the organiser typed, and the existing ideathons."""
    return {"stage": "draft", "theme": theme.strip(), "existing": existing or []}


def usable_names(parsed: dict[str, Any]) -> list[str]:
    """Distinct name options within the form's limit, up to four. Empty when the agent gave none."""
    raw = parsed.get("names")
    if not isinstance(raw, list):
        return []
    kept: list[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if 3 <= len(text) <= NAME_MAX_LEN and text not in kept:
                kept.append(text)
        if len(kept) == MAX_NAMES:
            break
    return kept


def usable_challenges(parsed: dict[str, Any]) -> list[str]:
    """Keep string statements within the form's length rules, up to the form's maximum."""
    raw = parsed.get("challenges")
    if not isinstance(raw, list):
        return []
    kept: list[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if MIN_LEN <= len(text) <= MAX_LEN:
                kept.append(text)
        if len(kept) == MAX_CHALLENGES:
            break
    return kept


async def propose_draft(
    theme: str,
    *,
    existing: list[dict[str, Any]] | None = None,
    tool_auth_token: str | None = None,
) -> studio.ExecuteResult:
    """Ask the Draft agent for challenge wording. Never raises for configuration gaps."""
    agent_id = studio.resolve_kompass_agent_id(HUB_AGENT_KEY)
    if not agent_id:
        return studio.ExecuteResult(
            success=False,
            error="AISTUDIO_AGENT_IDEATHON_DRAFT is not set; the Draft agent cannot run.",
        )
    return await studio.execute_run(
        agent_id=agent_id,
        input_payload=build_draft_input(theme, existing),
        tool_auth_token=tool_auth_token,
    )
