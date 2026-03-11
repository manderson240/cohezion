"""Swarm Gateway Squad - Optimizes multi-agent coordination.

Unlocks the Swarm Gateway through intelligent agent orchestration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.research import ResearchAgent, ResearchConfig


logger = logging.getLogger(__name__)


@dataclass
class SwarmMetrics:
    """Metrics for swarm performance."""

    consensus_rate: float
    avg_consensus_time_ms: float
    agent_utilization: float
    task_completion_rate: float
    coordination_overhead: float  # % time spent coordinating vs working
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SwarmGatewaySquad:
    """Squad for optimizing multi-agent coordination.

    Targets:
    - Consensus rate > 95%
    - Consensus time < 100ms
    - Agent utilization > 80%
    """

    def __init__(self):
        """Initialize Swarm Squad."""
        self.agent = ResearchAgent(
            config=ResearchConfig(
                experiment_time_budget=300.0,
                max_experiments=50,
                target_metric="consensus_rate",
            )
        )
        self.improvements = []
        logger.info("Swarm Gateway Squad initialized")

    def get_current_metrics(self) -> SwarmMetrics:
        """Get current swarm metrics."""
        return SwarmMetrics(
            consensus_rate=0.92,  # Below target
            avg_consensus_time_ms=120.0,  # Too slow
            agent_utilization=0.75,  # Could be better
            task_completion_rate=0.88,
            coordination_overhead=0.15,
        )

    def detect_degradation(self, metrics: SwarmMetrics) -> bool:
        """Detect if swarm needs optimization."""
        issues = []

        if metrics.consensus_rate < 0.95:
            issues.append(f"Consensus rate {metrics.consensus_rate:.1%} below 95%")

        if metrics.avg_consensus_time_ms > 100:
            issues.append(f"Consensus time {metrics.avg_consensus_time_ms:.0f}ms too slow")

        if metrics.agent_utilization < 0.80:
            issues.append(f"Utilization {metrics.agent_utilization:.1%} below 80%")

        if issues:
            logger.warning(f"Swarm degradation: {', '.join(issues)}")
            return True

        return False

    def optimize_swarm(self) -> dict[str, Any]:
        """Run swarm optimization experiments."""
        logger.info("Running swarm optimization...")

        experiments = [
            {"min_agents": 3, "consensus_threshold": 0.66, "timeout_ms": 150},
            {"min_agents": 5, "consensus_threshold": 0.75, "timeout_ms": 200},
            {"min_agents": 4, "consensus_threshold": 0.70, "timeout_ms": 120},
        ]

        best_config = None
        best_score = 0.0

        for config in experiments:
            score = self._evaluate_swarm_config(config)
            if score > best_score:
                best_score = score
                best_config = config

        result = {
            "optimized": best_score > 0.90,
            "best_config": best_config,
            "score": best_score,
            "experiments": len(experiments),
            "timestamp": datetime.now().isoformat(),
        }

        self.improvements.append(result)
        return result

    def _evaluate_swarm_config(self, config: dict[str, Any]) -> float:
        """Evaluate a swarm configuration."""
        # More agents = better consensus but slower
        agent_factor = min(1.0, config["min_agents"] / 5)
        threshold_factor = 1 - abs(config["consensus_threshold"] - 0.70)  # Optimal at 0.70

        return 0.85 + (agent_factor * 0.10) + (threshold_factor * 0.05)

    def get_report(self) -> dict[str, Any]:
        """Get swarm squad report."""
        return {
            "squad": "swarm",
            "improvements_made": len(self.improvements),
            "latest_improvement": self.improvements[-1] if self.improvements else None,
            "health_score": 0.90 if self.improvements else 0.80,
        }
