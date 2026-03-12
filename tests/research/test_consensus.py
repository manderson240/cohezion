"""Tests for PartyModeConsensus democratic voting system."""

from __future__ import annotations

import pytest

from cohezion.research.consensus import (
    ConsensusResult,
    ConsensusVote,
    PartyModeConsensus,
)


class TestConsensusVote:
    """Tests for ConsensusVote dataclass."""

    @pytest.mark.fast
    def test_vote_creation(self):
        """[VOTE-01] ConsensusVote stores vote data."""
        vote = ConsensusVote(
            voter_id="optimist",
            vote="improve",
            confidence=0.9,
            reasoning="Strong improvement",
        )
        assert vote.voter_id == "optimist"
        assert vote.vote == "improve"
        assert vote.confidence == 0.9
        assert vote.timestamp  # auto-generated


class TestConsensusResult:
    """Tests for ConsensusResult dataclass."""

    @pytest.mark.fast
    def test_result_creation(self):
        """[RESULT-01] ConsensusResult stores voting outcome."""
        result = ConsensusResult(
            proposal="test",
            votes_for=3,
            votes_against=1,
            votes_maintain=1,
            winning_vote="improve",
            confidence=0.8,
            consensus_achieved=True,
        )
        assert result.votes_for == 3
        assert result.votes_maintain == 1
        assert result.consensus_achieved is True


class TestPartyModeConsensus:
    """Tests for PartyModeConsensus voting logic."""

    @pytest.fixture
    def consensus(self):
        return PartyModeConsensus()

    @pytest.mark.fast
    def test_initialization_defaults(self, consensus):
        """[PMC-01] Default config: 3 min agents, 0.66 threshold."""
        assert consensus.min_agents == 3
        assert consensus.consensus_threshold == 0.66
        assert len(consensus.agents) == 5

    @pytest.mark.fast
    def test_strong_improvement_achieves_consensus(self, consensus):
        """[PMC-02] High improvement with low cost gets consensus."""
        metrics = {
            "improvement_pct": 20,
            "cost_usd": 1.0,
            "cv": 0.05,
            "thermodynamic_entropy": 0.1,
            "coherence_mean": 0.8,
        }
        result = consensus.vote("Apply improvement", metrics)
        assert isinstance(result, ConsensusResult)
        assert result.consensus_achieved is True
        assert result.winning_vote == "improve"

    @pytest.mark.fast
    def test_no_improvement_no_consensus_for_improve(self, consensus):
        """[PMC-03] Zero improvement doesn't achieve improve consensus."""
        metrics = {
            "improvement_pct": 0,
            "cost_usd": 10.0,
            "cv": 0.5,
            "thermodynamic_entropy": -0.1,
            "coherence_mean": 0.3,
        }
        result = consensus.vote("No improvement", metrics)
        assert result.winning_vote != "improve"

    @pytest.mark.fast
    def test_quorum_not_met(self):
        """[PMC-04] Below quorum returns no consensus."""
        consensus = PartyModeConsensus(min_agents=10)  # More than available agents
        result = consensus.vote("test", {"improvement_pct": 20})
        assert result.consensus_achieved is False
        assert result.winning_vote == "maintain"

    @pytest.mark.fast
    def test_voting_history_tracked(self, consensus):
        """[PMC-05] Each vote is recorded in history."""
        consensus.vote("First", {"improvement_pct": 20, "cost_usd": 1.0})
        consensus.vote("Second", {"improvement_pct": 5, "cost_usd": 1.0})
        assert len(consensus.voting_history) == 2

    @pytest.mark.fast
    def test_individual_agent_votes(self, consensus):
        """[PMC-06] Each agent produces a valid ConsensusVote."""
        metrics = {"improvement_pct": 12, "cost_usd": 2.0, "cv": 0.05}
        for name, fn in consensus.agents.items():
            vote = fn("test proposal", metrics)
            assert isinstance(vote, ConsensusVote)
            assert vote.voter_id == name
            assert vote.vote in ("improve", "maintain", "revert")
            assert 0.0 <= vote.confidence <= 1.0

    @pytest.mark.fast
    def test_pessimist_needs_strong_evidence(self, consensus):
        """[PMC-07] Pessimist votes revert unless improvement > 15 and cost < 5."""
        weak = consensus._pessimist_vote("test", {"improvement_pct": 10, "cost_usd": 1.0})
        assert weak.vote == "revert"

        strong = consensus._pessimist_vote("test", {"improvement_pct": 20, "cost_usd": 1.0})
        assert strong.vote == "improve"

    @pytest.mark.fast
    def test_economist_efficiency_threshold(self, consensus):
        """[PMC-08] Economist checks improvement-per-dollar ratio."""
        efficient = consensus._economist_vote("test", {"improvement_pct": 20, "cost_usd": 1.0})
        assert efficient.vote == "improve"  # 20% / $1 = 20 efficiency > 5

        wasteful = consensus._economist_vote("test", {"improvement_pct": 2, "cost_usd": 10.0})
        assert wasteful.vote == "maintain"  # 2% / $10 = 0.2 efficiency < 5

    @pytest.mark.fast
    def test_custom_threshold(self):
        """[PMC-09] Custom consensus threshold is respected."""
        strict = PartyModeConsensus(consensus_threshold=1.0)  # Require unanimity
        metrics = {"improvement_pct": 12, "cost_usd": 2.0, "cv": 0.05}
        result = strict.vote("test", metrics)
        # Unlikely to get unanimity with 5 diverse agents
        assert result.consensus_achieved is False
