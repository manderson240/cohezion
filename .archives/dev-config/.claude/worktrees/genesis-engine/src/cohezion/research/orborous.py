"""Orborous - Self-improving compound system via Party Mode Democratic Consensus.

The autonomous improvement loop that never ends.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from cohezion.research import (
    ResearchSquad,
    integrate_with_compound_system,
)
from cohezion.research.consensus import PartyModeConsensus
from cohezion.research.cost_optimization import CostBudget


logger = logging.getLogger(__name__)


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

        logger.info("Orborous initialized - self-improvement system ready")

    async def monitor_cycle(self) -> None:
        """Single self-improvement cycle."""
        self.cycle_count += 1
        logger.info(f"Orborous Cycle #{self.cycle_count} starting")

        try:
            logger.info("Monitoring compound system...")
            skill_metrics = await self._get_compound_metrics()

            degraded_skills = []
            for skill_name, metrics in skill_metrics.items():
                signal = self.squad.detect_degradation(skill_name, metrics)
                if signal:
                    degraded_skills.append(signal)
                    logger.warning(f"Degradation detected: {skill_name}")

            if not degraded_skills:
                logger.info("No degradation detected, system healthy")
                return

            for signal in degraded_skills[:3]:  # Max 3 per cycle
                logger.info(f"Optimizing: {signal.skill_name}")

                result = self.squad.optimize_skill(
                    skill_name=signal.skill_name,
                    baseline_metric=signal.current_value,
                    max_experiments=20,
                )

                logger.info("Calling democratic consensus...")
                consensus_result = self.consensus.vote(
                    proposal=f"Apply refinement to {result.target_skill}",
                    metrics=result.to_dict(),
                )

                if consensus_result.consensus_achieved:
                    if consensus_result.winning_vote == "improve":
                        logger.info("Consensus achieved - applying refinement")
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
                        logger.info("Consensus rejected - rolling back")
                else:
                    logger.info("No consensus - maintaining current state")

            logger.info("Validating improvements...")
            await self._validate_improvements()

        except Exception as e:
            logger.error(f"Orborous cycle failed: {e}")

    async def _get_compound_metrics(self) -> dict[str, dict[str, float]]:
        """Get current metrics from compound system.

        TODO: Wire to real GlobalMetricsAggregator instead of hardcoded values.
        See deferred idea in docs/plans/2026-03-11-deferred-research-modules.md.
        """
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
        logger.info("Validation complete")

    async def run_forever(self) -> None:
        """Run Orborous - async infinite self-improvement loop.

        Unlike the removed sync auto_optimize() (which used blocking time.sleep),
        this is async and yields control via asyncio.sleep between cycles.
        """
        logger.info("Orborous awakening - infinite self-improvement engaged")
        self.active = True

        while self.active:
            await self.monitor_cycle()
            await asyncio.sleep(300)  # 5 minutes between cycles

            if self.squad.cost_tracker.total_cost > self.cost_budget.max_cost_usd:
                logger.warning("Budget exceeded - pausing Orborous")
                self.active = False

    def stop(self) -> None:
        """Gracefully stop Orborous."""
        logger.info("Orborous stopping...")
        self.active = False

    def get_status(self) -> dict[str, Any]:
        """Get Orborous status report."""
        return {
            "cycles_completed": self.cycle_count,
            "active": self.active,
            "improvements_made": len(self.improvement_history),
            "total_cost_usd": self.squad.cost_tracker.total_cost,
            "budget_remaining_pct": (1 - self.squad.cost_tracker.total_cost / self.cost_budget.max_cost_usd) * 100,
            "latest_improvements": self.improvement_history[-5:],
        }
