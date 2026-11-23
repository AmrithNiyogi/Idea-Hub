"""Live call to the Kompass Ideathon Rank agent through the staging gateway.

Skipped unless every condition holds:
- ``AISTUDIO_LIVE_TEST=1`` in the environment
- the gateway settings and ``AISTUDIO_AGENT_IDEATHON_RANK`` are set in ``.env``
- ``IDEATHON_LIVE_TEST_ID`` names an ideathon that has entries in the gateway's data

This test spends real agent runs and needs the tool auth token, so it never runs in CI by default.
"""

from __future__ import annotations

import os
import uuid

import pytest

from app.config.settings import settings
from app.services import aistudio_execute_client as studio
from app.services import ideathon_rank_service

LIVE = os.environ.get("AISTUDIO_LIVE_TEST") == "1"
LIVE_IDEATHON = os.environ.get("IDEATHON_LIVE_TEST_ID", "")
CONFIGURED = bool(
    studio.aistudio_configured() and studio.resolve_kompass_agent_id("ideathon-rank")
)


@pytest.mark.skipif(
    not (LIVE and CONFIGURED and LIVE_IDEATHON),
    reason="live test: set AISTUDIO_LIVE_TEST=1, IDEATHON_LIVE_TEST_ID and the gateway settings",
)
@pytest.mark.asyncio
async def test_rank_agent_answers_over_the_gateway() -> None:
    result = await ideathon_rank_service.propose_rank(uuid.UUID(LIVE_IDEATHON), {"impact": 1.0})
    assert result.success, result.error
    assert result.result_text.strip(), "the agent returned an empty reply"
    assert settings.AISTUDIO_PROJECT_SLUG
