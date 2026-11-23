"""Authenticated downloads for KonnektIdea → coding-agent skill packs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.config.settings import settings
from app.dependencies.auth import RequireUser
from app.schemas.agent_context import AgentSkillPack
from app.services import agent_skill_pack

router = APIRouter(prefix="/agent-handoff", tags=["agent-handoff"])

_ZIP_PATH = f"{settings.API_PREFIX}/agent-handoff/skill-pack.zip"


def _skill_meta() -> AgentSkillPack:
    """Build skill metadata for JSON responses."""
    pack = agent_skill_pack.build_skill_pack_zip()
    cursor, claude, _ = agent_skill_pack.install_instructions()
    return AgentSkillPack(
        name=agent_skill_pack.SKILL_NAME,
        skill_markdown=pack.skill_markdown,
        install_cursor=cursor,
        install_claude=claude,
        zip_url=_ZIP_PATH,
    )


@router.get(
    "/skill",
    response_model=AgentSkillPack,
    summary="Agent skill pack metadata",
    description=(
        "Returns the idea-hub-pull-idea SKILL.md body plus Cursor/Claude "
        "install paths. Prefer Download skill (zip) for one-shot install."
    ),
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Skill assets missing from this deployment"},
    },
)
async def get_skill_pack(current: RequireUser) -> AgentSkillPack:
    """Return skill markdown and install instructions for copy/download UIs."""
    _ = current
    try:
        return _skill_meta()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get(
    "/skill-pack.zip",
    summary="Download agent skill zip",
    description=(
        "Zip that extracts `.cursor/skills/idea-hub-pull-idea/SKILL.md` and "
        "`.claude/skills/idea-hub-pull-idea/SKILL.md` at a repo root, plus README."
    ),
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Skill assets missing from this deployment"},
        200: {
            "content": {"application/zip": {}},
            "description": "Skill pack zip",
        },
    },
    response_class=Response,
)
async def download_skill_pack_zip(current: RequireUser) -> Response:
    """Stream the installable skill zip for Cursor and Claude Code."""
    _ = current
    try:
        pack = agent_skill_pack.build_skill_pack_zip()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return Response(
        content=pack.content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{pack.filename}"',
            "Cache-Control": "no-store",
        },
    )
