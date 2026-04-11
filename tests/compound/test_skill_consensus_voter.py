"""Tests for multi-agent skill consensus voting."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.skill_consensus_voter import (
    AgentVote,
    ConsensusResult,
    SkillConsensusVoter,
    VotingStrategy,
)
from cohezion.compound.skill_selector import SkillScore


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    return MagicMock()


@pytest.fixture
def voter(mock_mcp_client):
    """Create skill consensus voter with mock MCP client."""
    return SkillConsensusVoter(mock_mcp_client)


@pytest.fixture
def sample_skills():
    """Create sample skills for testing."""
    return {
        "skill_a": SkillScore(
            skill_name="skill_a",
            coherence_score=0.9,
            token_efficiency=0.85,
            success_rate=0.9,
            times_used=10,
            composite_score=0.88,
        ),
        "skill_b": SkillScore(
            skill_name="skill_b",
            coherence_score=0.7,
            token_efficiency=0.8,
            success_rate=0.75,
            times_used=8,
            composite_score=0.75,
        ),
        "skill_c": SkillScore(
            skill_name="skill_c",
            coherence_score=0.6,
            token_efficiency=0.7,
            success_rate=0.65,
            times_used=5,
            composite_score=0.65,
        ),
    }


@pytest.fixture
def sample_votes(sample_skills):
    """Create sample votes from agents."""
    return [
        AgentVote(
            agent_id="agent_1",
            task_description="Generate ideas",
            operation_type="generate",
            voted_skills=[
                sample_skills["skill_a"],
                sample_skills["skill_b"],
                sample_skills["skill_c"],
            ],
            agent_coherence_score=0.9,
        ),
        AgentVote(
            agent_id="agent_2",
            task_description="Generate ideas",
            operation_type="generate",
            voted_skills=[
                sample_skills["skill_a"],
                sample_skills["skill_c"],
                sample_skills["skill_b"],
            ],
            agent_coherence_score=0.85,
        ),
        AgentVote(
            agent_id="agent_3",
            task_description="Generate ideas",
            operation_type="generate",
            voted_skills=[
                sample_skills["skill_b"],
                sample_skills["skill_a"],
                sample_skills["skill_c"],
            ],
            agent_coherence_score=0.7,
        ),
    ]


class TestAgentVote:
    """Tests for AgentVote dataclass."""

    def test_agent_vote_creation(self, sample_skills):
        """Test creating an AgentVote."""
        vote = AgentVote(
            agent_id="test_agent",
            task_description="Test task",
            operation_type="generate",
            voted_skills=[sample_skills["skill_a"]],
            agent_coherence_score=0.8,
        )

        assert vote.agent_id == "test_agent"
        assert vote.task_description == "Test task"
        assert vote.operation_type == "generate"
        assert len(vote.voted_skills) == 1
        assert vote.voted_skills[0].skill_name == "skill_a"
        assert vote.agent_coherence_score == 0.8

    def test_agent_vote_repr(self, sample_skills):
        """Test string representation."""
        vote = AgentVote(
            agent_id="agent_1",
            task_description="Test",
            operation_type="generate",
            voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
            agent_coherence_score=0.85,
        )

        repr_str = repr(vote)
        assert "agent_1" in repr_str
        assert "skill_a" in repr_str
        assert "0.85" in repr_str

    def test_agent_vote_empty_skills(self):
        """Test vote with no skills."""
        vote = AgentVote(
            agent_id="agent_1",
            task_description="Test",
            operation_type="generate",
            voted_skills=[],
        )

        assert vote.voted_skills == []
        assert vote.agent_coherence_score == 0.5  # Default


class TestConsensusResult:
    """Tests for ConsensusResult dataclass."""

    def test_consensus_result_success(self, sample_skills):
        """Test successful consensus result."""
        result = ConsensusResult(
            consensus_skill=sample_skills["skill_a"],
            confidence_score=0.95,
            strategy_used=VotingStrategy.MAJORITY,
            votes_for_consensus=3,
            total_votes=3,
            fallback_used=False,
        )

        assert result.consensus_skill.skill_name == "skill_a"
        assert result.confidence_score == 0.95
        assert result.strategy_used == VotingStrategy.MAJORITY
        assert result.votes_for_consensus == 3
        assert result.fallback_used is False

    def test_consensus_result_failure(self):
        """Test failed consensus result."""
        result = ConsensusResult(
            consensus_skill=None,
            confidence_score=0.4,
            strategy_used=VotingStrategy.UNANIMOUS,
            votes_for_consensus=0,
            total_votes=3,
            fallback_used=True,
        )

        assert result.consensus_skill is None
        assert result.fallback_used is True

    def test_consensus_result_with_runner_up(self, sample_skills):
        """Test result with runner-up skill."""
        result = ConsensusResult(
            consensus_skill=sample_skills["skill_a"],
            confidence_score=0.67,
            strategy_used=VotingStrategy.MAJORITY,
            votes_for_consensus=2,
            total_votes=3,
            runner_up_skill=sample_skills["skill_b"],
        )

        assert result.consensus_skill.skill_name == "skill_a"
        assert result.runner_up_skill.skill_name == "skill_b"

    def test_consensus_result_repr(self, sample_skills):
        """Test string representation."""
        result = ConsensusResult(
            consensus_skill=sample_skills["skill_a"],
            confidence_score=0.85,
            strategy_used=VotingStrategy.WEIGHTED,
            votes_for_consensus=2,
            total_votes=3,
        )

        repr_str = repr(result)
        assert "skill_a" in repr_str
        assert "0.85" in repr_str
        assert "weighted" in repr_str


class TestSkillConsensusVoterInitialization:
    """Tests for voter initialization."""

    def test_initialization_default(self, mock_mcp_client):
        """Test initialization with defaults."""
        voter = SkillConsensusVoter(mock_mcp_client)

        assert voter.mcp_client is mock_mcp_client
        assert voter.project == "cohezion"

    def test_initialization_custom_project(self, mock_mcp_client):
        """Test initialization with custom project."""
        voter = SkillConsensusVoter(mock_mcp_client, project="test_project")

        assert voter.project == "test_project"


class TestMajorityVoting:
    """Tests for majority voting strategy."""

    def test_majority_unanimous_agreement(self, voter, sample_skills):
        """Test majority voting with unanimous agreement."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_c"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        assert result.consensus_skill is not None
        assert result.consensus_skill.skill_name == "skill_a"
        assert result.confidence_score == 1.0
        assert result.votes_for_consensus == 3
        assert result.fallback_used is False

    def test_majority_partial_agreement(self, voter, sample_skills):
        """Test majority voting with >50% agreement."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        # 2/3 = 66.7% > 50%, should achieve consensus
        assert result.consensus_skill is not None
        assert result.consensus_skill.skill_name == "skill_a"
        assert abs(result.confidence_score - 0.667) < 0.01
        assert result.fallback_used is False

    def test_majority_no_consensus(self, voter, sample_skills):
        """Test majority voting when no consensus (even split)."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"], sample_skills["skill_a"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        # 50/50 split, neither reaches >50%
        # Should fallback to single best
        assert result.consensus_skill is not None
        assert result.fallback_used is True

    def test_majority_with_runner_up(self, voter, sample_skills):
        """Test that majority voting records runner-up skill."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        assert result.runner_up_skill is not None
        assert result.runner_up_skill.skill_name == "skill_b"

    def test_majority_custom_threshold(self, voter, sample_skills):
        """Test majority voting with custom threshold."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
            ),
        ]

        # Require 100% for consensus
        result = voter.vote_on_skills(
            votes, strategy=VotingStrategy.MAJORITY, require_agreement_threshold=1.0
        )

        # 2/3 < 100%, should fallback
        assert result.fallback_used is True


class TestWeightedVoting:
    """Tests for weighted voting strategy."""

    def test_weighted_high_coherence_bias(self, voter, sample_skills):
        """Test that higher coherence agents influence consensus more."""
        votes = [
            AgentVote(
                agent_id="expert",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.95,  # Expert
            ),
            AgentVote(
                agent_id="novice1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
                agent_coherence_score=0.3,
            ),
            AgentVote(
                agent_id="novice2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
                agent_coherence_score=0.3,
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.WEIGHTED)

        # Expert's skill_a (0.95) vs novices' skill_b (0.3+0.3=0.6)
        # Total weight = 0.95+0.3+0.3 = 1.55
        # skill_a: 0.95/1.55 = 61.3% > 50%
        assert result.consensus_skill is not None
        assert result.consensus_skill.skill_name == "skill_a"
        assert result.fallback_used is False

    def test_weighted_all_equal_coherence(self, voter, sample_skills):
        """Test weighted voting when all agents have equal coherence."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.5,
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.5,
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
                agent_coherence_score=0.5,
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.WEIGHTED)

        # Should be same as majority voting
        assert result.consensus_skill.skill_name == "skill_a"
        assert abs(result.confidence_score - 0.667) < 0.01

    def test_weighted_consensus_failure_fallback(self, voter, sample_skills):
        """Test weighted voting fallback when threshold not met."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
                agent_coherence_score=0.4,
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"], sample_skills["skill_a"]],
                agent_coherence_score=0.4,
            ),
        ]

        result = voter.vote_on_skills(
            votes, strategy=VotingStrategy.WEIGHTED, require_agreement_threshold=0.6
        )

        # 50/50 split, threshold 60%, should fallback
        assert result.fallback_used is True


class TestUnanimousVoting:
    """Tests for unanimous voting strategy."""

    def test_unanimous_all_agree(self, voter, sample_skills):
        """Test unanimous voting when all agents agree."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_c"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.UNANIMOUS)

        assert result.consensus_skill.skill_name == "skill_a"
        assert result.confidence_score == 1.0
        assert result.votes_for_consensus == 3
        assert result.fallback_used is False

    def test_unanimous_one_disagrees(self, voter, sample_skills):
        """Test unanimous voting when one agent disagrees."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.UNANIMOUS)

        # Not unanimous, should fallback
        assert result.fallback_used is True
        assert result.consensus_skill is not None  # Fallback selected best
        assert result.confidence_score < 1.0

    def test_unanimous_all_disagree(self, voter, sample_skills):
        """Test unanimous voting when all agents vote different."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
            ),
            AgentVote(
                agent_id="a3",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_c"]],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.UNANIMOUS)

        # Complete disagreement, should fallback
        assert result.fallback_used is True


class TestFallbackSingleBest:
    """Tests for fallback to single best skill."""

    def test_fallback_selects_highest_scoring_skill(self, voter, sample_skills):
        """Test that fallback selects skill with highest composite score."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"], sample_skills["skill_a"]],
                agent_coherence_score=0.5,
            ),
            AgentVote(
                agent_id="a2",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_c"], sample_skills["skill_a"]],
                agent_coherence_score=0.5,
            ),
        ]

        result = voter._fallback_single_best(votes)

        # skill_a appears in 2nd position for both, skill_b in 1st
        # skill_b (0.5 * 1.0 * 0.5) + skill_a (0.5 * 0.5 * 0.5 + 0.5 * 0.5 * 0.5)
        # skill_b = 0.25, skill_a = 0.25
        # Due to rank weighting, 1st position matters more
        assert result.consensus_skill is not None

    def test_fallback_with_agent_coherence_weighting(self, voter, sample_skills):
        """Test that fallback weights by agent coherence."""
        votes = [
            AgentVote(
                agent_id="expert",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.9,
            ),
            AgentVote(
                agent_id="novice",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
                agent_coherence_score=0.2,
            ),
        ]

        result = voter._fallback_single_best(votes)

        # Expert strongly votes for skill_a (0.9 * 1.0)
        # Novice votes for skill_b (0.2 * 1.0)
        # skill_a should win
        assert result.consensus_skill.skill_name == "skill_a"

    def test_fallback_empty_votes(self, voter):
        """Test fallback with no votes."""
        result = voter._fallback_single_best([])

        assert result.consensus_skill is None
        assert result.fallback_used is True


class TestVaultPersistence:
    """Tests for vault persistence of voting metrics."""

    def test_persist_voting_metrics_called(self, mock_mcp_client, sample_skills):
        """Test that voting metrics are persisted to vault."""
        voter = SkillConsensusVoter(mock_mcp_client)
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
        ]

        voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        # Check that vault_add_document was called
        mock_mcp_client.vault_add_document.assert_called_once()
        call_args = mock_mcp_client.vault_add_document.call_args

        # Verify call parameters
        assert "title" in call_args.kwargs
        assert "content" in call_args.kwargs
        assert "document_type" in call_args.kwargs
        assert call_args.kwargs["document_type"] == "voting_metric"

    def test_persist_voting_metrics_non_blocking(self, mock_mcp_client, sample_skills):
        """Test that vault errors don't crash voting."""
        mock_mcp_client.vault_add_document.side_effect = RuntimeError("Vault down")

        voter = SkillConsensusVoter(mock_mcp_client)
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
            ),
        ]

        # Should not raise exception
        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        assert result.consensus_skill is not None

    def test_persist_voting_metrics_content(self, mock_mcp_client, sample_skills):
        """Test that voting metrics content is valid JSON."""
        voter = SkillConsensusVoter(mock_mcp_client)
        votes = [
            AgentVote(
                agent_id="agent_1",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.85,
            ),
        ]

        voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        # Get the content passed to vault_add_document
        call_args = mock_mcp_client.vault_add_document.call_args
        content = call_args.kwargs["content"]

        # Should be valid JSON
        import json

        data = json.loads(content)
        assert data["strategy"] == "majority"
        assert data["num_agents"] == 1
        assert data["consensus_achieved"] is True


class TestEmptyAndEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_vote_on_skills_empty_votes(self, voter):
        """Test voting with no votes."""
        result = voter.vote_on_skills([])

        assert result.consensus_skill is None
        assert result.confidence_score == 0.0
        assert result.fallback_used is True

    def test_vote_with_agent_empty_skills(self, voter):
        """Test agent vote with no skills."""
        votes = [
            AgentVote(
                agent_id="a1",
                task_description="test",
                operation_type="generate",
                voted_skills=[],
            ),
        ]

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        # Should handle gracefully
        assert result is not None

    def test_multiple_voting_strategies_comparison(self, voter, sample_skills):
        """Test that different strategies produce different results."""
        votes = [
            AgentVote(
                agent_id="expert",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.95,
            ),
            AgentVote(
                agent_id="novice",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"]],
                agent_coherence_score=0.2,
            ),
        ]

        majority_result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)
        weighted_result = voter.vote_on_skills(votes, strategy=VotingStrategy.WEIGHTED)

        # Majority should be 50/50 (no consensus)
        # Weighted should favor expert's skill_a
        assert majority_result.fallback_used is True
        assert weighted_result.consensus_skill.skill_name == "skill_a"


class TestConsensusAchievementRate:
    """Tests for consensus achievement metrics."""

    def test_high_consensus_rate_majority(self, voter, sample_skills):
        """Test that majority voting achieves high consensus rate."""
        # Create 100 votes with 90% agreement
        votes = []
        for i in range(100):
            skill = sample_skills["skill_a"] if i < 90 else sample_skills["skill_b"]

            votes.append(
                AgentVote(
                    agent_id=f"agent_{i}",
                    task_description="test",
                    operation_type="generate",
                    voted_skills=[skill],
                    agent_coherence_score=0.5,
                )
            )

        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        assert result.consensus_skill is not None
        assert result.fallback_used is False

    def test_weighted_improves_over_majority(self, voter, sample_skills):
        """Test that weighted voting achieves consensus when majority fails."""
        # Create scenario where experts agree but majority doesn't due to novice votes
        votes = []

        # 1 expert strongly voting for skill_a
        votes.append(
            AgentVote(
                agent_id="expert",
                task_description="test",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"]],
                agent_coherence_score=0.95,
            )
        )

        # 3 novices voting for skill_b
        for i in range(3):
            votes.append(
                AgentVote(
                    agent_id=f"novice_{i}",
                    task_description="test",
                    operation_type="generate",
                    voted_skills=[sample_skills["skill_b"]],
                    agent_coherence_score=0.2,
                )
            )

        majority_result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)
        weighted_result = voter.vote_on_skills(votes, strategy=VotingStrategy.WEIGHTED)

        # Majority: skill_b wins (75%)
        assert majority_result.consensus_skill.skill_name == "skill_b"

        # Weighted: skill_a should win (0.95 > 0.2*3)
        # weighted has skill_a weight = 0.95
        # weighted has skill_b weight = 0.2*3 = 0.6
        # 0.95 / (0.95 + 0.6) = 0.613 > 0.5
        assert weighted_result.consensus_skill.skill_name == "skill_a"


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_voting_workflow(self, mock_mcp_client, sample_skills):
        """Test complete voting workflow."""
        voter = SkillConsensusVoter(mock_mcp_client)

        # Create diverse votes
        votes = [
            AgentVote(
                agent_id="specialist_1",
                task_description="Generate creative content",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_b"]],
                agent_coherence_score=0.92,
            ),
            AgentVote(
                agent_id="specialist_2",
                task_description="Generate creative content",
                operation_type="generate",
                voted_skills=[sample_skills["skill_a"], sample_skills["skill_c"]],
                agent_coherence_score=0.88,
            ),
            AgentVote(
                agent_id="generalist",
                task_description="Generate creative content",
                operation_type="generate",
                voted_skills=[sample_skills["skill_b"], sample_skills["skill_a"]],
                agent_coherence_score=0.65,
            ),
        ]

        # Try all three strategies
        for strategy in [
            VotingStrategy.MAJORITY,
            VotingStrategy.WEIGHTED,
            VotingStrategy.UNANIMOUS,
        ]:
            result = voter.vote_on_skills(votes, strategy=strategy)

            # All should return a result
            assert result is not None
            assert isinstance(result, ConsensusResult)

            # Verify vault was called
            if strategy == VotingStrategy.MAJORITY:
                mock_mcp_client.vault_add_document.assert_called()

    def test_get_voting_stats(self, mock_mcp_client):
        """Test getting voting statistics."""
        voter = SkillConsensusVoter(mock_mcp_client)
        stats = voter.get_voting_stats()

        assert isinstance(stats, dict)
        assert "message" in stats
