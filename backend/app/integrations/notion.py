"""Notion docs provider — internal integration token (MVP).

Primary path: create / update **pages (documents)** under a parent page,
with title + body blocks from the idea (problem / solution / markdown).

Database row create remains an optional advanced path when only a database
is shared with the integration.

Auth: ``Authorization: Bearer <integration_secret>`` plus ``Notion-Version``.
Create a Notion internal integration at https://www.notion.so/my-integrations,
share the target page (or database) with that integration, then paste the
secret under Integrations → Notion.

Optional OAuth app env (``NOTION_CLIENT_ID`` / ``NOTION_CLIENT_SECRET``) is
reserved for a later authorization-code flow; MVP uses the internal secret.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.trackers.base import (
    ConnectField,
    ConnectionProbe,
    CreateIssuePayload,
    ExternalIssue,
    RemoteTask,
    UpdateTaskPayload,
)
from app.utils.jsonish import as_dict

_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?"
    r"[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}"
)
_MAX_RICH = 1900
_MAX_CHILDREN = 100


class NotionProvider:
    """Docs adapter that satisfies the TrackerProvider protocol for connect/link."""

    id = "notion"
    display_name = "Notion"
    description = (
        "Create Notion pages (documents) from ideas — title, problem, and "
        "solution as page content under a parent page. Database rows are "
        "optional. Use an internal integration secret from Notion → My "
        "integrations."
    )
    auth_mode = "api_token"
    integration_category = "docs"
    connect_fields = [
        ConnectField(
            key="integration_token",
            label="Internal integration secret",
            secret=True,
            placeholder="secret_…",
            help_text=(
                "Notion → Settings → Connections → Develop or manage "
                "integrations → New integration → copy Internal Integration "
                "Secret."
            ),
        ),
        ConnectField(
            key="parent_page_id",
            label="Parent page ID",
            required=False,
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            help_text=(
                "Primary: new idea documents are created as child pages under "
                "this page. Share the page with your integration (••• → "
                "Connections), then paste the page ID from the URL."
            ),
        ),
        ConnectField(
            key="database_id",
            label="Database ID",
            required=False,
            advanced=True,
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            help_text=(
                "Advanced / optional. Only needed if you want new items as "
                "database rows instead of (or in addition to) pages. Share "
                "the database with the integration first."
            ),
        ),
        ConnectField(
            key="title_property",
            label="Database title property",
            required=False,
            advanced=True,
            placeholder="Name",
            help_text=(
                "Advanced: title column name when creating database rows "
                "(default: Name)."
            ),
        ),
    ]

    async def validate_connection(
        self, credentials: dict[str, Any]
    ) -> ConnectionProbe:
        token = (credentials.get("integration_token") or "").strip()
        if not token:
            raise ValueError("Notion requires an internal integration secret.")
        parent_page_id = _normalize_uuid(
            credentials.get("parent_page_id") or ""
        )
        database_id = _normalize_uuid(credentials.get("database_id") or "")
        if not parent_page_id and not database_id:
            raise ValueError(
                "Provide a parent page ID (recommended for documents) "
                "and/or a database ID — share it with the integration in Notion."
            )

        headers = _headers(token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            me = await client.get(f"{_API}/users/me", headers=headers)
            if me.status_code == 401:
                raise ValueError("Notion integration secret was rejected.")
            if me.status_code >= 400:
                raise ValueError(f"Notion auth failed: {_safe_detail(me)}")
            me_data = me.json()
            bot = as_dict(me_data)
            bot_name = str(bot.get("name") or "").strip()
            if not bot_name:
                bot_obj = as_dict(bot.get("bot"))
                owner = (
                    as_dict(bot_obj.get("owner"))
                )
                user = (
                    as_dict(owner.get("user"))
                )
                bot_name = str(user.get("name") or "Notion integration").strip()

            target_label = ""
            # Probe parent page first (document-centric).
            if parent_page_id:
                page = await client.get(
                    f"{_API}/pages/{parent_page_id}", headers=headers
                )
                if page.status_code == 404:
                    raise ValueError(
                        "Notion parent page not found — share it with the "
                        "integration and check the ID."
                    )
                if page.status_code >= 400:
                    raise ValueError(
                        f"Notion page probe failed: {_safe_detail(page)}"
                    )
                page_data = page.json() or {}
                page_title = _page_title_from_properties(
                    page_data.get("properties") or {}
                ) or parent_page_id
                target_label = page_title
            if database_id:
                db = await client.get(
                    f"{_API}/databases/{database_id}", headers=headers
                )
                if db.status_code == 404:
                    raise ValueError(
                        "Notion database not found — share it with the "
                        "integration and check the ID."
                    )
                if db.status_code >= 400:
                    raise ValueError(
                        f"Notion database probe failed: {_safe_detail(db)}"
                    )
                db_data = db.json() or {}
                db_title = _plain_title(db_data.get("title")) or database_id
                if target_label:
                    target_label = f"{target_label} · db:{db_title}"
                else:
                    target_label = f"db:{db_title}"

        label = f"{bot_name} · {target_label}" if target_label else str(bot_name)
        return ConnectionProbe(
            display_label=label[:255],
            external_account_id=str(
                (bot.get("id") if isinstance(bot, dict) else "") or ""
            ),
            meta={
                "parent_page_id": parent_page_id,
                "database_id": database_id,
                "title_property": (
                    (credentials.get("title_property") or "Name").strip()
                    or "Name"
                ),
                "mode": "page" if parent_page_id else "database",
            },
        )

    async def create_issue(
        self,
        credentials: dict[str, Any],
        payload: CreateIssuePayload,
    ) -> ExternalIssue:
        token = (credentials.get("integration_token") or "").strip()
        if not token:
            raise ValueError("Notion requires an internal integration secret.")

        parent_page_id = _normalize_uuid(
            payload.extra.get("parent_page_id")
            or credentials.get("parent_page_id")
            or ""
        )
        database_id = _normalize_uuid(
            payload.extra.get("database_id")
            or credentials.get("database_id")
            or ""
        )
        title_property = (
            (
                payload.extra.get("title_property")
                or credentials.get("title_property")
                or "Name"
            )
            .strip()
            or "Name"
        )
        title = (payload.title or "Idea").strip()[:2000]
        force_database = bool(payload.extra.get("as_database_row"))

        # Document-first: prefer child page under parent unless explicitly
        # requested as a database row, or only a database is configured.
        if parent_page_id and not force_database:
            body: dict[str, Any] = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
            }
        elif database_id:
            body = {
                "parent": {"database_id": database_id},
                "properties": {
                    title_property: {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
            }
        else:
            raise ValueError(
                "Notion create needs a parent_page_id (for documents) or "
                "database_id on the connection."
            )

        children = _build_idea_blocks(payload)
        if children:
            body["children"] = children[:_MAX_CHILDREN]

        headers = _headers(token)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_API}/pages", headers=headers, json=body
            )
            if resp.status_code >= 400:
                raise ValueError(f"Notion create failed: {_safe_detail(resp)}")
            data = resp.json() or {}

        page_id = str(data.get("id") or "")
        url = str(data.get("url") or "")
        if not page_id:
            raise ValueError("Notion response missing page id.")
        if not url:
            url = f"https://www.notion.so/{page_id.replace('-', '')}"
        return ExternalIssue(
            external_id=page_id,
            url=url,
            key=page_id,
            raw=as_dict(data),
        )

    async def resolve_existing(
        self,
        credentials: dict[str, Any],
        external_id_or_url: str,
    ) -> ExternalIssue:
        remote = await self.get_task(credentials, external_id_or_url)
        return ExternalIssue(
            external_id=remote.external_id,
            url=remote.url,
            key=remote.key or remote.external_id,
            raw=remote.raw,
        )

    async def get_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
    ) -> RemoteTask:
        token = (credentials.get("integration_token") or "").strip()
        page_id = _parse_notion_page_id(external_id)
        if not token or not page_id:
            raise ValueError("Provide a Notion page id or Notion page URL.")
        headers = _headers(token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{_API}/pages/{page_id}", headers=headers)
            if resp.status_code == 404:
                raise ValueError(f"Notion page {page_id} was not found.")
            if resp.status_code >= 400:
                raise ValueError(f"Notion lookup failed: {_safe_detail(resp)}")
            data = resp.json() or {}
        title = _page_title_from_properties(data.get("properties") or {})
        url = str(data.get("url") or "")
        if not url:
            url = f"https://www.notion.so/{page_id.replace('-', '')}"
        archived = bool(data.get("archived"))
        return RemoteTask(
            external_id=page_id,
            title=title,
            status="archived" if archived else "open",
            status_id="archived" if archived else "open",
            url=url,
            key=page_id,
            editable_fields=["title", "append_content"],
            raw=as_dict(data),
        )

    async def update_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask:
        token = (credentials.get("integration_token") or "").strip()
        page_id = _parse_notion_page_id(external_id)
        if not token or not page_id:
            raise ValueError("Provide a Notion page id or Notion page URL.")

        append_raw = ""
        if payload.extra:
            append_raw = str(
                payload.extra.get("append_content")
                or payload.extra.get("content")
                or ""
            ).strip()

        headers = _headers(token)
        async with httpx.AsyncClient(timeout=30.0) as client:
            if payload.title is not None:
                title = (payload.title or "").strip()
                if not title:
                    raise ValueError("Notion title cannot be empty.")
                current = await client.get(
                    f"{_API}/pages/{page_id}", headers=headers
                )
                if current.status_code >= 400:
                    raise ValueError(
                        f"Notion lookup failed: {_safe_detail(current)}"
                    )
                cur = current.json() or {}
                prop_name = _title_property_name(cur.get("properties") or {})
                if not prop_name:
                    prop_name = (
                        (credentials.get("title_property") or "Name").strip()
                        or "Name"
                    )
                body = {
                    "properties": {
                        prop_name: {
                            "title": [
                                {
                                    "type": "text",
                                    "text": {"content": title[:2000]},
                                }
                            ]
                        }
                    }
                }
                resp = await client.patch(
                    f"{_API}/pages/{page_id}", headers=headers, json=body
                )
                if resp.status_code >= 400:
                    raise ValueError(
                        f"Notion update failed: {_safe_detail(resp)}"
                    )

            if append_raw:
                blocks = _blocks_from_markdown(append_raw)[:_MAX_CHILDREN]
                if not blocks:
                    raise ValueError("Nothing to append to the Notion page.")
                # Notion accepts at most 100 children per request.
                for i in range(0, len(blocks), _MAX_CHILDREN):
                    chunk = blocks[i : i + _MAX_CHILDREN]
                    resp = await client.patch(
                        f"{_API}/blocks/{page_id}/children",
                        headers=headers,
                        json={"children": chunk},
                    )
                    if resp.status_code >= 400:
                        raise ValueError(
                            f"Notion append failed: {_safe_detail(resp)}"
                        )

            if payload.title is None and not append_raw:
                raise ValueError(
                    "Notion update supports title and/or append_content."
                )

        return await self.get_task(credentials, page_id)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _build_idea_blocks(payload: CreateIssuePayload) -> list[dict[str, Any]]:
    """Turn idea fields into Notion block children (page body)."""
    extra = payload.extra or {}
    problem = str(extra.get("problem") or "").strip()
    solution = str(extra.get("solution") or "").strip()
    description = (payload.description or "").strip()
    idea_url = (payload.idea_url or "").strip()

    blocks: list[dict[str, Any]] = []

    if problem:
        blocks.append(_heading_block("Problem"))
        blocks.extend(_blocks_from_markdown(problem))
    if solution:
        blocks.append(_heading_block("Solution"))
        blocks.extend(_blocks_from_markdown(solution))

    # Fallback: unstructured description when problem/solution absent.
    if not problem and not solution and description:
        # Strip a trailing idea URL if we will add it separately.
        body = description
        if idea_url and body.endswith(idea_url):
            body = body[: -len(idea_url)].rstrip()
        blocks.extend(_blocks_from_markdown(body))

    if idea_url:
        blocks.append(_heading_block("KonnektIdea"))
        blocks.append(
            _paragraph_block(
                idea_url,
                link_url=idea_url,
            )
        )

    return blocks[:_MAX_CHILDREN]


def _blocks_from_markdown(text: str) -> list[dict[str, Any]]:
    """Lightweight markdown → Notion blocks (headings, bullets, paragraphs)."""
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return []

    blocks: list[dict[str, Any]] = []
    for chunk in re.split(r"\n{2,}", raw):
        line = chunk.strip()
        if not line:
            continue
        lines = [ln.rstrip() for ln in line.split("\n") if ln.strip()]
        if not lines:
            continue

        # Single-line heading
        if len(lines) == 1:
            m = re.match(r"^(#{1,3})\s+(.+)$", lines[0])
            if m:
                level = min(len(m.group(1)), 3)
                blocks.append(_heading_block(m.group(2).strip(), level=level))
                continue
            if re.match(r"^[-*]\s+", lines[0]):
                blocks.append(
                    _bulleted_block(re.sub(r"^[-*]\s+", "", lines[0]).strip())
                )
                continue
            blocks.extend(_paragraph_chunks(lines[0]))
            continue

        # Multi-line: if all bullets, emit list; else one paragraph per line.
        if all(re.match(r"^[-*]\s+", ln) for ln in lines):
            for ln in lines:
                blocks.append(
                    _bulleted_block(re.sub(r"^[-*]\s+", "", ln).strip())
                )
            continue

        first = lines[0]
        hm = re.match(r"^(#{1,3})\s+(.+)$", first)
        if hm:
            level = min(len(hm.group(1)), 3)
            blocks.append(_heading_block(hm.group(2).strip(), level=level))
            rest = "\n".join(lines[1:]).strip()
            if rest:
                blocks.extend(_paragraph_chunks(rest))
            continue

        blocks.extend(_paragraph_chunks("\n".join(lines)))

    return blocks


def _paragraph_chunks(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    remaining = (text or "").strip()
    while remaining:
        piece, remaining = remaining[:_MAX_RICH], remaining[_MAX_RICH:]
        out.append(_paragraph_block(piece))
    return out


def _rich_text(content: str, *, link_url: str = "") -> list[dict[str, Any]]:
    piece = (content or "")[:_MAX_RICH]
    item: dict[str, Any] = {"type": "text", "text": {"content": piece}}
    if link_url:
        item["text"]["link"] = {"url": link_url[:2000]}
    return [item]


def _paragraph_block(
    content: str, *, link_url: str = ""
) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": _rich_text(content, link_url=link_url),
        },
    }


def _heading_block(content: str, *, level: int = 2) -> dict[str, Any]:
    level = 2 if level not in (1, 2, 3) else level
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text((content or "")[:_MAX_RICH])},
    }


def _bulleted_block(content: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": _rich_text((content or "")[:_MAX_RICH]),
        },
    }


def _normalize_uuid(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    # Accept 32-char hex without dashes.
    compact = raw.replace("-", "")
    if len(compact) == 32 and all(
        c in "0123456789abcdefABCDEF" for c in compact
    ):
        return (
            f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-"
            f"{compact[16:20]}-{compact[20:32]}"
        ).lower()
    m = _UUID_RE.search(raw)
    if not m:
        return raw
    return _normalize_uuid(m.group(0)) if "-" not in m.group(0) else m.group(0).lower()


def _parse_notion_page_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" in raw or "notion.so" in raw.lower():
        path = urlparse(raw).path.rstrip("/")
        # Notion URLs end with a 32-char hex id (often after a title slug).
        compact = re.sub(r"[^0-9a-fA-F]", "", path)
        if len(compact) >= 32:
            return _normalize_uuid(compact[-32:])
        m = _UUID_RE.search(path)
        if m:
            return _normalize_uuid(m.group(0))
        return ""
    return _normalize_uuid(raw)


def _plain_title(title_arr: Any) -> str:
    if not isinstance(title_arr, list):
        return ""
    parts: list[str] = []
    for block in title_arr:
        if not isinstance(block, dict):
            continue
        plain = block.get("plain_text")
        if plain:
            parts.append(str(plain))
            continue
        text = as_dict(block.get("text"))
        if text.get("content"):
            parts.append(str(text["content"]))
    return "".join(parts).strip()


def _page_title_from_properties(properties: dict[str, Any]) -> str:
    name = _title_property_name(properties)
    if not name:
        return ""
    prop = properties.get(name) or {}
    if not isinstance(prop, dict):
        return ""
    return _plain_title(prop.get("title"))


def _title_property_name(properties: dict[str, Any]) -> str:
    for key, prop in (properties or {}).items():
        if isinstance(prop, dict) and prop.get("type") == "title":
            return str(key)
    return ""


def _safe_detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            msg = data.get("message") or data.get("code") or data
            return str(msg)[:240]
    except Exception:  # noqa: BLE001
        pass
    return f"HTTP {resp.status_code}"
