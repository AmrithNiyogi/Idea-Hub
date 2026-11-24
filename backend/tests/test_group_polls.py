"""Poll tally helper: counts per option, total, and the caller's own vote."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.groups import GroupPoll, GroupPollVote
from app.services.groups_service import GroupsService


def test_poll_out_tallies_votes_and_my_vote() -> None:
    me, other, third = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    poll = GroupPoll(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        question="Ship Friday?",
        options=["yes", "no", "later"],
        multi_select=False,
        created_by=me,
        closed_at=None,
        created_at=datetime.now(timezone.utc),
    )
    votes = [
        GroupPollVote(poll_id=poll.id, user_id=me, option_index=0),
        GroupPollVote(poll_id=poll.id, user_id=other, option_index=2),
        GroupPollVote(poll_id=poll.id, user_id=third, option_index=0),
    ]

    out = GroupsService(None)._poll_out(poll, votes, me)  # type: ignore[arg-type]

    assert out.counts == [2, 0, 1]
    assert out.total_votes == 3
    assert out.my_votes == [0]


def test_poll_out_multi_select_lists_all_my_votes() -> None:
    me = uuid.uuid4()
    poll = GroupPoll(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        question="Which days?",
        options=["mon", "tue", "wed"],
        multi_select=True,
        created_by=me,
        created_at=datetime.now(timezone.utc),
    )
    votes = [
        GroupPollVote(poll_id=poll.id, user_id=me, option_index=2),
        GroupPollVote(poll_id=poll.id, user_id=me, option_index=0),
    ]

    out = GroupsService(None)._poll_out(poll, votes, me)  # type: ignore[arg-type]

    assert out.counts == [1, 0, 1]
    assert out.my_votes == [0, 2]
    assert out.multi_select is True


def test_poll_out_without_my_vote() -> None:
    me = uuid.uuid4()
    poll = GroupPoll(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        question="Lunch?",
        options=["pizza", "sushi"],
        created_by=me,
        created_at=datetime.now(timezone.utc),
    )

    out = GroupsService(None)._poll_out(poll, [], me)  # type: ignore[arg-type]

    assert out.counts == [0, 0]
    assert out.total_votes == 0
    assert out.my_votes == []
