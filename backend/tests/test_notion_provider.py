"""Notion adapter unit tests (id parsing, connect fields, page-first blocks)."""

from __future__ import annotations

from app.integrations.notion import (
    NotionProvider,
    _blocks_from_markdown,
    _build_idea_blocks,
    _normalize_uuid,
    _parse_notion_page_id,
)
from app.trackers.base import CreateIssuePayload


def test_normalize_uuid_with_and_without_dashes() -> None:
    dashed = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    compact = dashed.replace("-", "")
    assert _normalize_uuid(dashed) == dashed
    assert _normalize_uuid(compact) == dashed


def test_parse_notion_page_id_from_url() -> None:
    page_id = "a1b2c3d4e5f67890abcdef1234567890"
    url = f"https://www.notion.so/Workspace-My-Idea-{page_id}"
    assert _parse_notion_page_id(url) == _normalize_uuid(page_id)


def test_parse_notion_page_id_raw() -> None:
    dashed = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert _parse_notion_page_id(dashed) == dashed


def test_notion_connect_fields_page_first() -> None:
    p = NotionProvider()
    assert p.id == "notion"
    assert p.integration_category == "docs"
    keys = [f.key for f in p.connect_fields]
    assert keys[0] == "integration_token"
    assert keys[1] == "parent_page_id"
    assert "database_id" in keys
    db = next(f for f in p.connect_fields if f.key == "database_id")
    assert db.advanced is True
    assert db.required is False
    title_prop = next(f for f in p.connect_fields if f.key == "title_property")
    assert title_prop.advanced is True
    assert "page" in p.description.lower() or "document" in p.description.lower()


def test_blocks_from_markdown_headings_and_bullets() -> None:
    blocks = _blocks_from_markdown(
        "## Problem\nCustomers wait too long.\n\n- Step one\n- Step two"
    )
    types = [b["type"] for b in blocks]
    assert "heading_2" in types
    assert "paragraph" in types
    assert types.count("bulleted_list_item") == 2


def test_build_idea_blocks_prefers_problem_solution() -> None:
    payload = CreateIssuePayload(
        title="Ship faster",
        description="ignored when structured fields present",
        idea_id="11111111-1111-1111-1111-111111111111",
        idea_url="http://localhost:5173/ideas/11111111-1111-1111-1111-111111111111",
        extra={
            "problem": "Slow handoffs",
            "solution": "Shared Notion docs",
        },
    )
    blocks = _build_idea_blocks(payload)
    types = [b["type"] for b in blocks]
    assert types.count("heading_2") >= 2
    plain = []
    for b in blocks:
        key = b["type"]
        rts = (b.get(key) or {}).get("rich_text") or []
        for rt in rts:
            plain.append(rt.get("plain_text") or rt.get("text", {}).get("content", ""))
    joined = " ".join(plain)
    assert "Problem" in joined
    assert "Slow handoffs" in joined
    assert "Solution" in joined
    assert "Shared Notion docs" in joined
    assert "IdeaKonnekt" in joined
