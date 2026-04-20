"""Consensus - Democratic voting system for autonomous compound improvements.

PartyModeConsensus runs multiple agent perspectives in parallel and
requires a configurable supermajority before applying any change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ConsensusVote:
    """Individual vote in democratic consensus."""

    voter_id: str
    vote: str  # "improve", "maintain", "revert"
    confidence: float  # 0.0 - 1.0
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConsensusResult:
    """Result of democratic consensus."""

    proposal: str
    votes_for: int
    votes_against: int
    votes_maintain: int
    winning_vote: str
    confidence: float
    consensus_achieved: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PartyModeConsensus:
    """Democratic consensus system for autonomous improvements.

    Multiple agents vote on whether to apply improvements.
    No single point of failure.
    """

    def __init__(self, min_agents: int = 3, consensus_threshold: float = 0.66):
        """Initialize consensus system.

        Args:
            min_agents: Minimum agents needed for quorum
            consensus_threshold: % of votes needed for consensus
        """
        self.min_agents = min_agents
        self.consensus_threshold = consensus_threshold
        self.voting_history: list[ConsensusResult] = []

        # Party agents with different perspectives
        self.agents = {
            "optimist": self._optimist_vote,
            "pessimist": self._pessimist_vote,
            "pragmatist": self._pragmatist_vote,
            "thermodynamicist": self._thermodynamicist_vote,
            "economist": self._economist_vote,
        }

    def _optimist_vote(self, proposal: str, metrics: dict[str, Any]) -> ConsensusVote:
        """Optimist agent - votes for improvement if any benefit."""
        improvement = metrics.get("improvement_pct", 0)
        if improvement > 5:
            return ConsensusVote(
                voter_id="optimist",
                vote="improve",
                confidence=min(improvement / 10, 1.0),
                reasoning=f"{improvement:.1f}% improvement detected",
            )
        return ConsensusVote(
            voter_id="optimist",
            vote="maintain",
            confidence=0.5,
            reasoning="No significant improvement",
        )

    def _pessimist_vote(self, proposal: str, metrics: dict[str, Any]) -> ConsensusVote:
        """Pessimist agent - cautious, needs strong evidence."""
        improvement = metrics.get("improvement_pct", 0)
        cost = metrics.get("cost_usd", 0)

        if improvement > 15 and cost < 5:
            return ConsensusVote(
                voter_id="pessimist",
                vote="improve",
                confidence=0.7,
                reasoning="Strong improvement with low cost",
            )
        return ConsensusVote(
            voter_id="pessimist",
            vote="revert",
            confidence=0.8,
            reasoning="Insufficient evidence or too expensive",
        )

    def _pragmatist_vote(self, proposal: str, metrics: dict[str, Any]) -> ConsensusVote:
        """Pragmatist agent - balances risk and reward."""
        improvement = metrics.get("improvement_pct", 0)
        reproducibility = metrics.get("cv", 1.0)  # Coefficient of variation

        if improvement > 10 and reproducibility < 0.1:
            return ConsensusVote(
                voter_id="pragmatist",
                vote="improve",
                confidence=0.85,
                reasoning="Reproducible 10%+ improvement",
            )
        return ConsensusVote(
            voter_id="pragmatist",
            vote="maintain",
            confidence=0.6,
            reasoning="Not reproducible enough",
        )

    def _thermodynamicist_vote(self, proposal: str, metrics: dict[str, Any]) -> ConsensusVote:
        """Thermodynamicist agent - cares about system stability."""
        entropy = metrics.get("thermodynamic_entropy", 0)
        coherence = metrics.get("coherence_mean", 0)

        if entropy > 0 and coherence > 0.6:
            return ConsensusVote(
                voter_id="thermodynamicist",
                vote="improve",
                confidence=min(coherence, 1.0),
                reasoning=f"Entropy positive ({entropy:.3f}), coherence high ({coherence:.2f})",
            )
        return ConsensusVote(
            voter_id="thermodynamicist",
            vote="revert",
            confidence=0.9,
            reasoning="Thermodynamic instability detected",
        )

    def _economist_vote(self, proposal: str, metrics: dict[str, Any]) -> ConsensusVote:
        """Economist agent - cares about cost efficiency."""
        improvement = metrics.get("improvement_pct", 0)
        cost = metrics.get("cost_usd", 0)

        efficiency = improvement / max(cost, 0.01)  # Improvement per dollar

        if efficiency > 5:  # >5% per dollar
            return ConsensusVote(
                voter_id="economist",
                vote="improve",
                confidence=min(efficiency / 10, 1.0),
                reasoning=f"Efficient: {efficiency:.1f}% per ${cost:.2f}",
            )
        return ConsensusVote(
            voter_id="economist",
            vote="maintain",
            confidence=0.7,
            reasoning=f"Low efficiency: {efficiency:.1f}% per ${cost:.2f}",
        )

    def vote(self, proposal: str, metrics: dict[str, Any]) -> ConsensusResult:
        """Run democratic consensus on proposal.

        Args:
            proposal: Description of proposed change
            metrics: Dict of metrics to evaluate

        Returns:
            ConsensusResult with voting outcome
        """
        votes = []
        for agent_name, vote_fn in self.agents.items():
            try:
                vote = vote_fn(proposal, metrics)
                votes.append(vote)
                logger.info(f"Agent {agent_name} voted: {vote.vote} ({vote.confidence:.2f})")
            except Exception as e:
                logger.warning(f"Agent {agent_name} failed to vote: {e}")

        if len(votes) < self.min_agents:
            return ConsensusResult(
                proposal=proposal,
                votes_for=0,
                votes_against=0,
                votes_maintain=len(votes),
                winning_vote="maintain",
                confidence=0.0,
                consensus_achieved=False,
            )

        vote_counts: dict[str, int] = {"improve": 0, "maintain": 0, "revert": 0}
        total_confidence = 0.0

        for vote in votes:
            vote_counts[vote.vote] += 1
            total_confidence += vote.confidence

        winning_vote = max(vote_counts, key=lambda k: vote_counts[k])
        max_votes = vote_counts[winning_vote]
        consensus_achieved = max_votes / len(votes) >= self.consensus_threshold
        avg_confidence = total_confidence / len(votes)

        result = ConsensusResult(
            proposal=proposal,
            votes_for=vote_counts["improve"],
            votes_against=vote_counts["revert"],
            votes_maintain=vote_counts["maintain"],
            winning_vote=winning_vote,
            confidence=avg_confidence,
            consensus_achieved=consensus_achieved,
        )

        self.voting_history.append(result)

        logger.info(
            f"Consensus result: {winning_vote} "
            f"({max_votes}/{len(votes)} votes, "
            f"consensus={'achieved' if consensus_achieved else 'failed'})"
        )

        return result
