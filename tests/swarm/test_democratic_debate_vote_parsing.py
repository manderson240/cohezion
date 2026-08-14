"""Substring matching flipped the sign of every dissent.

THE DEFECT (found 2026-08-14). Votes were parsed as:

    for v in VoteValue:
        if v.name in response.upper(): vote = v; break

and ``"AGREE" in "DISAGREE"`` is True. AGREE precedes DISAGREE in the enum, so:

    "Vote: DISAGREE"          -> AGREE (+1)   should be -1
    "Vote: STRONGLY_DISAGREE" -> AGREE (+1)   should be -2

MEASURED CONSEQUENCE: five agents ALL voting STRONGLY_DISAGREE scored 0.750 and returned
consensus=True, against a true score of 0.000. A module whose entire purpose is measuring
consensus reported agreement on unanimous dissent.

Second defect, same site: an unreadable reply fell through to ``vote = VoteValue.NEUTRAL``,
so a dead agent cast a neutral vote instead of abstaining -- indistinguishable from a
considered neutral opinion, and it drags any real result toward the 0.5 midpoint.
"""

from __future__ import annotations

import pytest

from cohezion.swarm.democratic_debate import (
    AgentRole,
    AgentVote,
    DebateRound,
    VoteValue,
    parse_vote,
)


# ---------------------------------------------------------------- sign correctness
@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("Vote: STRONGLY_AGREE\nReasoning: solid.", VoteValue.STRONGLY_AGREE),
        ("Vote: AGREE\nReasoning: fine.", VoteValue.AGREE),
        ("Vote: NEUTRAL\nReasoning: unsure.", VoteValue.NEUTRAL),
        ("Vote: DISAGREE\nReasoning: risky.", VoteValue.DISAGREE),
        ("Vote: STRONGLY_DISAGREE\nReasoning: unsafe.", VoteValue.STRONGLY_DISAGREE),
    ],
)
def test_every_vote_parses_to_itself(reply: str, expected: VoteValue) -> None:
    """THE regression. Under substring matching the two DISAGREE cases returned AGREE."""
    vote, parsed = parse_vote(reply)
    assert parsed
    assert vote is expected, f"{reply!r} parsed as {vote.name}, expected {expected.name}"


def test_dissent_never_parses_with_a_positive_value() -> None:
    """Stated as the property that actually matters: a dissent must never score positive."""
    for reply in ("Vote: DISAGREE", "Vote: STRONGLY_DISAGREE"):
        vote, _ = parse_vote(reply)
        assert vote.value < 0, f"{reply!r} scored {vote.value:+d} — sign flipped"


# ---------------------------------------------------------------- abstention
def test_empty_reply_is_an_abstention_not_a_neutral_vote() -> None:
    vote, parsed = parse_vote("")
    assert parsed is False
    assert vote is VoteValue.NEUTRAL  # placeholder value; `parsed` is what carries meaning


def test_unreadable_reply_is_an_abstention() -> None:
    _, parsed = parse_vote("I have some concerns but no strong view either way.")
    assert parsed is False


# ---------------------------------------------------------------- consensus impact
def _round(votes: list[AgentVote]) -> DebateRound:
    return DebateRound(round_number=1, topic="t", proposals={}, votes=votes)


def _vote(v: VoteValue, parsed: bool = True) -> AgentVote:
    return AgentVote(role=AgentRole.SYNTHESIZER, vote=v, reasoning="", parsed=parsed)


def test_unanimous_strong_dissent_is_not_consensus() -> None:
    """The headline failure, asserted end-to-end through calculate_consensus."""
    # Parse a real reply rather than constructing the enum directly — the bug was in the
    # PARSER, so a test that hand-builds STRONGLY_DISAGREE would never have caught it.
    parsed_vote, ok = parse_vote("Vote: STRONGLY_DISAGREE\nReasoning: unsafe.")
    assert ok
    votes = [_vote(parsed_vote) for _ in range(5)]
    reached, score = _round(votes).calculate_consensus()
    assert score == pytest.approx(0.0), f"unanimous strong dissent scored {score}"
    assert reached is False


def test_unanimous_strong_agreement_is_consensus() -> None:
    """Discriminating in the other direction: the fix must not block genuine agreement."""
    votes = [_vote(VoteValue.STRONGLY_AGREE) for _ in range(5)]
    reached, score = _round(votes).calculate_consensus()
    assert score == pytest.approx(1.0)
    assert reached is True


def test_abstentions_are_excluded_not_scored_as_neutral() -> None:
    """Two real strong-agree votes plus three abstentions must read as the two real votes,
    not be dragged toward 0.5 by three phantom neutrals."""
    votes = [_vote(VoteValue.STRONGLY_AGREE) for _ in range(2)]
    votes += [_vote(VoteValue.NEUTRAL, parsed=False) for _ in range(3)]
    reached, score = _round(votes).calculate_consensus()
    assert score == pytest.approx(1.0), f"abstentions diluted the score to {score}"
    assert reached is True


def test_all_abstentions_is_not_consensus() -> None:
    """No readable votes is no evidence — it must not read as agreement."""
    votes = [_vote(VoteValue.NEUTRAL, parsed=False) for _ in range(5)]
    reached, score = _round(votes).calculate_consensus()
    assert (reached, score) == (False, 0.0)


def test_existing_votes_without_the_parsed_field_still_count() -> None:
    """Backward compatibility: `parsed` defaults True, so older constructions are counted."""
    v = AgentVote(role=AgentRole.SYNTHESIZER, vote=VoteValue.AGREE, reasoning="")
    assert v.parsed is True
    reached, score = _round([v]).calculate_consensus()
    assert score > 0.5
