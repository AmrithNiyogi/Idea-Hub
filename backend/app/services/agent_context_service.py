"""Build KonnektIdea → coding-agent handoff packs.

Responsibilities:
- Assemble idea, status history, latest decision, comments, and delivery
  summary into a structured + markdown payload for Cursor / Claude Code.
- Redact anonymous authorship and never emit emails, tokens, or secrets.

Collaborators:
- ``idea_service.get_idea`` / ``list_comments``
- ``DeliveryRepository.get_project_by_idea``
- ``Category``, ``User``, ``Decision`` ORM reads

Side Effects:
- Read-only; no writes.

Must never:
- Include SMTP/JWT/OTP material or user email addresses in prompts.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.review import Decision
from app.models.user import User
from app.repositories.delivery_repository import DeliveryRepository
from app.schemas.agent_context import (
    AgentCategoryRef,
    AgentCommentHighlight,
    AgentCommentsSummary,
    AgentContextOut,
    AgentDecisionSummary,
    AgentDeliverySummary,
    AgentPersonRef,
    AgentPrompts,
    AgentRelatedLink,
    AgentSkillPack,
    AgentStatusEvent,
)
from app.config.settings import settings
from app.services import agent_skill_pack, idea_service

_COMMENT_CAP = 8
_COMMENT_BODY_MAX = 280
_OPEN_TASK_CAP = 8
_IDEA_HUB_REPO_HINT = "/home/nakula/Desktop/DotKonnekt/REPOS/Idea-Hub"
_SKILL_ZIP_URL = f"{settings.API_PREFIX}/agent-handoff/skill-pack.zip"


def _truncate(text: str, max_len: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.isoformat()


def _person(user: User | None) -> AgentPersonRef | None:
    if user is None:
        return None
    return AgentPersonRef(id=user.id, name=user.name)


async def _load_users(
    session: AsyncSession, ids: set[uuid.UUID]
) -> dict[uuid.UUID, User]:
    if not ids:
        return {}
    result = await session.execute(select(User).where(User.id.in_(ids)))
    return {u.id: u for u in result.scalars().all()}


def _render_markdown(ctx: AgentContextOut) -> str:
    """Render the downloadable context.md from structured fields."""
    lines: list[str] = [
        f"# Idea: {ctx.title}",
        "",
        f"- **ID:** `{ctx.idea_id}`",
    ]
    if ctx.slug:
        lines.append(f"- **Slug:** `{ctx.slug}`")
    lines.append(f"- **Status:** `{ctx.status}`")
    if ctx.category:
        lines.append(f"- **Category:** {ctx.category.label} (`{ctx.category.slug}`)")
    lines.append(f"- **Effort:** `{ctx.effort}`")
    if ctx.tags:
        lines.append(f"- **Tags:** {', '.join(f'`{t}`' for t in ctx.tags)}")
    if ctx.anonymous:
        lines.append("- **Author:** Anonymous (identity redacted)")
    elif ctx.author:
        lines.append(f"- **Author:** {ctx.author.name}")
    if ctx.owner:
        lines.append(f"- **Owner:** {ctx.owner.name}")
    lines.extend(["", "## Problem", "", ctx.problem or "_(empty)_", ""])
    lines.extend(["## Solution", "", ctx.solution or "_(empty)_", ""])
    lines.extend(["## Beneficiaries", "", ctx.beneficiaries or "_(empty)_", ""])
    lines.extend(
        ["## Success metrics", "", ctx.success_metrics or "_(empty)_", ""]
    )

    lines.extend(["## Decision history", ""])
    if not ctx.status_history:
        lines.append("_No status transitions recorded._")
        lines.append("")
    else:
        for ev in ctx.status_history:
            fr = ev.from_status or "—"
            reason = f" — {ev.reason}" if ev.reason else ""
            lines.append(
                f"- `{_iso(ev.at)}`: `{fr}` → `{ev.to_status}`{reason}"
            )
        lines.append("")

    if ctx.latest_decision:
        d = ctx.latest_decision
        lines.extend(
            [
                "## Latest decision",
                "",
                f"- **Outcome:** `{d.outcome}` (as `{d.as_role}`)",
                f"- **At:** `{_iso(d.at)}`",
                f"- **Reason:** {d.reason}",
            ]
        )
        if d.hours is not None:
            lines.append(f"- **Hours recommended:** {d.hours}")
        if d.question:
            lines.append(f"- **Question:** {d.question}")
        if d.change_mind:
            lines.append(f"- **What would change our mind:** {d.change_mind}")
        lines.append("")

    lines.extend(
        [
            "## Comments summary",
            "",
            f"- **Count:** {ctx.comments.count}",
        ]
    )
    if ctx.comments.highlights:
        lines.append("")
        for h in ctx.comments.highlights:
            who = h.author_name or "Someone"
            lines.append(f"- ({h.kind}, `{_iso(h.at)}`) **{who}:** {h.body}")
    lines.append("")

    if ctx.delivery:
        d = ctx.delivery
        lines.extend(
            [
                "## Delivery",
                "",
                f"- **Hours granted:** {d.hours_granted}",
                f"- **Tasks:** {d.task_done}/{d.task_total} done",
            ]
        )
        if d.started_at:
            lines.append(f"- **Started:** `{_iso(d.started_at)}`")
        if d.implemented_at:
            lines.append(f"- **Implemented:** `{_iso(d.implemented_at)}`")
        if d.outcome:
            lines.append(f"- **Outcome notes:** {d.outcome}")
        if d.open_task_titles:
            lines.append("- **Open tasks:**")
            for t in d.open_task_titles:
                lines.append(f"  - {t}")
        lines.append("")

    if ctx.related_links:
        lines.extend(["## Related links", ""])
        for link in ctx.related_links:
            lines.append(f"- [{link.label}]({link.href})")
        lines.append("")

    lines.extend(["## Build with an agent", ""])
    _, _, skill_summary = agent_skill_pack.install_instructions(
        api_base=ctx.api_base_url
    )
    lines.append(skill_summary.rstrip())
    lines.append("")
    lines.extend(
        [
            f"- **Idea ID:** `{ctx.idea_id}`",
            f"- **API:** `GET {ctx.api_base_url}{settings.API_PREFIX}/ideas/"
            f"{ctx.idea_id}/agent-context`",
            f"- **Skill zip (auth):** `{ctx.skill.zip_url}` "
            "(KonnektIdea UI: **Download skill**)",
            "",
        ]
    )

    lines.extend(
        [
            "---",
            "",
            "_Generated by KonnektIdea agent handoff. Do not include secrets, "
            "API keys, passwords, or OTP codes in follow-up prompts._",
            "",
        ]
    )
    return "\n".join(lines)


def _cursor_prompt(markdown: str, idea_id: uuid.UUID, api_base: str) -> str:
    return (
        "You are helping implement an KonnektIdea idea in Cursor.\n\n"
        f"**Idea ID:** `{idea_id}`\n"
        f"**API base:** `{api_base}`\n"
        f"**Re-fetch:** `GET {api_base}{settings.API_PREFIX}/ideas/"
        f"{idea_id}/agent-context` "
        "(session cookie or `Authorization: Bearer`).\n\n"
        "### How to use this paste\n"
        "- This prompt **already includes the full context pack** — start from it.\n"
        "- Do **not** block on installing a skill. Optional skill "
        f"`{agent_skill_pack.SKILL_NAME}` can re-fetch later if the user "
        "installed it (Download skill in KonnektIdea → extract at repo root).\n"
        f"- Env for the skill: `IDEA_HUB_API_URL={api_base}`.\n\n"
        "### Repo guidance\n"
        f"- Default KonnektIdea repo path hint: `{_IDEA_HUB_REPO_HINT}` "
        "(adjust if your checkout differs).\n"
        "- If the user pastes a **target product repo** path or URL, "
        "implement there instead of KonnektIdea itself.\n"
        "- Prefer additive changes; match existing architecture and tokens.\n"
        "- Never invent secrets; use `.env.example` placeholders only.\n\n"
        "### Task\n"
        "1. Read the context pack below.\n"
        "2. Clarify scope only if critical info is missing.\n"
        "3. Propose a short implementation plan, then start building.\n\n"
        "### Context pack\n\n"
        f"{markdown}"
    )


def _claude_prompt(markdown: str, idea_id: uuid.UUID, api_base: str) -> str:
    return (
        "You are Claude Code implementing an KonnektIdea idea.\n\n"
        f"**Idea ID:** `{idea_id}`\n"
        f"**API base:** `{api_base}`\n"
        f"**Re-fetch:** `GET {api_base}{settings.API_PREFIX}/ideas/"
        f"{idea_id}/agent-context` "
        "(session cookie or `Authorization: Bearer`).\n\n"
        "### How to use this paste\n"
        "- Full context is **embedded below** — begin implementing from it.\n"
        "- Skill install is optional; only needed to re-pull live context.\n"
        f"- If skill `{agent_skill_pack.SKILL_NAME}` is present under "
        f"`.claude/skills/{agent_skill_pack.SKILL_NAME}/`, you may use it "
        f"with this idea id. Set `IDEA_HUB_API_URL={api_base}`.\n\n"
        "### Repo guidance\n"
        f"- Default KonnektIdea checkout hint: `{_IDEA_HUB_REPO_HINT}`.\n"
        "- Read `CLAUDE.md` / project instructions if present and follow them.\n"
        "- If the user names a different product repo, work in that repo.\n"
        "- Keep secrets out of commits and prompts; use env examples only.\n\n"
        "### Task\n"
        "1. Ingest the context pack.\n"
        "2. Outline the smallest viable change set.\n"
        "3. Implement against the stated problem/solution and success metrics.\n\n"
        "### Context pack\n\n"
        f"{markdown}"
    )


def _build_skill_pack() -> AgentSkillPack:
    """Load skill markdown + install copy for the agent-context payload."""
    try:
        skill_md = agent_skill_pack.load_skill_markdown()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent skill pack missing: {exc}",
        ) from exc
    cursor, claude, _ = agent_skill_pack.install_instructions()
    return AgentSkillPack(
        name=agent_skill_pack.SKILL_NAME,
        skill_markdown=skill_md,
        install_cursor=cursor,
        install_claude=claude,
        zip_url=_SKILL_ZIP_URL,
    )


async def build_agent_context(
    session: AsyncSession,
    idea_id: uuid.UUID,
) -> AgentContextOut:
    """Assemble structured + markdown agent context for one idea.

    Args:
        session (AsyncSession): Active DB session.
        idea_id (uuid.UUID): Target idea primary key.

    Returns:
        AgentContextOut: Structured fields, markdown, and tool prompts.

    Raises:
        HTTPException: 404 when the idea is missing or still a private draft.
    """
    idea = await idea_service.get_idea(session, idea_id, with_history=True)
    if idea is None or idea.status == "draft":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Idea not found"
        )

    category: Category | None = None
    if idea.category_id:
        category = await session.get(Category, idea.category_id)

    decision_row = (
        await session.execute(
            select(Decision)
            .where(Decision.idea_id == idea.id)
            .order_by(Decision.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    comments = await idea_service.list_comments(session, idea.id)

    user_ids: set[uuid.UUID] = set()
    if not idea.anonymous:
        user_ids.add(idea.author_id)
    if idea.owner_id:
        user_ids.add(idea.owner_id)
    for c in comments[-_COMMENT_CAP:]:
        user_ids.add(c.author_id)
    users = await _load_users(session, user_ids)

    history_sorted = sorted(
        idea.status_history or [], key=lambda h: h.at
    )
    status_events = [
        AgentStatusEvent(
            from_status=h.from_status,
            to_status=h.to_status,
            at=h.at,
            reason=h.reason or "",
        )
        for h in history_sorted
    ]

    latest_decision: AgentDecisionSummary | None = None
    if decision_row is not None:
        latest_decision = AgentDecisionSummary(
            outcome=decision_row.outcome,
            reason=decision_row.reason,
            at=decision_row.created_at,
            as_role=decision_row.as_role,
            hours=decision_row.hours,
            question=decision_row.question or "",
            change_mind=decision_row.change_mind or "",
        )

    recent = comments[-_COMMENT_CAP:]
    highlights: list[AgentCommentHighlight] = []
    for c in recent:
        author_name: str | None = None
        if not idea.anonymous or c.author_id != idea.author_id:
            author_name = users.get(c.author_id).name if c.author_id in users else None
        if idea.anonymous and c.author_id == idea.author_id:
            author_name = "Anonymous author"
        highlights.append(
            AgentCommentHighlight(
                kind=c.kind,
                body=_truncate(c.body, _COMMENT_BODY_MAX),
                at=c.created_at,
                author_name=author_name,
            )
        )

    delivery_summary: AgentDeliverySummary | None = None
    project = await DeliveryRepository(session).get_project_by_idea(
        idea.id, with_children=True
    )
    if project is not None:
        tasks = list(project.tasks or [])

        def _task_done(t) -> bool:
            return t.status == "done" or t.done_at is not None

        open_titles = [t.title for t in tasks if not _task_done(t)][:_OPEN_TASK_CAP]
        delivery_summary = AgentDeliverySummary(
            hours_granted=project.hours_granted,
            started_at=project.started_at,
            implemented_at=project.implemented_at,
            outcome=project.outcome or "",
            task_total=len(tasks),
            task_done=sum(1 for t in tasks if _task_done(t)),
            open_task_titles=open_titles,
        )

    related_links = [
        AgentRelatedLink(label="Idea detail", href=f"/ideas/{idea.id}"),
        AgentRelatedLink(
            label="Discussion", href=f"/ideas/{idea.id}?tab=discussion"
        ),
        AgentRelatedLink(
            label="Decision history", href=f"/ideas/{idea.id}?tab=decision"
        ),
    ]
    if delivery_summary is not None:
        related_links.append(
            AgentRelatedLink(
                label="Delivery", href=f"/ideas/{idea.id}?tab=delivery"
            )
        )

    author = None if idea.anonymous else _person(users.get(idea.author_id))
    owner = _person(users.get(idea.owner_id)) if idea.owner_id else None

    api_base = agent_skill_pack.public_api_base()
    skill = _build_skill_pack()

    # Build without markdown/prompts first, then fill via renderer.
    draft = AgentContextOut(
        idea_id=idea.id,
        slug=idea.slug,
        title=idea.title,
        status=idea.status,
        category=(
            AgentCategoryRef(
                id=category.id, slug=category.slug, label=category.label
            )
            if category
            else None
        ),
        problem=idea.problem or "",
        solution=idea.solution or "",
        beneficiaries=idea.beneficiaries or "",
        success_metrics=idea.success_metrics or "",
        effort=idea.effort or "M",
        tags=list(idea.tags or []),
        anonymous=bool(idea.anonymous),
        author=author,
        owner=owner,
        status_history=status_events,
        latest_decision=latest_decision,
        comments=AgentCommentsSummary(
            count=len(comments), highlights=highlights
        ),
        delivery=delivery_summary,
        related_links=related_links,
        api_base_url=api_base,
        skill=skill,
        markdown="",  # filled below
        prompts=AgentPrompts(cursor="", claude=""),
    )
    markdown = _render_markdown(draft)
    draft.markdown = markdown
    draft.prompts = AgentPrompts(
        cursor=_cursor_prompt(markdown, idea.id, api_base),
        claude=_claude_prompt(markdown, idea.id, api_base),
    )
    return draft
