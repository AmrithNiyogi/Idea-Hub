"""Organiser edits to an ideathon: phase-gated fields and date validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.ideathon import IdeathonUpdate
from app.services.ideathon_service import IdeathonService

START = datetime(2026, 12, 1, tzinfo=timezone.utc)
END = START + timedelta(days=30)
CHALLENGE = "Reduce the time support agents spend triaging tickets."


class _Actor:
    def __init__(self, roles: set[str]) -> None:
        self._roles = roles

    def has_role(self, role: str) -> bool:
        return role in self._roles


def _service(phase: str = "open", completed: bool = False) -> tuple[IdeathonService, Any]:
    it = SimpleNamespace(
        id=uuid.uuid4(),
        title="Original title",
        theme="Original theme",
        challenges=[CHALLENGE],
        start_at=START,
        end_at=END,
        phase=phase,
        completed_at=datetime.now(timezone.utc) if completed else None,
    )
    svc = IdeathonService.__new__(IdeathonService)
    svc.repo = SimpleNamespace(get=AsyncMock(return_value=it))
    svc.session = SimpleNamespace(commit=AsyncMock())
    return svc, it


ADMIN = _Actor({"admin"})


@pytest.mark.asyncio
async def test_non_organiser_is_forbidden() -> None:
    svc, _ = _service()
    with pytest.raises(HTTPException) as exc:
        await svc.update(uuid.uuid4(), IdeathonUpdate(title="New title"), _Actor(set()))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_open_ideathon_accepts_all_fields() -> None:
    svc, it = _service()
    new_end = END + timedelta(days=10)
    await svc.update(
        it.id,
        IdeathonUpdate(
            title="New title",
            theme="New theme",
            challenges=["Cut onboarding drop-off for new hires in the first week."],
            end_at=new_end,
        ),
        ADMIN,
    )
    assert it.title == "New title"
    assert it.theme == "New theme"
    assert it.end_at == new_end
    assert it.start_at == START
    svc.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_dates_and_title_editable_after_open_but_theme_locked() -> None:
    svc, it = _service(phase="pitch")
    await svc.update(it.id, IdeathonUpdate(title="Renamed", start_at=START + timedelta(days=1)), ADMIN)
    assert it.title == "Renamed"
    with pytest.raises(HTTPException) as exc:
        await svc.update(it.id, IdeathonUpdate(theme="Different"), ADMIN)
    assert exc.value.status_code == 400
    assert it.theme == "Original theme"


@pytest.mark.asyncio
async def test_challenges_locked_after_open() -> None:
    svc, it = _service(phase="shortlist")
    with pytest.raises(HTTPException) as exc:
        await svc.update(
            it.id,
            IdeathonUpdate(challenges=["Cut onboarding drop-off for new hires in the first week."]),
            ADMIN,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_completed_ideathon_cannot_be_edited() -> None:
    svc, it = _service(phase="handoff", completed=True)
    with pytest.raises(HTTPException) as exc:
        await svc.update(it.id, IdeathonUpdate(title="Too late"), ADMIN)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_end_must_be_after_start() -> None:
    svc, it = _service()
    with pytest.raises(HTTPException) as exc:
        await svc.update(it.id, IdeathonUpdate(end_at=START - timedelta(days=1)), ADMIN)
    assert exc.value.status_code == 400
    assert it.end_at == END


def test_update_schema_allows_empty_body_and_checks_challenge_length() -> None:
    assert IdeathonUpdate().model_dump(exclude_unset=True) == {}
    with pytest.raises(ValidationError):
        IdeathonUpdate(challenges=["too short"])
