"""Tracker provider contract — implement this to add a new external tracker.

A provider is a pure integration adapter: it never talks to the DB or FastAPI.
The ``TrackerService`` owns persistence, encryption, and authz; providers only
validate credentials and create/link remote work items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class ConnectField:
    """One credential / config field the UI should collect for ``connect``."""

    key: str
    label: str
    secret: bool = False
    required: bool = True
    placeholder: str = ""
    help_text: str = ""
    # When True, Integrations UI groups the field under an Advanced disclosure.
    advanced: bool = False


@dataclass
class CreateIssuePayload:
    """Normalized idea → external task payload."""

    title: str
    description: str
    idea_id: str
    idea_url: str
    status_hint: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalIssue:
    """Result of creating or resolving a remote work item."""

    external_id: str
    url: str
    key: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionProbe:
    """Outcome of ``validate_connection`` (workspace/user display meta)."""

    display_label: str
    external_account_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteAssignee:
    """Person assigned on a remote work item (or assignable candidate)."""

    id: str = ""
    name: str = ""
    email: str = ""
    avatar_url: str = ""


@dataclass
class RemoteStatusOption:
    """A status the remote tracker accepts for this work item."""

    name: str
    id: str = ""
    color: str = ""
    type: str = ""  # open | closed | custom | done | …


@dataclass
class RemotePriorityOption:
    """A priority the remote tracker accepts for this work item."""

    name: str
    id: str = ""
    color: str = ""


@dataclass
class RemoteTask:
    """Live snapshot of a remote work item (fetched from the tracker)."""

    external_id: str
    title: str = ""
    status: str = ""
    status_id: str = ""
    status_color: str = ""
    status_type: str = ""
    url: str = ""
    key: str = ""
    priority: str = ""
    priority_id: str = ""
    priority_color: str = ""
    due_date: str = ""  # ISO date YYYY-MM-DD, or empty if unset
    assignees: list[RemoteAssignee] = field(default_factory=list)
    assignable: list[RemoteAssignee] = field(default_factory=list)
    status_options: list[RemoteStatusOption] = field(default_factory=list)
    priority_options: list[RemotePriorityOption] = field(default_factory=list)
    editable_fields: list[str] = field(
        default_factory=lambda: ["status", "title"]
    )
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateTaskPayload:
    """Partial update pushed back to the remote tracker.

    Optional fields use ``None`` to mean “leave unchanged”. Empty string clears
    clearable fields (``priority``, ``due_date``) when the provider supports it.
    ``assignee_ids`` is the desired full set of remote user ids (provider diffs
    add/rem against current assignees).
    """

    status: Optional[str] = None
    title: Optional[str] = None
    priority: Optional[str] = None  # name or id; "" clears
    due_date: Optional[str] = None  # YYYY-MM-DD; "" clears
    assignee_ids: Optional[list[str]] = None
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class TrackerProvider(Protocol):
    """First-class extension point for SaaS or self-built trackers.

    Required attributes / methods
    -----------------------------
    ``id``:
        Stable slug stored in DB (``clickup``, ``jira``, ``custom_webhook``, …).
    ``display_name``:
        Human label for UI lists.
    ``description``:
        Short help blurb for the connect form.
    ``auth_mode``:
        One of ``api_token``, ``basic``, ``webhook``, ``oauth`` (informational).
    ``connect_fields``:
        Ordered fields the frontend renders; secrets are never echoed back.
    ``validate_connection(credentials)``:
        Probe the remote API; raise ``ValueError`` on bad credentials.
    ``create_issue(credentials, payload)``:
        Create a remote task/issue and return ``ExternalIssue``.
    ``resolve_existing(credentials, external_id_or_url)``:
        Resolve an existing remote id/URL into ``ExternalIssue`` for linking.
    ``get_task(credentials, external_id)``:
        Fetch a live remote snapshot (title, status, assignees, options).
    ``update_task(credentials, external_id, payload)``:
        Push supported field changes (at least status) back to the tracker.
    """

    id: str
    display_name: str
    description: str
    auth_mode: str
    connect_fields: list[ConnectField]

    async def validate_connection(
        self, credentials: dict[str, Any]
    ) -> ConnectionProbe: ...

    async def create_issue(
        self,
        credentials: dict[str, Any],
        payload: CreateIssuePayload,
    ) -> ExternalIssue: ...

    async def resolve_existing(
        self,
        credentials: dict[str, Any],
        external_id_or_url: str,
    ) -> ExternalIssue: ...

    async def get_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
    ) -> RemoteTask: ...

    async def update_task(
        self,
        credentials: dict[str, Any],
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask: ...
