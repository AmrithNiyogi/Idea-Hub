"""Debug log masking: masked by default, full values only when the unmasked switch is on."""

from __future__ import annotations

import pytest

from app.config.settings import settings
from app.utils.debug_log import describe_headers, mask

TOKEN = "eyJhbGciOiJIUzI1NiJ9.payload-middle-part.signature-tail"


def test_mask_hides_the_middle_of_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AGENT_INTERNAL_DEBUG_UNMASKED", False)
    masked = mask(f"Bearer {TOKEN}")
    assert masked.startswith("Bearer eyJhbGciOiJI")
    assert "payload-middle-part" not in masked
    assert f"len {len(TOKEN)}" in masked


def test_unmasked_switch_prints_the_full_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AGENT_INTERNAL_DEBUG_UNMASKED", True)
    assert mask(f"Bearer {TOKEN}") == f"Bearer {TOKEN}"
    headers = describe_headers({"Authorization": f"Bearer {TOKEN}", "Cookie": f"access_token={TOKEN}"})
    assert TOKEN in headers["Authorization"]
    assert TOKEN in headers["Cookie"]
