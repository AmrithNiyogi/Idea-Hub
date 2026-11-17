"""Smoke tests for agent skill pack + handoff zip."""

from __future__ import annotations

import zipfile
from io import BytesIO

from app.services import agent_skill_pack


def test_load_skill_markdown_from_assets() -> None:
    text = agent_skill_pack.load_skill_markdown()
    assert "idea-hub-pull-idea" in text
    assert "agent-context" in text


def test_build_skill_pack_zip_has_both_tool_paths() -> None:
    pack = agent_skill_pack.build_skill_pack_zip()
    assert pack.filename.endswith(".zip")
    assert "idea-hub-pull-idea" in pack.skill_markdown
    with zipfile.ZipFile(BytesIO(pack.content)) as zf:
        names = set(zf.namelist())
    assert "README.md" in names
    assert ".cursor/skills/idea-hub-pull-idea/SKILL.md" in names
    assert ".claude/skills/idea-hub-pull-idea/SKILL.md" in names


def test_install_instructions_include_api_base() -> None:
    cursor, claude, summary = agent_skill_pack.install_instructions(
        api_base="http://example.test:8000"
    )
    assert "IDEA_HUB_API_URL=http://example.test:8000" in cursor
    assert ".claude/skills/idea-hub-pull-idea" in claude
    assert "Download skill" in summary
