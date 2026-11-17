"""Notion docs provider — internal integration token (MVP).

Auth: ``Authorization: Bearer <integration_secret>`` plus ``Notion-Version``.
Create a Notion internal integration at https://www.notion.so/my-integrations,
share the target page/database with that integration, then paste the secret
under Integrations → Notion.

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

_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?"
    r"[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}"
)


class NotionProvider:
    """Docs adapter that satisfies the TrackerProvider protocol for connect/link."""

    id = "notion"
    display_name = "Notion"
    description = (
        "Create or link Notion pages (or database rows) from accepted ideas. "
        "Use an internal integration secret from Notion → My integrations."
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
                "integrations → New integration → copy Internal Integration Secret."
            ),
        ),
        ConnectField(
            key="parent_page_id",
            label="Default parent page ID",
            required=False,
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            help_text=(
                "Page where new idea pages are created. Share the page with "
                "your integration first. Leave empty if you only use a database."
            ),
        ),
        ConnectField(
            key="database_id",
            label="Default database ID",
            required=False,
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            help_text=(
                "Optional. When set, new items are rows in this database "
                "(share the database with the integration)."
            ),
        ),
        ConnectField(
            key="title_property",
            label="Database title property",
            required=False,
            placeholder="Name",
            help_text=(
                "Title column name when creating database rows (default: Name)."
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
                "Provide a default parent page ID and/or database ID "
                "(share it with the integration in Notion)."
            )

        headers = _headers(token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            me = await client.get(f"{_API}/users/me", headers=headers)
            if me.status_code == 401:
                raise ValueError("Notion integration secret was rejected.")
            if me.status_code >= 400:
                raise ValueError(f"Notion auth failed: {_safe_detail(me)}")
            me_data = me.json()
            bot = me_data if isinstance(me_data, dict) else {}
            bot_name = str(bot.get("name") or "").strip()
            if not bot_name:
                bot_obj = bot.get("bot") if isinstance(bot.get("bot"), dict) else {}
                owner = (
                    bot_obj.get("owner")
                    if isinstance(bot_obj.get("owner"), dict)
                    else {}
                )
                user = (
                    owner.get("user") if isinstance(owner.get("user"), dict) else {}
                )
                bot_name = str(user.get("name") or "Notion integration").strip()

            target_label = ""
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
                target_label = _plain_title(db_data.get("title")) or database_id
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
                if target_label:
                    target_label = f"{target_label} · {page_title}"
                else:
                    target_label = page_title

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

        database_id = _normalize_uuid(
            payload.extra.get("database_id")
            or credentials.get("database_id")
            or ""
        )
        parent_page_id = _normalize_uuid(
            payload.extra.get("parent_page_id")
            or credentials.get("parent_page_id")
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
        description = (payload.description or "").strip()
        if payload.idea_url:
            if description:
                description = f"{description}\n\n{payload.idea_url}"
            else:
                description = payload.idea_url

        if database_id:
            body: dict[str, Any] = {
                "parent": {"database_id": database_id},
                "properties": {
                    title_property: {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
            }
        elif parent_page_id:
            body = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
            }
        else:
            raise ValueError(
                "Notion create needs a parent_page_id or database_id on the "
                "connection."
            )

        if description:
            # Keep first block short — Notion rich_text content max 2000 chars.
            body["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": description[:1900]},
                            }
                        ]
                    },
                }
            ]

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
            raw=data if isinstance(data, dict) else {},
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
            editable_fields=["title"],
            raw=data if isinstance(data, dict) else {},
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
        if payload.title is None:
            raise ValueError("Notion update supports title only for MVP.")
        title = (payload.title or "").strip()
        if not title:
            raise ValueError("Notion title cannot be empty.")

        # Resolve which property holds the title (page vs database row).
        headers = _headers(token)
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                            {"type": "text", "text": {"content": title[:2000]}}
                        ]
                    }
                }
            }
            resp = await client.patch(
                f"{_API}/pages/{page_id}", headers=headers, json=body
            )
            if resp.status_code >= 400:
                raise ValueError(f"Notion update failed: {_safe_detail(resp)}")
        return await self.get_task(credentials, page_id)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
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
        text = block.get("text") if isinstance(block.get("text"), dict) else {}
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
