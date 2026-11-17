"""Generic / self-built tracker via configurable webhook.

This is the extension path for a tracker you develop later: point Idea Hub at
your create-task HTTP endpoint. Auth is a single header value (Bearer, API key,
or custom ``Authorization`` string).

Contract (create)
-----------------
``POST {webhook_url}``

Request JSON::

    {
      "title": "…",
      "description": "…",
      "idea_id": "uuid",
      "idea_url": "https://…/ideas/uuid",
      "status_hint": "prototype",
      "tags": ["…"],
      "extra": {}
    }

Success response (2xx) JSON — at least one of ``id`` / ``external_id``::

    {
      "id": "TASK-1",
      "url": "https://your-tracker/tasks/TASK-1",
      "key": "TASK-1"
    }

Validate uses optional ``GET {webhook_url}`` or ``POST`` with
``{"action":"ping"}`` when ``ping_mode`` is ``post`` (default ``get``).
"""

from __future__ import annotations

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


class CustomWebhookProvider:
    id = "custom_webhook"
    display_name = "Custom tracker (webhook)"
    description = (
        "Plug in a tracker you build later: Idea Hub POSTs create-task JSON "
        "to your URL with an optional auth header. Use this until you ship a "
        "dedicated TrackerProvider class."
    )
    auth_mode = "webhook"
    connect_fields = [
        ConnectField(
            key="webhook_url",
            label="Create-task URL",
            placeholder="https://tracker.example.com/api/idea-hub/tasks",
            help_text="HTTPS endpoint that accepts the create-task JSON contract.",
        ),
        ConnectField(
            key="auth_header_name",
            label="Auth header name",
            required=False,
            placeholder="Authorization",
            help_text="Defaults to Authorization when a value is set.",
        ),
        ConnectField(
            key="auth_header_value",
            label="Auth header value",
            secret=True,
            required=False,
            placeholder="Bearer …",
            help_text="Optional. Never committed; stored encrypted.",
        ),
        ConnectField(
            key="ping_mode",
            label="Validate mode",
            required=False,
            placeholder="get",
            help_text="get (default) or post — how connect validation probes the URL.",
        ),
        ConnectField(
            key="display_label",
            label="Display name",
            required=False,
            placeholder="Our internal tracker",
            help_text="Shown in Idea Hub connection lists.",
        ),
    ]

    async def validate_connection(
        self, credentials: dict[str, Any]
    ) -> ConnectionProbe:
        merged = _with_env_defaults(credentials)
        url = _require_https_url(merged.get("webhook_url"))
        headers = _auth_headers(merged)
        mode = (merged.get("ping_mode") or "get").strip().lower()
        async with httpx.AsyncClient(timeout=20.0) as client:
            if mode == "post":
                resp = await client.post(
                    url, headers=headers, json={"action": "ping"}
                )
            else:
                resp = await client.get(url, headers=headers)
            # Some webhooks only accept POST create — treat 405 on GET as OK.
            if resp.status_code == 405 and mode != "post":
                pass
            elif resp.status_code >= 400:
                raise ValueError(
                    f"Custom tracker probe failed: HTTP {resp.status_code}"
                )
        host = urlparse(url).netloc
        label = (merged.get("display_label") or "").strip() or host
        return ConnectionProbe(
            display_label=label,
            external_account_id=host,
            meta={"webhook_url": url, "ping_mode": mode},
        )

    async def create_issue(
        self,
        credentials: dict[str, Any],
        payload: CreateIssuePayload,
    ) -> ExternalIssue:
        merged = _with_env_defaults(credentials)
        url = _require_https_url(merged.get("webhook_url"))
        headers = {
            **_auth_headers(merged),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {
            "title": payload.title,
            "description": payload.description,
            "idea_id": payload.idea_id,
            "idea_url": payload.idea_url,
            "status_hint": payload.status_hint,
            "tags": payload.tags,
            "extra": payload.extra,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                raise ValueError(
                    f"Custom tracker create failed: HTTP {resp.status_code}"
                )
            data = _json_obj(resp)
        external_id = str(
            data.get("id") or data.get("external_id") or data.get("key") or ""
        )
        if not external_id:
            raise ValueError(
                "Custom tracker response must include id, external_id, or key."
            )
        issue_url = str(data.get("url") or data.get("html_url") or "")
        if not issue_url:
            issue_url = f"{url.rstrip('/')}/{external_id}"
        return ExternalIssue(
            external_id=external_id,
            url=issue_url,
            key=str(data.get("key") or external_id),
            raw=data,
        )

    async def resolve_existing(
        self,
        credentials: dict[str, Any],
        external_id_or_url: str,
    ) -> ExternalIssue:
        """Link-only path: store the caller-supplied id/URL without a remote GET.

        Self-built trackers can later override this with a real lookup by
        registering a dedicated ``TrackerProvider`` instead of the webhook stub.
        """
        _ = credentials
        raw = (external_id_or_url or "").strip()
        if not raw:
            raise ValueError("Provide an external id or URL to link.")
        if "://" in raw:
            return ExternalIssue(external_id=raw.rstrip("/").split("/")[-1], url=raw, key="")
        return ExternalIssue(external_id=raw, url="", key=raw)

    async def get_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
    ) -> RemoteTask:
        """Best-effort live fetch via ``POST {webhook_url}`` with ``action=get_task``.

        Expected 2xx JSON::

            {
              "id": "…",
              "title": "…",
              "status": "…",
              "url": "https://…",
              "assignees": [{"id":"…","name":"…"}],
              "status_options": [{"id":"…","name":"…"}]
            }

        If the webhook does not implement get_task, raise ``ValueError``.
        """
        merged = _with_env_defaults(credentials)
        url = _require_https_url(merged.get("webhook_url"))
        task_id = (external_id or "").strip()
        if not task_id:
            raise ValueError("Provide an external task id.")
        headers = {
            **_auth_headers(merged),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                headers=headers,
                json={"action": "get_task", "external_id": task_id},
            )
            if resp.status_code >= 400:
                raise ValueError(
                    f"Custom tracker get_task failed: HTTP {resp.status_code}"
                )
            data = _json_obj(resp)
        return _remote_from_webhook(data, task_id, url)

    async def update_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask:
        """Best-effort write-back via ``POST`` ``action=update_task``."""
        merged = _with_env_defaults(credentials)
        url = _require_https_url(merged.get("webhook_url"))
        task_id = (external_id or "").strip()
        if not task_id:
            raise ValueError("Provide an external task id.")
        body: dict[str, Any] = {
            "action": "update_task",
            "external_id": task_id,
        }
        if payload.status is not None:
            body["status"] = payload.status
        if payload.title is not None:
            body["title"] = payload.title
        if payload.priority is not None:
            body["priority"] = payload.priority
        if payload.due_date is not None:
            body["due_date"] = payload.due_date
        if payload.assignee_ids is not None:
            body["assignee_ids"] = list(payload.assignee_ids)
        if payload.extra:
            body["extra"] = dict(payload.extra)
        if len(body) <= 2:
            raise ValueError("No custom tracker fields to update.")
        headers = {
            **_auth_headers(merged),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                raise ValueError(
                    f"Custom tracker update_task failed: HTTP {resp.status_code}"
                )
            data = _json_obj(resp)
        return _remote_from_webhook(data, task_id, url)


def _remote_from_webhook(
    data: dict[str, Any], fallback_id: str, webhook_url: str
) -> RemoteTask:
    external_id = str(
        data.get("id") or data.get("external_id") or fallback_id
    )
    assignees: list[RemoteAssignee] = []
    for a in data.get("assignees") or []:
        if isinstance(a, dict):
            assignees.append(
                RemoteAssignee(
                    id=str(a.get("id") or ""),
                    name=str(a.get("name") or a.get("email") or ""),
                    email=str(a.get("email") or ""),
                    avatar_url=str(
                        a.get("avatar_url") or a.get("avatar") or ""
                    ),
                )
            )
        elif isinstance(a, str) and a.strip():
            assignees.append(RemoteAssignee(name=a.strip()))
    options: list[RemoteStatusOption] = []
    for o in data.get("status_options") or data.get("statuses") or []:
        if not isinstance(o, dict):
            continue
        name = str(o.get("name") or o.get("status") or "").strip()
        if not name:
            continue
        options.append(
            RemoteStatusOption(
                id=str(o.get("id") or name),
                name=name,
                color=str(o.get("color") or ""),
                type=str(o.get("type") or ""),
            )
        )
    status = str(data.get("status") or "")
    issue_url = str(data.get("url") or data.get("html_url") or "")
    if not issue_url:
        issue_url = f"{webhook_url.rstrip('/')}/{external_id}"
    assignable: list[RemoteAssignee] = []
    for a in data.get("assignable") or data.get("members") or []:
        if isinstance(a, dict):
            assignable.append(
                RemoteAssignee(
                    id=str(a.get("id") or ""),
                    name=str(a.get("name") or a.get("email") or ""),
                    email=str(a.get("email") or ""),
                    avatar_url=str(a.get("avatar_url") or a.get("avatar") or ""),
                )
            )
    priority_options: list[RemotePriorityOption] = []
    for o in data.get("priority_options") or data.get("priorities") or []:
        if not isinstance(o, dict):
            continue
        name = str(o.get("name") or "").strip()
        if not name:
            continue
        priority_options.append(
            RemotePriorityOption(
                id=str(o.get("id") or name),
                name=name,
                color=str(o.get("color") or ""),
            )
        )
    editable = data.get("editable_fields")
    if isinstance(editable, list) and editable:
        editable_fields = [str(x) for x in editable]
    else:
        editable_fields = ["status", "title", "priority", "due_date", "assignees"]
    return RemoteTask(
        external_id=external_id,
        title=str(data.get("title") or data.get("name") or ""),
        status=status,
        status_id=str(data.get("status_id") or ""),
        status_color=str(data.get("status_color") or ""),
        status_type=str(data.get("status_type") or ""),
        url=issue_url,
        key=str(data.get("key") or external_id),
        priority=str(data.get("priority") or ""),
        priority_id=str(data.get("priority_id") or ""),
        priority_color=str(data.get("priority_color") or ""),
        due_date=str(data.get("due_date") or "")[:10],
        assignees=assignees,
        assignable=assignable,
        status_options=options,
        priority_options=priority_options,
        editable_fields=editable_fields,
        raw=data,
    )


def _with_env_defaults(credentials: dict[str, Any]) -> dict[str, Any]:
    """Fill blank fields from optional Settings placeholders (local demos)."""
    from app.config.settings import settings

    out = dict(credentials or {})
    if not (out.get("webhook_url") or "").strip():
        out["webhook_url"] = settings.TRACKER_CUSTOM_WEBHOOK_URL or ""
    if not (out.get("auth_header_value") or "").strip():
        out["auth_header_value"] = settings.TRACKER_CUSTOM_AUTH_HEADER or ""
    return out


def _require_https_url(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("webhook_url must be an absolute http(s) URL.")
    # Allow http only for local/dev loopback; require https otherwise.
    host = parsed.hostname or ""
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("webhook_url must use https (except localhost).")
    return url.rstrip("/")


def _auth_headers(credentials: dict[str, Any]) -> dict[str, str]:
    value = (credentials.get("auth_header_value") or "").strip()
    if not value:
        return {}
    name = (credentials.get("auth_header_name") or "Authorization").strip()
    if not name:
        name = "Authorization"
    return {name: value}


def _json_obj(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Custom tracker response was not JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("Custom tracker response must be a JSON object.")
    return data
