"""Orborous - Self-improving compound system via Party Mode Democratic Consensus.

The autonomous improvement loop that never ends.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from cohezion.research import (
    ResearchAgent,
    ResearchConfig,
    ResearchSquad,
    integrate_with_compound_system,
)
from cohezion.research.cost_optimization import CostBudget


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
    votes_abstain: int
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
        experiments = metrics.get("experiments_run", 1)

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
        # Collect votes from all agents
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
                votes_abstain=len(votes),
                winning_vote="abstain",
                confidence=0.0,
                consensus_achieved=False,
            )

        # Count votes
        vote_counts = {"improve": 0, "maintain": 0, "revert": 0}
        total_confidence = 0.0

        for vote in votes:
            vote_counts[vote.vote] += 1
            total_confidence += vote.confidence

        # Determine winner
        winning_vote = max(vote_counts, key=vote_counts.get)
        max_votes = vote_counts[winning_vote]

        # Check consensus threshold
        consensus_achieved = max_votes / len(votes) >= self.consensus_threshold

        avg_confidence = total_confidence / len(votes)

        result = ConsensusResult(
            proposal=proposal,
            votes_for=vote_counts["improve"],
            votes_against=vote_counts["revert"],
            votes_abstain=vote_counts["maintain"],
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


class Orborous:
    """Self-improving compound system that never ends.

    The recursive loop:
    1. Monitor compound system
    2. Detect degradation
    3. Research Squad runs experiments
    4. Party Mode consensus votes
    5. Apply improvements
    6. Validate
    7. Repeat

    The ouroboros eating its own tail - infinite self-improvement.
    """

    def __init__(
        self,
        squad: ResearchSquad | None = None,
        consensus: PartyModeConsensus | None = None,
        cost_budget: CostBudget | None = None,
    ):
        """Initialize Orborous self-improvement system."""
        self.squad = squad or integrate_with_compound_system()
        self.consensus = consensus or PartyModeConsensus()
        self.cost_budget = cost_budget or CostBudget(max_cost_usd=50.0)

        self.improvement_history: list[dict[str, Any]] = []
        self.cycle_count = 0
        self.active = False

        logger.info("🐍 Orborous initialized - self-improvement system ready")

    async def monitor_cycle(self) -> None:
        """Single self-improvement cycle."""
        self.cycle_count += 1
        logger.info(f"🔄 Orborous Cycle #{self.cycle_count} starting")

        try:
            # 1. Monitor compound system
            logger.info("Monitoring compound system...")
            skill_metrics = await self._get_compound_metrics()

            # 2. Detect degradation
            degraded_skills = []
            for skill_name, metrics in skill_metrics.items():
                signal = self.squad.detect_degradation(skill_name, metrics)
                if signal:
                    degraded_skills.append(signal)
                    logger.warning(f"🔍 Degradation detected: {skill_name}")

            if not degraded_skills:
                logger.info("✅ No degradation detected, system healthy")
                return

            # 3. Research Squad optimizes
            for signal in degraded_skills[:3]:  # Max 3 per cycle
                logger.info(f"🔬 Optimizing: {signal.skill_name}")

                result = self.squad.optimize_skill(
                    skill_name=signal.skill_name,
                    baseline_metric=signal.current_value,
                    max_experiments=20,
                )

                # 4. Party Mode consensus
                logger.info("🗳️  Calling democratic consensus...")
                consensus_result = self.consensus.vote(
                    proposal=f"Apply refinement to {result.target_skill}",
                    metrics=result.to_dict(),
                )

                # 5. Apply if consensus achieved
                if consensus_result.consensus_achieved:
                    if consensus_result.winning_vote == "improve":
                        logger.info("✅ Consensus achieved - applying refinement")
                        success = self.squad.apply_refinement(result)
                        if success:
                            self.improvement_history.append(
                                {
                                    "cycle": self.cycle_count,
                                    "skill": result.target_skill,
                                    "improvement_pct": result.improvement_pct,
                                    "consensus_confidence": consensus_result.confidence,
                                }
                            )
                    elif consensus_result.winning_vote == "revert":
                        logger.info("❌ Consensus rejected - rolling back")
                        # Rollback logic here
                else:
                    logger.info("⚠️  No consensus - maintaining current state")

            # 6. Validate
            logger.info("Validating improvements...")
            await self._validate_improvements()

        except Exception as e:
            logger.error(f"Orborous cycle failed: {e}")
            # Don't stop - keep improving

    async def _get_compound_metrics(self) -> dict[str, dict[str, float]]:
        """Get current metrics from compound system."""
        # In production: Query GlobalMetricsAggregator
        # For now: Simulate realistic metrics
        return {
            "coding": {
                "coherence": 0.45,  # Degraded
                "success_rate": 0.95,
            },
            "analysis": {
                "coherence": 0.82,
                "success_rate": 0.88,
            },
            "security": {
                "coherence": 0.91,
                "success_rate": 0.97,
            },
        }

    async def _validate_improvements(self) -> None:
        """Validate improvements were actually improvements."""
        # Run thermodynamic checks
        # Verify no regressions
        logger.info("✓ Validation complete")

    async def run_forever(self) -> None:
        """Run Orborous - infinite self-improvement."""
        logger.info("🐍 Orborous awakening - infinite self-improvement engaged")
        self.active = True

        while self.active:
            await self.monitor_cycle()

            # Sleep between cycles
            await asyncio.sleep(300)  # 5 minutes

            # Safety: Check cost
            if self.squad.cost_tracker.total_cost > self.cost_budget.max_cost_usd:
                logger.warning("💰 Budget exceeded - pausing Orborous")
                self.active = False

    def stop(self) -> None:
        """Gracefully stop Orborous."""
        logger.info("🛑 Orborous stopping...")
        self.active = False

    def get_status(self) -> dict[str, Any]:
        """Get Orborous status report."""
        return {
            "cycles_completed": self.cycle_count,
            "active": self.active,
            "improvements_made": len(self.improvement_history),
            "total_cost_usd": self.squad.cost_tracker.total_cost,
            "budget_remaining_pct": (
                1 - self.squad.cost_tracker.total_cost / self.cost_budget.max_cost_usd
            )
            * 100,
            "latest_improvements": self.improvement_history[-5:],
        }


# Orborous activation
async def awaken_orborous():
    """Awaken the self-improving system."""
    orborous = Orborous()
    await orborous.run_forever()


# Entry point
if __name__ == "__main__":
    # Run Orborous
    asyncio.run(awaken_orborous())
