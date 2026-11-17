"""Ship the Idea Hub → agent skill pack for end-user install.

Responsibilities:
- Locate the canonical ``idea-hub-pull-idea`` SKILL.md (API assets first).
- Build install instructions for Cursor and Claude Code skill paths.
- Produce a zip that extracts into both tool skill directories at a repo root.

Collaborators:
- ``app.config.settings`` for the public API base hint used in prompts.

Must never:
- Embed SMTP/JWT/OTP secrets into skill text or zip contents.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.config.settings import settings

SKILL_NAME = "idea-hub-pull-idea"
_SKILL_FILENAME = "SKILL.md"
_ZIP_FILENAME = "idea-hub-pull-idea-skill.zip"


def _repo_root() -> Path:
    """Return the Idea Hub checkout root (parent of ``backend/``)."""
    # backend/app/services/this_file.py → parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def _asset_skill_path() -> Path:
    """Packaged skill shipped with the API (works without a full git tree)."""
    return (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "agent_skills"
        / SKILL_NAME
        / _SKILL_FILENAME
    )


def resolve_skill_markdown_path() -> Path:
    """Resolve SKILL.md from assets, then repo Cursor/Claude skill mirrors.

    Returns:
        Path: Absolute path to an existing SKILL.md.

    Raises:
        FileNotFoundError: When no skill file can be located.
    """
    candidates = [
        _asset_skill_path(),
        _repo_root() / ".cursor" / "skills" / SKILL_NAME / _SKILL_FILENAME,
        _repo_root() / ".claude" / "skills" / SKILL_NAME / _SKILL_FILENAME,
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"Skill {SKILL_NAME} not found in assets or repo skill dirs"
    )


def load_skill_markdown() -> str:
    """Read the canonical skill markdown body.

    Returns:
        str: Full SKILL.md contents (UTF-8).

    Raises:
        FileNotFoundError: When the skill file is missing.
        OSError: When the file cannot be read.
    """
    return resolve_skill_markdown_path().read_text(encoding="utf-8")


def public_api_base() -> str:
    """Public API origin for agent prompts (no trailing slash).

    Prefers ``PUBLIC_API_URL``, then falls back to local uvicorn default.
    """
    raw = (settings.PUBLIC_API_URL or "").strip().rstrip("/")
    return raw or "http://127.0.0.1:8000"


def install_instructions(*, api_base: str | None = None) -> tuple[str, str, str]:
    """Build Cursor / Claude / summary install copy for UI and context.md.

    Args:
        api_base (str | None): Optional API origin override.

    Returns:
        tuple[str, str, str]: ``(cursor_path_help, claude_path_help, summary_md)``.
    """
    base = api_base or public_api_base()
    cursor = (
        f"Extract the skill pack at your target repo root so the file exists at "
        f"`.cursor/skills/{SKILL_NAME}/SKILL.md` "
        f"(Cursor project skills). Set `IDEA_HUB_API_URL={base}`."
    )
    claude = (
        f"Extract the same pack at the repo root so "
        f"`.claude/skills/{SKILL_NAME}/SKILL.md` exists "
        f"(Claude Code skills). Set `IDEA_HUB_API_URL={base}`."
    )
    summary = "\n".join(
        [
            f"### Optional skill: `{SKILL_NAME}`",
            "",
            "The context pack below is **self-contained** — paste a Cursor/Claude "
            "prompt to start building without installing anything.",
            "",
            "To re-fetch live context later, install the skill from Idea Hub "
            "(**Build with an agent → Download skill**), then extract at the "
            "target repo root:",
            "",
            f"- **Cursor:** `.cursor/skills/{SKILL_NAME}/SKILL.md`",
            f"- **Claude Code:** `.claude/skills/{SKILL_NAME}/SKILL.md`",
            "",
            f"Env: `IDEA_HUB_API_URL={base}` (or `VITE_API_BASE_URL`).",
            "",
            f"Then ask the agent to use skill `{SKILL_NAME}` with the idea UUID.",
            "",
        ]
    )
    return cursor, claude, summary


@dataclass(frozen=True)
class SkillPackBytes:
    """In-memory zip artifact for HTTP download."""

    filename: str
    content: bytes
    skill_markdown: str


def build_skill_pack_zip() -> SkillPackBytes:
    """Build a zip that installs the skill for both Cursor and Claude Code.

    Zip layout (extract at repo root):

    - ``README.md`` — human install steps
    - ``.cursor/skills/idea-hub-pull-idea/SKILL.md``
    - ``.claude/skills/idea-hub-pull-idea/SKILL.md``

    Returns:
        SkillPackBytes: Filename, zip bytes, and raw skill markdown.

    Raises:
        FileNotFoundError: When SKILL.md cannot be resolved.
    """
    skill_md = load_skill_markdown()
    base = public_api_base()
    cursor_help, claude_help, _ = install_instructions(api_base=base)
    readme = "\n".join(
        [
            f"# {SKILL_NAME} skill pack",
            "",
            "Extract this archive at the **root of the repo** where you want "
            "the coding agent to work (Idea Hub or your product repo).",
            "",
            "## Cursor",
            "",
            cursor_help,
            "",
            "## Claude Code",
            "",
            claude_help,
            "",
            "## After install",
            "",
            f"Ask the agent: use skill `{SKILL_NAME}` with idea `<uuid>` "
            f"or idea URL. Auth: browser session cookie or "
            f"`Authorization: Bearer <token>` against `{base}`.",
            "",
            "Never put SMTP passwords, JWT secrets, or OTP codes into prompts.",
            "",
        ]
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", readme)
        zf.writestr(f".cursor/skills/{SKILL_NAME}/{_SKILL_FILENAME}", skill_md)
        zf.writestr(f".claude/skills/{SKILL_NAME}/{_SKILL_FILENAME}", skill_md)
    return SkillPackBytes(
        filename=_ZIP_FILENAME,
        content=buf.getvalue(),
        skill_markdown=skill_md,
    )
