"""Tracker registry + provider descriptor smoke tests."""

from __future__ import annotations

import pytest

from app.trackers.registry import (
    get_provider,
    list_providers,
    provider_public_dict,
    register_provider,
)
from app.trackers.base import (
    ConnectField,
    ConnectionProbe,
    CreateIssuePayload,
    ExternalIssue,
    RemoteTask,
    UpdateTaskPayload,
)


def test_builtins_include_clickup_jira_custom() -> None:
    ids = {p.id for p in list_providers()}
    assert {"clickup", "jira", "custom_webhook"} <= ids


def test_provider_public_dict_exposes_connect_fields() -> None:
    p = get_provider("clickup")
    d = provider_public_dict(p)
    assert d["id"] == "clickup"
    assert d["display_name"]
    keys = {f["key"] for f in d["connect_fields"]}
    assert "api_token" in keys
    assert "list_id" in keys


class _StubProvider:
    id = "test_stub"
    display_name = "Test Stub"
    description = "Example custom provider for registry tests."
    auth_mode = "api_token"
    connect_fields = [
        ConnectField(key="token", label="Token", secret=True),
    ]

    async def validate_connection(self, credentials: dict) -> ConnectionProbe:
        if not credentials.get("token"):
            raise ValueError("token required")
        return ConnectionProbe(display_label="stub")

    async def create_issue(
        self, credentials: dict, payload: CreateIssuePayload
    ) -> ExternalIssue:
        return ExternalIssue(
            external_id="1",
            url="https://example.test/1",
            key="1",
        )

    async def resolve_existing(
        self, credentials: dict, external_id_or_url: str
    ) -> ExternalIssue:
        return ExternalIssue(
            external_id=external_id_or_url,
            url="",
            key=external_id_or_url,
        )

    async def get_task(self, credentials: dict, external_id: str) -> RemoteTask:
        return RemoteTask(external_id=external_id, title="stub", status="open")

    async def update_task(
        self,
        credentials: dict,
        external_id: str,
        payload: UpdateTaskPayload,
    ) -> RemoteTask:
        return RemoteTask(
            external_id=external_id,
            title=payload.title or "stub",
            status=payload.status or "open",
        )


def test_register_custom_provider() -> None:
    register_provider(_StubProvider(), replace=True)
    p = get_provider("test_stub")
    assert p.display_name == "Test Stub"
    assert any(x.id == "test_stub" for x in list_providers())


@pytest.mark.asyncio
async def test_custom_webhook_rejects_non_https() -> None:
    p = get_provider("custom_webhook")
    with pytest.raises(ValueError, match="http\\(s\\)"):
        await p.validate_connection(
            {"webhook_url": "ftp://evil.example/hooks"}
        )
