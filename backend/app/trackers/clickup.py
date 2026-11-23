"""ClickUp tracker provider — personal API token + list id.

Auth: ``Authorization: <api_token>`` (ClickUp personal token).
Docs: https://developer.clickup.com/docs/authentication
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.trackers.base import (
    ConnectField,
    ConnectionProbe,
    CreateIssuePayload,
    ExternalIssue,
    RemoteAssignee,
    RemotePriorityOption,
    RemoteStatusOption,
    RemoteTask,
    UpdateTaskPayload,
)
from app.utils.jsonish import as_dict

_API = "https://api.clickup.com/api/v2"

# ClickUp PUT /task/{id} priority is an integer: 1 urgent … 4 low (null clears).
_CLICKUP_PRIORITIES: list[RemotePriorityOption] = [
    RemotePriorityOption(id="1", name="urgent", color="#f50000"),
    RemotePriorityOption(id="2", name="high", color="#ffcc00"),
    RemotePriorityOption(id="3", name="normal", color="#6fddff"),
    RemotePriorityOption(id="4", name="low", color="#d8d8d8"),
]
_CLICKUP_PRIORITY_BY_NAME = {p.name: int(p.id) for p in _CLICKUP_PRIORITIES}
_CLICKUP_PRIORITY_BY_ID = {p.id: p for p in _CLICKUP_PRIORITIES}
_EDITABLE = ["status", "title", "priority", "due_date", "assignees"]


class ClickUpProvider:
    id = "clickup"
    display_name = "ClickUp"
    description = (
        "Create tasks in a ClickUp list using a personal API token. "
        "Generate a token in ClickUp → Settings → Apps."
    )
    auth_mode = "api_token"
    connect_fields = [
        ConnectField(
            key="api_token",
            label="API token",
            secret=True,
            placeholder="pk_…",
            help_text="ClickUp personal API token.",
        ),
        ConnectField(
            key="list_id",
            label="Default list ID",
            placeholder="9012…",
            help_text="Numeric list id where new tasks are created.",
        ),
        ConnectField(
            key="team_id",
            label="Workspace (team) ID",
            required=False,
            placeholder="optional",
            help_text="Optional; used only for display / validation.",
        ),
    ]

    async def validate_connection(
        self, credentials: dict[str, Any]
    ) -> ConnectionProbe:
        token = (credentials.get("api_token") or "").strip()
        list_id = (credentials.get("list_id") or "").strip()
        if not token or not list_id:
            raise ValueError("ClickUp requires api_token and list_id.")
        headers = {"Authorization": token}
        async with httpx.AsyncClient(timeout=20.0) as client:
            me = await client.get(f"{_API}/user", headers=headers)
            if me.status_code == 401:
                raise ValueError("ClickUp API token was rejected.")
            me.raise_for_status()
            user = (me.json() or {}).get("user") or {}
            lst = await client.get(f"{_API}/list/{list_id}", headers=headers)
            if lst.status_code == 404:
                raise ValueError(f"ClickUp list {list_id} was not found.")
            if lst.status_code == 401:
                raise ValueError("ClickUp API token cannot access that list.")
            lst.raise_for_status()
            list_name = (lst.json() or {}).get("name") or list_id
        label = user.get("username") or user.get("email") or "ClickUp user"
        return ConnectionProbe(
            display_label=f"{label} · {list_name}",
            external_account_id=str(user.get("id") or ""),
            meta={"list_id": list_id, "list_name": list_name},
        )

    async def create_issue(
        self,
        credentials: dict[str, Any],
        payload: CreateIssuePayload,
    ) -> ExternalIssue:
        token = (credentials.get("api_token") or "").strip()
        list_id = (
            (payload.extra.get("list_id") or credentials.get("list_id") or "")
            .strip()
        )
        if not token or not list_id:
            raise ValueError("ClickUp requires api_token and list_id.")
        body = {
            "name": payload.title[:200],
            "description": payload.description,
            "tags": payload.tags[:20],
        }
        headers = {"Authorization": token, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_API}/list/{list_id}/task",
                headers=headers,
                json=body,
            )
            if resp.status_code >= 400:
                detail = _safe_detail(resp)
                raise ValueError(f"ClickUp create failed: {detail}")
            data = resp.json() or {}
        task_id = str(data.get("id") or "")
        url = str(data.get("url") or f"https://app.clickup.com/t/{task_id}")
        if not task_id:
            raise ValueError("ClickUp response missing task id.")
        return ExternalIssue(
            external_id=task_id,
            url=url,
            key=task_id,
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
        token = (credentials.get("api_token") or "").strip()
        task_id = _parse_clickup_task_id(external_id)
        if not token or not task_id:
            raise ValueError("Provide a ClickUp task id or task URL.")
        headers = {"Authorization": token}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{_API}/task/{task_id}", headers=headers)
            if resp.status_code == 404:
                raise ValueError(f"ClickUp task {task_id} was not found.")
            if resp.status_code >= 400:
                raise ValueError(f"ClickUp lookup failed: {_safe_detail(resp)}")
            data = resp.json() or {}
            list_id = str((data.get("list") or {}).get("id") or "")
            # Prefer the task's own list; fall back to connected default list.
            if not list_id:
                list_id = (credentials.get("list_id") or "").strip()
            options = await _fetch_list_statuses(client, headers, list_id)
            assignable = await _fetch_list_members(
                client,
                headers,
                list_id,
                team_id=(credentials.get("team_id") or "").strip(),
            )
        return _task_from_clickup(data, task_id, options, assignable)

    async def update_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask:
        token = (credentials.get("api_token") or "").strip()
        task_id = _parse_clickup_task_id(external_id)
        if not token or not task_id:
            raise ValueError("Provide a ClickUp task id or task URL.")
        body: dict[str, Any] = {}
        if payload.status is not None:
            # ClickUp PUT /task/{id} expects the status *name* string
            # (e.g. "in progress"), not the status UUID.
            status_name = (payload.status or "").strip()
            if not status_name:
                raise ValueError("ClickUp status cannot be empty.")
            body["status"] = status_name
        if payload.title is not None:
            title = (payload.title or "").strip()
            if not title:
                raise ValueError("ClickUp title cannot be empty.")
            body["name"] = title[:200]
        if payload.priority is not None:
            body["priority"] = _clickup_priority_value(payload.priority)
        if payload.due_date is not None:
            due_raw = (payload.due_date or "").strip()
            if not due_raw:
                body["due_date"] = None
                body["due_date_time"] = False
            else:
                body["due_date"] = _iso_date_to_ms(due_raw)
                body["due_date_time"] = False
        if payload.assignee_ids is not None:
            desired = {
                str(x).strip()
                for x in payload.assignee_ids
                if str(x).strip()
            }
            # Need current assignees to compute add/rem.
            headers_peek = {"Authorization": token}
            async with httpx.AsyncClient(timeout=20.0) as peek:
                cur = await peek.get(
                    f"{_API}/task/{task_id}", headers=headers_peek
                )
                if cur.status_code >= 400:
                    raise ValueError(
                        f"ClickUp lookup failed: {_safe_detail(cur)}"
                    )
                cur_data = cur.json() or {}
            current = {
                str(a.get("id") or "").strip()
                for a in (cur_data.get("assignees") or [])
                if isinstance(a, dict) and str(a.get("id") or "").strip()
            }
            add = sorted(desired - current)
            rem = sorted(current - desired)
            # ClickUp requires int user ids in add/rem arrays.
            body["assignees"] = {
                "add": [_as_clickup_user_id(x) for x in add],
                "rem": [_as_clickup_user_id(x) for x in rem],
            }
        if not body:
            raise ValueError("No ClickUp fields to update.")
        headers = {"Authorization": token, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{_API}/task/{task_id}",
                headers=headers,
                json=body,
            )
            if resp.status_code >= 400:
                raise ValueError(f"ClickUp update failed: {_safe_detail(resp)}")
            data = resp.json() or {}
            list_id = str((data.get("list") or {}).get("id") or "")
            if not list_id:
                list_id = (credentials.get("list_id") or "").strip()
            auth_h = {"Authorization": token}
            options = await _fetch_list_statuses(client, auth_h, list_id)
            assignable = await _fetch_list_members(
                client,
                auth_h,
                list_id,
                team_id=(credentials.get("team_id") or "").strip(),
            )
        return _task_from_clickup(data, task_id, options, assignable)


async def _fetch_list_statuses(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    list_id: str,
) -> list[RemoteStatusOption]:
    """Load allowed statuses for a ClickUp list (for the status picker).

    ClickUp stores per-list statuses. We read ``GET /list/{list_id}`` and map
    each entry's ``status`` string (what PUT expects) plus color/type for UI.
    """
    if not list_id:
        return []
    try:
        resp = await client.get(f"{_API}/list/{list_id}", headers=headers)
        if resp.status_code >= 400:
            return []
        data = resp.json() or {}
    except Exception:  # noqa: BLE001
        return []
    out: list[RemoteStatusOption] = []
    for row in data.get("statuses") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("status") or "").strip()
        if not name:
            continue
        out.append(
            RemoteStatusOption(
                id=str(row.get("id") or name),
                name=name,
                color=str(row.get("color") or ""),
                type=str(row.get("type") or ""),
            )
        )
    return out


def _task_from_clickup(
    data: dict[str, Any],
    fallback_id: str,
    options: list[RemoteStatusOption],
    assignable: Optional[list[RemoteAssignee]] = None,
) -> RemoteTask:
    task_id = str(data.get("id") or fallback_id)
    status_obj = as_dict(data.get("status"))
    status_name = str(status_obj.get("status") or "")
    assignees = _assignees_from_clickup_users(data.get("assignees") or [])
    url = str(data.get("url") or f"https://app.clickup.com/t/{task_id}")
    # Ensure current status is in the option list even if list fetch failed.
    if status_name and not any(
        o.name.lower() == status_name.lower() for o in options
    ):
        options = [
            RemoteStatusOption(
                id=str(status_obj.get("id") or status_name),
                name=status_name,
                color=str(status_obj.get("color") or ""),
                type=str(status_obj.get("type") or ""),
            ),
            *options,
        ]
    priority_name, priority_id, priority_color = _parse_clickup_priority(
        data.get("priority")
    )
    due_date = _ms_to_iso_date(data.get("due_date"))
    # Merge current assignees into assignable so the picker always shows them.
    assignable_list = list(assignable or [])
    seen = {a.id for a in assignable_list if a.id}
    for a in assignees:
        if a.id and a.id not in seen:
            assignable_list.append(a)
            seen.add(a.id)
    return RemoteTask(
        external_id=task_id,
        title=str(data.get("name") or ""),
        status=status_name,
        status_id=str(status_obj.get("id") or ""),
        status_color=str(status_obj.get("color") or ""),
        status_type=str(status_obj.get("type") or ""),
        url=url,
        key=task_id,
        priority=priority_name,
        priority_id=priority_id,
        priority_color=priority_color,
        due_date=due_date,
        assignees=assignees,
        assignable=assignable_list,
        status_options=options,
        priority_options=list(_CLICKUP_PRIORITIES),
        editable_fields=list(_EDITABLE),
        raw=as_dict(data),
    )


def _assignees_from_clickup_users(rows: Any) -> list[RemoteAssignee]:
    out: list[RemoteAssignee] = []
    for a in rows or []:
        if not isinstance(a, dict):
            continue
        uid = str(a.get("id") or "").strip()
        if not uid:
            continue
        out.append(
            RemoteAssignee(
                id=uid,
                name=str(
                    a.get("username")
                    or a.get("email")
                    or a.get("name")
                    or uid
                ),
                email=str(a.get("email") or ""),
                avatar_url=str(
                    a.get("profilePicture") or a.get("profilePic") or ""
                ),
            )
        )
    return out


def _unnest_member_rows(rows: list[Any]) -> list[Any]:
    """Return each member's ``user`` object when nested, otherwise the row itself."""
    out: list[Any] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nested_user = row.get("user")
        out.append(nested_user if isinstance(nested_user, dict) else row)
    return out


async def _fetch_list_members(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    list_id: str,
    *,
    team_id: str = "",
) -> list[RemoteAssignee]:
    """Assignable people for a ClickUp list (falls back to workspace members)."""
    members: list[RemoteAssignee] = []
    if list_id:
        try:
            resp = await client.get(
                f"{_API}/list/{list_id}/member", headers=headers
            )
            if resp.status_code < 400:
                data = resp.json() or {}
                members = _assignees_from_clickup_users(data.get("members") or [])
                # Some responses nest user under each member.
                if not members:
                    members = _assignees_from_clickup_users(
                        _unnest_member_rows(data.get("members") or [])
                    )
        except Exception:  # noqa: BLE001
            members = []
    if members:
        return members
    if not team_id:
        return []
    try:
        resp = await client.get(f"{_API}/team/{team_id}", headers=headers)
        if resp.status_code >= 400:
            return []
        data = resp.json() or {}
        team = as_dict(data.get("team")) or as_dict(data)
        rows = []
        for row in team.get("members") or []:
            if isinstance(row, dict) and isinstance(row.get("user"), dict):
                rows.append(row["user"])
            elif isinstance(row, dict):
                rows.append(row)
        return _assignees_from_clickup_users(rows)
    except Exception:  # noqa: BLE001
        return []


def _as_clickup_user_id(value: str) -> int | str:
    """ClickUp assignee add/rem prefers numeric ids when possible."""
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        return text


def _parse_clickup_priority(
    raw: Any,
) -> tuple[str, str, str]:
    """Normalize ClickUp priority object / id → (name, id, color)."""
    if raw is None or raw == "":
        return "", "", ""
    if isinstance(raw, dict):
        pid = str(raw.get("id") or raw.get("priority") or "").strip()
        # ClickUp sometimes returns priority as the word ("high") in `priority`.
        word = str(raw.get("priority") or "").strip().lower()
        color = str(raw.get("color") or "")
        if pid in _CLICKUP_PRIORITY_BY_ID:
            opt = _CLICKUP_PRIORITY_BY_ID[pid]
            return opt.name, opt.id, color or opt.color
        if word in _CLICKUP_PRIORITY_BY_NAME:
            opt = _CLICKUP_PRIORITY_BY_ID[str(_CLICKUP_PRIORITY_BY_NAME[word])]
            return opt.name, opt.id, color or opt.color
        if word:
            return word, pid or word, color
        return "", pid, color
    # Numeric / string id
    pid = str(raw).strip()
    if pid in _CLICKUP_PRIORITY_BY_ID:
        opt = _CLICKUP_PRIORITY_BY_ID[pid]
        return opt.name, opt.id, opt.color
    return "", pid, ""


def _clickup_priority_value(raw: str) -> Optional[int]:
    """Map UI priority name/id → ClickUp integer, or None to clear."""
    text = (raw or "").strip().lower()
    if not text:
        return None
    if text in _CLICKUP_PRIORITY_BY_NAME:
        return _CLICKUP_PRIORITY_BY_NAME[text]
    if text in _CLICKUP_PRIORITY_BY_ID:
        return int(text)
    raise ValueError(
        "ClickUp priority must be urgent, high, normal, low, or empty to clear."
    )


def _iso_date_to_ms(value: str) -> int:
    """YYYY-MM-DD → Unix ms at UTC midnight (ClickUp due_date)."""
    text = (value or "").strip()
    try:
        day = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("due_date must be YYYY-MM-DD.") from exc
    return int(day.timestamp() * 1000)


def _ms_to_iso_date(raw: Any) -> str:
    """ClickUp due_date (ms string/int) → YYYY-MM-DD, or ''."""
    if raw is None or raw == "":
        return ""
    try:
        ms = int(raw)
    except (TypeError, ValueError):
        # Already an ISO-ish string
        text = str(raw).strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]
        return ""
    if ms <= 0:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _parse_clickup_task_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" in raw:
        path = urlparse(raw).path.rstrip("/")
        # https://app.clickup.com/t/abc123 or /t/abc123/…
        parts = [p for p in path.split("/") if p]
        if "t" in parts:
            i = parts.index("t")
            if i + 1 < len(parts):
                return parts[i + 1]
        return parts[-1] if parts else ""
    return raw


def _safe_detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            return str(data.get("err") or data.get("error") or data)[:240]
    except Exception:  # noqa: BLE001
        pass
    return f"HTTP {resp.status_code}"
