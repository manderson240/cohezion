"""Multi-agent skill selection via consensus voting.

Implements distributed skill selection where N agents vote on top-k skills
using multiple voting strategies: majority, weighted (by agent coherence history),
and unanimous consensus.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from cohezion.compound.skill_selector import SkillScore
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


class VotingStrategy(Enum):
    """Supported voting strategies for skill consensus."""

    MAJORITY = "majority"  # >50% agreement
    WEIGHTED = "weighted"  # Weighted by agent coherence history
    UNANIMOUS = "unanimous"  # 100% agreement required


@dataclass
class AgentVote:
    """Single agent's vote on skills for a task."""

    agent_id: str
    task_description: str
    operation_type: str
    voted_skills: list[SkillScore]  # Ranked skills from this agent
    agent_coherence_score: float = 0.5  # Historical coherence for weighting
    timestamp: datetime = field(default_factory=datetime.now)

    def __repr__(self) -> str:
        """Readable representation."""
        skills_str = ", ".join(s.skill_name for s in self.voted_skills[:3])
        return f"AgentVote(agent={self.agent_id}, skills=[{skills_str}...], coherence={self.agent_coherence_score:.2f})"


@dataclass
class ConsensusResult:
    """Result of skill consensus voting."""

    consensus_skill: SkillScore | None  # Winning skill
    confidence_score: float  # 0.0-1.0, how confident in result
    strategy_used: VotingStrategy
    votes_for_consensus: int  # How many agents agreed
    total_votes: int  # Total agents that voted
    runner_up_skill: SkillScore | None = None  # Second-place skill
    fallback_used: bool = False  # True if consensus failed, used fallback
    vote_aggregation: dict[str, Any] = field(default_factory=dict)  # Debug info

    def __repr__(self) -> str:
        """Readable representation."""
        skill_name = self.consensus_skill.skill_name if self.consensus_skill else "NONE"
        return (
            f"ConsensusResult(skill={skill_name}, "
            f"confidence={self.confidence_score:.2f}, "
            f"votes={self.votes_for_consensus}/{self.total_votes}, "
            f"strategy={self.strategy_used.value}, "
            f"fallback={self.fallback_used})"
        )


class SkillConsensusVoter:
    """Multi-agent skill selection via consensus voting.

    Aggregates skill votes from N agents using multiple strategies:
    - MAJORITY: >50% agreement on a skill
    - WEIGHTED: Weighted by each agent's coherence history
    - UNANIMOUS: All agents must agree

    Falls back to single-best if consensus fails.
    Persists voting metrics to vault (non-blocking).

    Example:
        ```python
        voter = SkillConsensusVoter(mcp_client)

        # Collect votes from 3 agents
        votes = [
            AgentVote(agent_id="agent1", ...voted_skills=[skill1, skill2]...),
            AgentVote(agent_id="agent2", ...voted_skills=[skill2, skill1]...),
            AgentVote(agent_id="agent3", ...voted_skills=[skill1, skill2]...),
        ]

        # Run consensus
        result = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)
        # Returns consensus_skill=skill1 (2/3 agents agreed)
        ```
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        project: str = "cohezion",
    ):
        """Initialize skill consensus voter.

        Args:
            mcp_client: Connected MCPClient for vault operations
            project: Project name for vault operations
        """
        self.mcp_client = mcp_client
        self.project = project
        logger.debug(
            "Initialized SkillConsensusVoter for project=%s",
            project,
        )

    def vote_on_skills(
        self,
        votes: list[AgentVote],
        strategy: VotingStrategy = VotingStrategy.MAJORITY,
        require_agreement_threshold: float = 0.5,
    ) -> ConsensusResult:
        """Run consensus voting on skill selections.

        Args:
            votes: List of AgentVote objects from agents
            strategy: Voting strategy to use
            require_agreement_threshold: Minimum fraction for consensus
                - MAJORITY: default 0.5 (>50%)
                - WEIGHTED: default 0.5 (sum of weights >50%)
                - UNANIMOUS: default 1.0 (all agents)

        Returns:
            ConsensusResult with winning skill and confidence score

        Performance:
            O(N*K) where N=number of agents, K=top-k skills
            Typical: <10ms for 5 agents × 5 skills
        """
        if not votes:
            logger.warning("No votes provided to consensus voter")
            return ConsensusResult(
                consensus_skill=None,
                confidence_score=0.0,
                strategy_used=strategy,
                votes_for_consensus=0,
                total_votes=0,
                fallback_used=True,
            )

        logger.info(
            "Running %s consensus on %d agent votes",
            strategy.value,
            len(votes),
        )

        # Run voting strategy
        if strategy == VotingStrategy.MAJORITY:
            result = self._vote_majority(votes, require_agreement_threshold)
        elif strategy == VotingStrategy.WEIGHTED:
            result = self._vote_weighted(votes, require_agreement_threshold)
        elif strategy == VotingStrategy.UNANIMOUS:
            result = self._vote_unanimous(votes)
        else:
            logger.error("Unknown voting strategy: %s", strategy)
            result = self._fallback_single_best(votes)
            result.fallback_used = True

        # Persist metrics non-blocking
        self._persist_voting_metrics(votes, result, strategy)

        return result

    def _vote_majority(
        self,
        votes: list[AgentVote],
        threshold: float = 0.5,
    ) -> ConsensusResult:
        """Majority voting: >threshold fraction of agents agree on a skill.

        Args:
            votes: Agent votes
            threshold: Minimum fraction (default 0.5 for >50%)

        Returns:
            ConsensusResult
        """
        # Count votes per skill (1st choice only)
        skill_votes = {}
        for vote in votes:
            if vote.voted_skills:
                top_skill = vote.voted_skills[0]
                if top_skill.skill_name not in skill_votes:
                    skill_votes[top_skill.skill_name] = {
                        "count": 0,
                        "skill": top_skill,
                        "agents": [],
                    }
                skill_votes[top_skill.skill_name]["count"] += 1
                skill_votes[top_skill.skill_name]["agents"].append(vote.agent_id)

        # Find skill with most votes
        if not skill_votes:
            return self._fallback_single_best(votes)

        sorted_skills = sorted(
            skill_votes.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )

        _best_skill_name, best_data = sorted_skills[0]
        vote_fraction = best_data["count"] / len(votes)

        # Check if threshold met (strictly greater for majority)
        consensus_achieved = vote_fraction > threshold

        # Get runner-up
        runner_up = None
        if len(sorted_skills) > 1:
            runner_up = sorted_skills[1][1]["skill"]

        result = ConsensusResult(
            consensus_skill=best_data["skill"] if consensus_achieved else None,
            confidence_score=vote_fraction,
            strategy_used=VotingStrategy.MAJORITY,
            votes_for_consensus=best_data["count"],
            total_votes=len(votes),
            runner_up_skill=runner_up,
            fallback_used=not consensus_achieved,
            vote_aggregation={
                "skill_votes": {k: v["count"] for k, v in skill_votes.items()},
                "threshold": threshold,
                "voted_agents": best_data["agents"],
            },
        )

        if not consensus_achieved:
            logger.warning(
                "Majority consensus failed (%.1f%% < %.1f%%). Using fallback.",
                vote_fraction * 100,
                threshold * 100,
            )
            result = self._fallback_single_best(votes)
            result.fallback_used = True

        return result

    def _vote_weighted(
        self,
        votes: list[AgentVote],
        threshold: float = 0.5,
    ) -> ConsensusResult:
        """Weighted voting: agents' votes weighted by their coherence history.

        Higher coherence agents' votes count more.

        Args:
            votes: Agent votes with coherence_score
            threshold: Minimum weight fraction (default 0.5)

        Returns:
            ConsensusResult
        """
        # Calculate skill weights
        skill_weights = {}
        total_weight = 0.0

        for vote in votes:
            agent_weight = vote.agent_coherence_score  # 0.0-1.0
            total_weight += agent_weight

            if vote.voted_skills:
                top_skill = vote.voted_skills[0]
                if top_skill.skill_name not in skill_weights:
                    skill_weights[top_skill.skill_name] = {
                        "weight": 0.0,
                        "skill": top_skill,
                        "voters": [],
                    }
                skill_weights[top_skill.skill_name]["weight"] += agent_weight
                skill_weights[top_skill.skill_name]["voters"].append((vote.agent_id, agent_weight))

        if not skill_weights or total_weight == 0:
            return self._fallback_single_best(votes)

        # Find skill with most weight
        sorted_skills = sorted(
            skill_weights.items(),
            key=lambda x: x[1]["weight"],
            reverse=True,
        )

        _best_skill_name, best_data = sorted_skills[0]
        weight_fraction = best_data["weight"] / total_weight if total_weight > 0 else 0

        consensus_achieved = weight_fraction > threshold

        # Get runner-up
        runner_up = None
        if len(sorted_skills) > 1:
            runner_up = sorted_skills[1][1]["skill"]

        result = ConsensusResult(
            consensus_skill=best_data["skill"] if consensus_achieved else None,
            confidence_score=weight_fraction,
            strategy_used=VotingStrategy.WEIGHTED,
            votes_for_consensus=len(best_data["voters"]),
            total_votes=len(votes),
            runner_up_skill=runner_up,
            fallback_used=not consensus_achieved,
            vote_aggregation={
                "skill_weights": {k: v["weight"] for k, v in skill_weights.items()},
                "total_weight": total_weight,
                "threshold": threshold,
                "voter_weights": {
                    name: {
                        "weight": best_data["weight"],
                        "voters": best_data["voters"],
                    }
                    for name, best_data in skill_weights.items()
                },
            },
        )

        if not consensus_achieved:
            logger.warning(
                "Weighted consensus failed (%.1f%% < %.1f%%). Using fallback.",
                weight_fraction * 100,
                threshold * 100,
            )
            result = self._fallback_single_best(votes)
            result.fallback_used = True

        return result

    def _vote_unanimous(self, votes: list[AgentVote]) -> ConsensusResult:
        """Unanimous voting: all agents must vote for the same skill.

        Args:
            votes: Agent votes

        Returns:
            ConsensusResult
        """
        if not votes:
            return self._fallback_single_best(votes)

        # Get first agent's top skill
        first_skill = votes[0].voted_skills[0] if votes[0].voted_skills else None
        if not first_skill:
            return self._fallback_single_best(votes)

        # Check if all agents voted for this skill
        unanimous = all(
            (vote.voted_skills and vote.voted_skills[0].skill_name == first_skill.skill_name) for vote in votes
        )

        result = ConsensusResult(
            consensus_skill=first_skill if unanimous else None,
            confidence_score=1.0 if unanimous else 0.0,
            strategy_used=VotingStrategy.UNANIMOUS,
            votes_for_consensus=len(votes) if unanimous else 0,
            total_votes=len(votes),
            runner_up_skill=None,
            fallback_used=not unanimous,
            vote_aggregation={
                "unanimous": unanimous,
                "agreed_skill": first_skill.skill_name if unanimous else None,
                "disagreed_agents": [
                    vote.agent_id
                    for vote in votes
                    if not (vote.voted_skills and vote.voted_skills[0].skill_name == first_skill.skill_name)
                ]
                if not unanimous
                else [],
            },
        )

        if not unanimous:
            logger.warning("Unanimous consensus failed. Agents disagreed. Using fallback.")
            result = self._fallback_single_best(votes)
            result.fallback_used = True

        return result

    def _fallback_single_best(self, votes: list[AgentVote]) -> ConsensusResult:
        """Fallback: select single best skill from all votes.

        Uses composite scoring across all agent votes to pick best skill overall.

        Args:
            votes: Agent votes

        Returns:
            ConsensusResult with fallback flag set
        """
        if not votes:
            return ConsensusResult(
                consensus_skill=None,
                confidence_score=0.0,
                strategy_used=VotingStrategy.MAJORITY,
                votes_for_consensus=0,
                total_votes=0,
                fallback_used=True,
            )

        # Collect all skills with weights
        skill_scores_weighted = {}
        for vote in votes:
            for rank, skill in enumerate(vote.voted_skills):
                # Weight by rank (first choice worth more)
                # and by agent coherence
                rank_weight = 1.0 / (rank + 1)  # 1.0 for 1st, 0.5 for 2nd, etc.
                agent_weight = vote.agent_coherence_score

                if skill.skill_name not in skill_scores_weighted:
                    skill_scores_weighted[skill.skill_name] = {
                        "skill": skill,
                        "total_score": 0.0,
                        "count": 0,
                    }

                skill_scores_weighted[skill.skill_name]["total_score"] += rank_weight * agent_weight
                skill_scores_weighted[skill.skill_name]["count"] += 1

        # Handle case where no skills were collected
        if not skill_scores_weighted:
            return ConsensusResult(
                consensus_skill=None,
                confidence_score=0.0,
                strategy_used=VotingStrategy.MAJORITY,
                votes_for_consensus=0,
                total_votes=len(votes),
                fallback_used=True,
            )

        # Find highest scoring skill
        best_skill_entry = max(
            skill_scores_weighted.values(),
            key=lambda x: x["total_score"],
        )
        best_skill = best_skill_entry["skill"]

        # Confidence is proportional to score
        max_possible_score = len(votes) * 1.0  # All agents vote for skill in 1st place
        confidence = best_skill_entry["total_score"] / max_possible_score

        result = ConsensusResult(
            consensus_skill=best_skill,
            confidence_score=confidence,
            strategy_used=VotingStrategy.MAJORITY,  # Report original strategy
            votes_for_consensus=best_skill_entry["count"],
            total_votes=len(votes),
            fallback_used=True,
            vote_aggregation={
                "all_skills": {name: entry["total_score"] for name, entry in skill_scores_weighted.items()},
                "max_possible_score": max_possible_score,
            },
        )

        logger.info(
            "Fallback: Selected %s (score=%.2f) from %d skills",
            best_skill.skill_name,
            best_skill_entry["total_score"],
            len(skill_scores_weighted),
        )

        return result

    def _persist_voting_metrics(
        self,
        votes: list[AgentVote],
        result: ConsensusResult,
        strategy: VotingStrategy,
    ) -> None:
        """Persist voting metrics to vault (non-blocking).

        Records voting outcomes for analysis and improvement.

        Args:
            votes: Agent votes
            result: Consensus result
            strategy: Strategy used
        """
        try:
            if not self.mcp_client:
                return

            # Build voting record
            voting_record = {
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy.value,
                "num_agents": len(votes),
                "consensus_skill": (result.consensus_skill.skill_name if result.consensus_skill else None),
                "confidence": result.confidence_score,
                "consensus_achieved": not result.fallback_used,
                "fallback_used": result.fallback_used,
                "votes_for_consensus": result.votes_for_consensus,
                "total_votes": result.total_votes,
                "agent_ids": [vote.agent_id for vote in votes],
                "vote_aggregation": dict(result.vote_aggregation.items()),
            }

            # Persist to vault with vault_add_document
            self.mcp_client.vault_add_document(
                title=f"voting-consensus-{strategy.value}-{datetime.now().isoformat()}",
                content=json.dumps(voting_record, indent=2, default=str),
                document_type="voting_metric",
                tags=[
                    "consensus",
                    strategy.value,
                    "skill_selection",
                ],
                project=self.project,
            )

            logger.debug(
                "Persisted voting metrics: strategy=%s, consensus=%s, confidence=%.2f",
                strategy.value,
                result.consensus_skill.skill_name if result.consensus_skill else "NONE",
                result.confidence_score,
            )

        except Exception as e:
            # Non-blocking: log and continue
            logger.debug(
                "Failed to persist voting metrics (non-blocking): %s",
                e,
            )

    def get_voting_stats(self) -> dict[str, Any]:
        """Get statistics on voting outcomes.

        Would query vault for voting records and compute aggregates.
        Stub for now - vault integration handles actual querying.

        Returns:
            Dictionary with voting statistics
        """
        return {
            "message": "Voting statistics - would query vault for historical data",
            "note": "Use MCPClient.vault_find_relevant_context with 'voting' tags",
        }
