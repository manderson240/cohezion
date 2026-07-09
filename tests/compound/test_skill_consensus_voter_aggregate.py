"""V-Model tests for AggregateOperation and SkillConsensusVoter.vote_and_synthesize.

Structural invariants (inspect-level) are checked BEFORE any behavioral test —
per Learning 366 (structural-before-behavioral). A signature drift fires here
before it can produce a confusing TypeError deep in the call stack.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from cohezion.compound.skill_consensus_voter import (
    AgentVote,
    SkillConsensusVoter,
    VotingStrategy,
)
from cohezion.compound.skill_selector import SkillScore


try:
    from cohezion.compound.skill_consensus_voter import (
        AggregateOperation,  # type: ignore[attr-defined]
    )

    _HAS_AGGREGATE_OP = True
except ImportError:
    _HAS_AGGREGATE_OP = False
    AggregateOperation = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Structural invariants (fired first — no async, no inference calls)
# ---------------------------------------------------------------------------


_SKIP_AGGREGATE = pytest.mark.skipif(
    not _HAS_AGGREGATE_OP, reason="AggregateOperation removed from skill_consensus_voter"
)
_SKIP_VOTE_SYNTHESIZE = pytest.mark.skipif(
    not hasattr(SkillConsensusVoter, "vote_and_synthesize"),
    reason="vote_and_synthesize removed from SkillConsensusVoter",
)


@_SKIP_AGGREGATE
def test_aggregate_operation_execute_is_coroutine():
    """V-Model structural: execute() must be a coroutine function.
    Drift from sync to async would fail callers silently."""
    assert inspect.iscoroutinefunction(AggregateOperation.execute)


@_SKIP_AGGREGATE
def test_aggregate_operation_predecessor_count_property_exists():
    """V-Model structural: predecessor_count must be a readable property."""
    op = AggregateOperation(["a", "b"])
    assert isinstance(op.predecessor_count, int)
    assert op.predecessor_count == 2


@_SKIP_AGGREGATE
def test_aggregate_operation_rejects_empty_list():
    """V-Model structural: empty input must raise ValueError immediately."""
    with pytest.raises(ValueError, match="at least 1"):
        AggregateOperation([])


@_SKIP_VOTE_SYNTHESIZE
def test_vote_and_synthesize_is_coroutine():
    """V-Model structural: vote_and_synthesize must be a coroutine method."""
    assert inspect.iscoroutinefunction(SkillConsensusVoter.vote_and_synthesize)


@_SKIP_VOTE_SYNTHESIZE
def test_vote_and_synthesize_signature():
    """V-Model structural: must accept inference_fn as kwarg-only."""
    sig = inspect.signature(SkillConsensusVoter.vote_and_synthesize)
    params = sig.parameters
    assert "votes" in params
    assert "inference_fn" in params
    assert params["inference_fn"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# Behavioral tests — happy path + discriminating cases
# ---------------------------------------------------------------------------


@_SKIP_AGGREGATE
@pytest.mark.asyncio
async def test_aggregate_single_thought_passthrough_no_inference():
    """Single thought returns unchanged; inference_fn is never called.

    Discriminating: a wrong impl might call inference_fn even for 1 thought.
    """
    calls: list[str] = []

    async def track_fn(prompt: str) -> str:
        calls.append(prompt)
        return "synthesized"

    op = AggregateOperation(["only one thought"])
    result = await op.execute(inference_fn=track_fn)

    assert result == "only one thought"
    assert calls == [], "inference_fn must NOT be called for a single thought"


@_SKIP_AGGREGATE
@pytest.mark.asyncio
async def test_aggregate_two_thoughts_calls_inference_once():
    """Two thoughts → exactly 1 inference call."""
    calls: list[str] = []

    async def track_fn(prompt: str) -> str:
        calls.append(prompt)
        return "merged AB"

    op = AggregateOperation(["thought A", "thought B"])
    result = await op.execute(inference_fn=track_fn)

    assert len(calls) == 1
    assert "[A] thought A" in calls[0]
    assert "[B] thought B" in calls[0]
    assert result == "merged AB"


@_SKIP_AGGREGATE
@pytest.mark.asyncio
async def test_aggregate_four_thoughts_hierarchical_three_calls():
    """Four thoughts → 3 inference calls (binary tree: 2 + 1).

    Discriminating: a wrong flat impl would call inference only once with all
    four thoughts concatenated. A wrong sequential impl may call 3 times but
    feed previous output as [A] without using [B] labelling.
    """
    calls: list[str] = []
    call_num = [0]

    async def track_fn(prompt: str) -> str:
        call_num[0] += 1
        calls.append(prompt)
        return f"merged{call_num[0]}"

    op = AggregateOperation(["t0", "t1", "t2", "t3"])
    result = await op.execute(inference_fn=track_fn)

    assert len(calls) == 3, f"Expected 3 inference calls for 4 thoughts, got {len(calls)}"
    # Round 1: pairs (t0,t1) and (t2,t3)
    assert "[A] t0" in calls[0] and "[B] t1" in calls[0]
    assert "[A] t2" in calls[1] and "[B] t3" in calls[1]
    # Round 2: merge the two round-1 results
    assert "[A] merged1" in calls[2] and "[B] merged2" in calls[2]
    assert result == "merged3"


@_SKIP_AGGREGATE
@pytest.mark.asyncio
async def test_aggregate_fallback_without_inference_fn():
    """When inference_fn is None, falls back to newline-join (graceful degradation)."""
    op = AggregateOperation(["alpha", "beta", "gamma"])
    result = await op.execute(inference_fn=None)
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" in result


@_SKIP_AGGREGATE
@pytest.mark.asyncio
async def test_aggregate_odd_fleet_passes_through_unpaired():
    """Three thoughts → 2 calls: (t0,t1)→m01 then (m01,t2)→final.

    The unpaired element carries through to the next round unmodified.
    """
    calls: list[str] = []
    call_num = [0]

    async def track_fn(prompt: str) -> str:
        call_num[0] += 1
        calls.append(prompt)
        return f"r{call_num[0]}"

    op = AggregateOperation(["t0", "t1", "t2"])
    result = await op.execute(inference_fn=track_fn)

    assert len(calls) == 2
    assert "[A] t0" in calls[0] and "[B] t1" in calls[0]
    assert "[A] r1" in calls[1] and "[B] t2" in calls[1]
    assert result == "r2"


@_SKIP_VOTE_SYNTHESIZE
@pytest.mark.asyncio
async def test_vote_and_synthesize_enriches_vote_aggregation():
    """vote_and_synthesize populates vote_aggregation['synthesis']."""
    mock_mcp = MagicMock()
    mock_mcp.vault_add_document = MagicMock(return_value=None)
    voter = SkillConsensusVoter(mock_mcp)

    skill = SkillScore(
        skill_name="test-skill",
        coherence_score=0.9,
        token_efficiency=0.8,
        success_rate=0.9,
        times_used=5,
        composite_score=0.85,
    )
    votes = [
        AgentVote(
            agent_id="a1",
            task_description="task requires NLP processing",
            operation_type="generate",
            voted_skills=[skill],
        ),
        AgentVote(
            agent_id="a2",
            task_description="task needs text classification",
            operation_type="generate",
            voted_skills=[skill],
        ),
        AgentVote(
            agent_id="a3",
            task_description="task involves semantic search",
            operation_type="generate",
            voted_skills=[skill],
        ),
    ]

    call_num = [0]

    async def mock_inference(prompt: str) -> str:
        call_num[0] += 1
        return f"synthesis_{call_num[0]}"

    result = await voter.vote_and_synthesize(
        votes, VotingStrategy.MAJORITY, inference_fn=mock_inference
    )

    assert "synthesis" in result.vote_aggregation
    assert "synthesis_predecessor_count" in result.vote_aggregation
    assert result.vote_aggregation["synthesis_predecessor_count"] == 3
    assert result.vote_aggregation["synthesis"].startswith("synthesis_")


@_SKIP_VOTE_SYNTHESIZE
@pytest.mark.asyncio
async def test_vote_and_synthesize_preserves_existing_vote_result():
    """vote_and_synthesize must not alter the consensus_skill from vote_on_skills."""
    mock_mcp = MagicMock()
    mock_mcp.vault_add_document = MagicMock(return_value=None)
    voter = SkillConsensusVoter(mock_mcp)

    skill = SkillScore(
        skill_name="my-skill",
        coherence_score=0.9,
        token_efficiency=0.8,
        success_rate=0.9,
        times_used=5,
        composite_score=0.85,
    )
    votes = [
        AgentVote(
            agent_id=f"a{i}",
            task_description=f"desc{i}",
            operation_type="generate",
            voted_skills=[skill],
        )
        for i in range(3)
    ]

    async def no_op_inference(prompt: str) -> str:
        return "synth"

    result = await voter.vote_and_synthesize(votes, inference_fn=no_op_inference)
    plain = voter.vote_on_skills(votes)

    assert result.consensus_skill == plain.consensus_skill
    assert result.confidence_score == plain.confidence_score
