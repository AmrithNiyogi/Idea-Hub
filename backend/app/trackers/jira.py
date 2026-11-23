"""Jira Cloud tracker provider — email + API token + site URL.

Auth: HTTP basic (email + API token) against Atlassian Cloud REST API v3.
Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
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
    RemoteAssignee,
    RemotePriorityOption,
    RemoteStatusOption,
    RemoteTask,
    UpdateTaskPayload,
)
from app.utils.jsonish import as_dict

_JIRA_EDITABLE = ["status", "title", "priority", "due_date", "assignees"]
_JIRA_FIELDS = "summary,status,assignee,issuetype,priority,duedate"


class JiraProvider:
    id = "jira"
    display_name = "Jira"
    description = (
        "Create issues in a Jira Cloud project using an Atlassian API token. "
        "Create a token at id.atlassian.com → Security → API tokens."
    )
    auth_mode = "basic"
    connect_fields = [
        ConnectField(
            key="base_url",
            label="Site URL",
            placeholder="https://your-domain.atlassian.net",
            help_text="Jira Cloud site origin (no path).",
        ),
        ConnectField(
            key="email",
            label="Atlassian email",
            placeholder="you@company.com",
        ),
        ConnectField(
            key="api_token",
            label="API token",
            secret=True,
            placeholder="ATATT3…",
        ),
        ConnectField(
            key="project_key",
            label="Default project key",
            placeholder="ENG",
            help_text="Project key used when creating issues.",
        ),
        ConnectField(
            key="issue_type",
            label="Issue type",
            required=False,
            placeholder="Task",
            help_text="Defaults to Task.",
        ),
    ]

    async def validate_connection(
        self, credentials: dict[str, Any]
    ) -> ConnectionProbe:
        base, email, token, project_key = _creds(credentials)
        auth = (email, token)
        async with httpx.AsyncClient(timeout=20.0, base_url=base) as client:
            me = await client.get("/rest/api/3/myself", auth=auth)
            if me.status_code == 401:
                raise ValueError("Jira email/token was rejected.")
            me.raise_for_status()
            user = me.json() or {}
            proj = await client.get(
                f"/rest/api/3/project/{project_key}", auth=auth
            )
            if proj.status_code == 404:
                raise ValueError(f"Jira project {project_key} was not found.")
            if proj.status_code == 401:
                raise ValueError("Jira credentials cannot access that project.")
            proj.raise_for_status()
            project = proj.json() or {}
        label = user.get("displayName") or email
        pname = project.get("name") or project_key
        return ConnectionProbe(
            display_label=f"{label} · {pname} ({project_key})",
            external_account_id=str(user.get("accountId") or ""),
            meta={
                "project_key": project_key,
                "project_name": pname,
                "base_url": base,
            },
        )

    async def create_issue(
        self,
        credentials: dict[str, Any],
        payload: CreateIssuePayload,
    ) -> ExternalIssue:
        base, email, token, project_key = _creds(credentials)
        issue_type = (
            payload.extra.get("issue_type")
            or credentials.get("issue_type")
            or "Task"
        )
        project = payload.extra.get("project_key") or project_key
        body = {
            "fields": {
                "project": {"key": project},
                "summary": payload.title[:255],
                "description": _adf_doc(payload.description),
                "issuetype": {"name": str(issue_type)},
            }
        }
        auth = (email, token)
        async with httpx.AsyncClient(timeout=30.0, base_url=base) as client:
            resp = await client.post(
                "/rest/api/3/issue",
                auth=auth,
                json=body,
                headers={"Accept": "application/json"},
            )
            if resp.status_code >= 400:
                raise ValueError(f"Jira create failed: {_safe_detail(resp)}")
            data = resp.json() or {}
        key = str(data.get("key") or "")
        issue_id = str(data.get("id") or key)
        if not key and not issue_id:
            raise ValueError("Jira response missing issue key.")
        url = f"{base}/browse/{key}" if key else f"{base}/browse/{issue_id}"
        return ExternalIssue(
            external_id=issue_id or key,
            url=url,
            key=key or issue_id,
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
        base, email, token, _project = _creds(credentials)
        key = _parse_jira_key(external_id, base) or (external_id or "").strip()
        if not key:
            raise ValueError("Provide a Jira issue key (e.g. ENG-42) or browse URL.")
        auth = (email, token)
        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=20.0, base_url=base) as client:
            resp = await client.get(
                f"/rest/api/3/issue/{key}",
                auth=auth,
                headers=headers,
                params={"fields": _JIRA_FIELDS},
            )
            if resp.status_code == 404:
                raise ValueError(f"Jira issue {key} was not found.")
            if resp.status_code >= 400:
                raise ValueError(f"Jira lookup failed: {_safe_detail(resp)}")
            data = resp.json() or {}
            options = await _fetch_transitions(client, auth, headers, key)
            priorities = await _fetch_priorities(client, auth, headers)
            assignable = await _fetch_assignable(
                client, auth, headers, key
            )
        return _task_from_jira(
            data, base, options, priorities, assignable
        )

    async def update_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask:
        base, email, token, _project = _creds(credentials)
        key = _parse_jira_key(external_id, base) or (external_id or "").strip()
        if not key:
            raise ValueError("Provide a Jira issue key (e.g. ENG-42) or browse URL.")
        auth = (email, token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0, base_url=base) as client:
            fields_body: dict[str, Any] = {}
            if payload.title is not None:
                title = (payload.title or "").strip()
                if not title:
                    raise ValueError("Jira summary cannot be empty.")
                fields_body["summary"] = title[:255]
            if payload.priority is not None:
                pri = (payload.priority or "").strip()
                if not pri:
                    raise ValueError(
                        "Jira priority cannot be cleared via IdeaKonnekt; "
                        "pick another priority."
                    )
                priorities = await _fetch_priorities(client, auth, headers)
                match = next(
                    (
                        p
                        for p in priorities
                        if p.name.lower() == pri.lower() or p.id == pri
                    ),
                    None,
                )
                if not match:
                    names = ", ".join(p.name for p in priorities) or "(none)"
                    raise ValueError(
                        f"Unknown Jira priority '{pri}'. Available: {names}"
                    )
                fields_body["priority"] = {"id": match.id}
            if payload.due_date is not None:
                due_raw = (payload.due_date or "").strip()
                # Jira accepts YYYY-MM-DD; null clears.
                fields_body["duedate"] = due_raw or None
            if payload.assignee_ids is not None:
                # Jira is single-assignee: first id wins; empty list unassigns.
                ids = [
                    str(x).strip()
                    for x in payload.assignee_ids
                    if str(x).strip()
                ]
                if not ids:
                    fields_body["assignee"] = None
                else:
                    fields_body["assignee"] = {"accountId": ids[0]}
            if fields_body:
                edit = await client.put(
                    f"/rest/api/3/issue/{key}",
                    auth=auth,
                    headers=headers,
                    json={"fields": fields_body},
                )
                if edit.status_code >= 400:
                    raise ValueError(f"Jira update failed: {_safe_detail(edit)}")
            if payload.status is not None:
                status_name = (payload.status or "").strip()
                if not status_name:
                    raise ValueError("Jira status cannot be empty.")
                options = await _fetch_transitions(client, auth, headers, key)
                transition = next(
                    (
                        o
                        for o in options
                        if o.name.lower() == status_name.lower()
                        or o.id == status_name
                    ),
                    None,
                )
                if not transition:
                    names = ", ".join(o.name for o in options) or "(none)"
                    raise ValueError(
                        f"No Jira transition to '{status_name}'. "
                        f"Available: {names}"
                    )
                tr = await client.post(
                    f"/rest/api/3/issue/{key}/transitions",
                    auth=auth,
                    headers=headers,
                    json={"transition": {"id": transition.id}},
                )
                if tr.status_code >= 400:
                    raise ValueError(
                        f"Jira transition failed: {_safe_detail(tr)}"
                    )
            if (
                payload.title is None
                and payload.status is None
                and payload.priority is None
                and payload.due_date is None
                and payload.assignee_ids is None
            ):
                raise ValueError("No Jira fields to update.")
            # Re-fetch live snapshot after writes.
            resp = await client.get(
                f"/rest/api/3/issue/{key}",
                auth=auth,
                headers={"Accept": "application/json"},
                params={"fields": _JIRA_FIELDS},
            )
            if resp.status_code >= 400:
                raise ValueError(f"Jira refresh failed: {_safe_detail(resp)}")
            data = resp.json() or {}
            accept = {"Accept": "application/json"}
            options = await _fetch_transitions(client, auth, accept, key)
            priorities = await _fetch_priorities(client, auth, accept)
            assignable = await _fetch_assignable(client, auth, accept, key)
        return _task_from_jira(
            data, base, options, priorities, assignable
        )


async def _fetch_transitions(
    client: httpx.AsyncClient,
    auth: tuple[str, str],
    headers: dict[str, str],
    key: str,
) -> list[RemoteStatusOption]:
    """Map Jira transitions → status picker options (target status name)."""
    try:
        resp = await client.get(
            f"/rest/api/3/issue/{key}/transitions",
            auth=auth,
            headers=headers,
        )
        if resp.status_code >= 400:
            return []
        data = resp.json() or {}
    except Exception:  # noqa: BLE001
        return []
    out: list[RemoteStatusOption] = []
    seen: set[str] = set()
    for row in data.get("transitions") or []:
        if not isinstance(row, dict):
            continue
        to = as_dict(row.get("to"))
        name = str(to.get("name") or row.get("name") or "").strip()
        tid = str(row.get("id") or "")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        cat = as_dict(to.get("statusCategory"))
        out.append(
            RemoteStatusOption(
                id=tid,
                name=name,
                color=str(cat.get("colorName") or ""),
                type=str(cat.get("key") or ""),
            )
        )
    return out


async def _fetch_priorities(
    client: httpx.AsyncClient,
    auth: tuple[str, str],
    headers: dict[str, str],
) -> list[RemotePriorityOption]:
    try:
        resp = await client.get(
            "/rest/api/3/priority", auth=auth, headers=headers
        )
        if resp.status_code >= 400:
            return []
        data = resp.json() or []
    except Exception:  # noqa: BLE001
        return []
    out: list[RemotePriorityOption] = []
    if not isinstance(data, list):
        return []
    for row in data:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        out.append(
            RemotePriorityOption(
                id=str(row.get("id") or name),
                name=name,
                color=str(row.get("statusColor") or row.get("iconUrl") or ""),
            )
        )
    return out


async def _fetch_assignable(
    client: httpx.AsyncClient,
    auth: tuple[str, str],
    headers: dict[str, str],
    key: str,
) -> list[RemoteAssignee]:
    """People who can be assigned to this Jira issue."""
    try:
        resp = await client.get(
            "/rest/api/3/user/assignable/search",
            auth=auth,
            headers=headers,
            params={"issueKey": key, "maxResults": 50},
        )
        if resp.status_code >= 400:
            return []
        data = resp.json() or []
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(data, list):
        return []
    out: list[RemoteAssignee] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        uid = str(row.get("accountId") or "").strip()
        if not uid:
            continue
        out.append(
            RemoteAssignee(
                id=uid,
                name=str(row.get("displayName") or row.get("emailAddress") or uid),
                email=str(row.get("emailAddress") or ""),
                avatar_url=str(
                    ((row.get("avatarUrls") or {}) or {}).get("24x24") or ""
                ),
            )
        )
    return out


def _task_from_jira(
    data: dict[str, Any],
    base: str,
    options: list[RemoteStatusOption],
    priorities: list[RemotePriorityOption] | None = None,
    assignable: list[RemoteAssignee] | None = None,
) -> RemoteTask:
    fields = as_dict(data.get("fields"))
    issue_key = str(data.get("key") or "")
    issue_id = str(data.get("id") or issue_key)
    status_obj = as_dict(fields.get("status"))
    status_name = str(status_obj.get("name") or "")
    status_cat = (
        as_dict(status_obj.get("statusCategory"))
    )
    assignees: list[RemoteAssignee] = []
    assignee = fields.get("assignee")
    if isinstance(assignee, dict) and assignee:
        avatars = as_dict(assignee.get("avatarUrls"))
        assignees.append(
            RemoteAssignee(
                id=str(assignee.get("accountId") or ""),
                name=str(assignee.get("displayName") or ""),
                email=str(assignee.get("emailAddress") or ""),
                avatar_url=str(avatars.get("24x24") or ""),
            )
        )
    if status_name and not any(
        o.name.lower() == status_name.lower() for o in options
    ):
        options = [
            RemoteStatusOption(
                id=str(status_obj.get("id") or status_name),
                name=status_name,
                color=str(status_cat.get("colorName") or ""),
                type=str(status_cat.get("key") or ""),
            ),
            *options,
        ]
    pri_obj = as_dict(fields.get("priority"))
    pri_name = str(pri_obj.get("name") or "")
    pri_id = str(pri_obj.get("id") or "")
    pri_color = str(pri_obj.get("statusColor") or "")
    due_raw = fields.get("duedate")
    due_date = ""
    if due_raw:
        text = str(due_raw).strip()
        due_date = text[:10] if len(text) >= 10 else text
    priority_options = list(priorities or [])
    if pri_name and not any(
        p.name.lower() == pri_name.lower() for p in priority_options
    ):
        priority_options = [
            RemotePriorityOption(id=pri_id or pri_name, name=pri_name, color=pri_color),
            *priority_options,
        ]
    assignable_list = list(assignable or [])
    seen = {a.id for a in assignable_list if a.id}
    for a in assignees:
        if a.id and a.id not in seen:
            assignable_list.append(a)
            seen.add(a.id)
    return RemoteTask(
        external_id=issue_id,
        title=str(fields.get("summary") or ""),
        status=status_name,
        status_id=str(status_obj.get("id") or ""),
        status_color=str(status_cat.get("colorName") or ""),
        status_type=str(status_cat.get("key") or ""),
        url=f"{base}/browse/{issue_key}" if issue_key else "",
        key=issue_key or issue_id,
        priority=pri_name,
        priority_id=pri_id,
        priority_color=pri_color,
        due_date=due_date,
        assignees=assignees,
        assignable=assignable_list,
        status_options=options,
        priority_options=priority_options,
        editable_fields=list(_JIRA_EDITABLE),
        raw=as_dict(data),
    )


def _creds(credentials: dict[str, Any]) -> tuple[str, str, str, str]:
    base = _normalize_base(str(credentials.get("base_url") or ""))
    email = (credentials.get("email") or "").strip()
    token = (credentials.get("api_token") or "").strip()
    project_key = (credentials.get("project_key") or "").strip().upper()
    if not base or not email or not token or not project_key:
        raise ValueError(
            "Jira requires base_url, email, api_token, and project_key."
        )
    return base, email, token, project_key


def _normalize_base(url: str) -> str:
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return ""
    if not raw.startswith("http"):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$", re.I)


def _parse_jira_key(value: str, base: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if _KEY_RE.match(raw):
        return raw.upper()
    if "://" in raw:
        path = urlparse(raw).path
        m = re.search(r"/browse/([A-Za-z][A-Za-z0-9]+-\d+)", path)
        if m:
            return m.group(1).upper()
        # Allow same-site relative keys at end of path
        tail = path.rstrip("/").split("/")[-1]
        if _KEY_RE.match(tail):
            return tail.upper()
    # Ignore unrelated bases quietly — key extraction is best-effort.
    _ = base
    return raw.upper() if _KEY_RE.match(raw) else ""


def _adf_doc(text: str) -> dict[str, Any]:
    """Minimal Atlassian Document Format paragraph wrapper."""
    content = (text or "").strip() or "(from IdeaKonnekt)"
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": content[:8000]}],
            }
        ],
    }


def _safe_detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            errs = data.get("errorMessages") or data.get("errors")
            if errs:
                return str(errs)[:240]
            return str(data)[:240]
    except Exception:  # noqa: BLE001
        pass
    return f"HTTP {resp.status_code}"
