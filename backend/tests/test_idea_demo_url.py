"""Live project (demo) link on an idea: https only, blank means none."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.idea import IdeaWrite


@pytest.mark.parametrize("url", ["https://demo.example.com", "https://acme.dev/app?x=1"])
def test_https_links_are_accepted(url: str) -> None:
    assert IdeaWrite(title="t", demo_url=url).demo_url == url


@pytest.mark.parametrize("url", ["http://demo.example.com", "ftp://x.example.com", "https://"])
def test_non_https_links_are_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        IdeaWrite(title="t", demo_url=url)


def test_blank_demo_url_is_stored_as_none() -> None:
    assert IdeaWrite(title="t", demo_url="   ").demo_url is None
