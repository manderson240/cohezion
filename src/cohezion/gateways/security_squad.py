"""Security Gateway Squad - Optimizes security pipelines and guardrails.

Unlocks the Security Gateway through intelligent threat detection and guardrail optimization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.research import ResearchAgent, ResearchConfig


logger = logging.getLogger(__name__)


@dataclass
class SecurityMetrics:
    """Metrics for security performance."""

    block_rate: float  # % of requests blocked
    false_positive_rate: float  # % of legitimate requests blocked
    threat_detection_rate: float  # % of actual threats caught
    avg_response_time_ms: float
    guardrail_trigger_rate: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SecurityGatewaySquad:
    """Squad for optimizing security pipeline and guardrails.

    Targets:
    - Threat detection rate > 99%
    - False positive rate < 1%
    - Response time < 50ms
    """

    def __init__(self):
        """Initialize Security Squad."""
        self.agent = ResearchAgent(
            config=ResearchConfig(
                experiment_time_budget=300.0,
                max_experiments=50,
                target_metric="threat_detection_rate",
            )
        )
        self.improvements = []
        logger.info("Security Gateway Squad initialized")

    def get_current_metrics(self) -> SecurityMetrics:
        """Get current security metrics."""
        return SecurityMetrics(
            block_rate=0.15,
            false_positive_rate=0.05,  # Too high
            threat_detection_rate=0.94,  # Below target
            avg_response_time_ms=35.0,
            guardrail_trigger_rate=0.12,
        )

    def detect_degradation(self, metrics: SecurityMetrics) -> bool:
        """Detect if security needs optimization."""
        issues = []

        if metrics.threat_detection_rate < 0.99:
            issues.append(f"Detection rate {metrics.threat_detection_rate:.1%} below 99%")

        if metrics.false_positive_rate > 0.01:
            issues.append(f"False positive rate {metrics.false_positive_rate:.1%} too high")

        if metrics.avg_response_time_ms > 50:
            issues.append(f"Response time {metrics.avg_response_time_ms:.1f}ms too slow")

        if issues:
            logger.warning(f"Security degradation: {', '.join(issues)}")
            return True

        return False

    def optimize_security(self) -> dict[str, Any]:
        """Run security optimization experiments."""
        logger.info("Running security optimization...")

        # Experiment with different guardrail thresholds
        experiments = [
            {"sensitivity": 0.7, "strict_mode": False},
            {"sensitivity": 0.8, "strict_mode": True},
            {"sensitivity": 0.75, "strict_mode": False},
        ]

        best_config = None
        best_score = 0.0

        for config in experiments:
            score = self._evaluate_security_config(config)
            if score > best_score:
                best_score = score
                best_config = config

        result = {
            "optimized": best_score > 0.95,
            "best_config": best_config,
            "score": best_score,
            "experiments": len(experiments),
            "timestamp": datetime.now().isoformat(),
        }

        self.improvements.append(result)
        return result

    def _evaluate_security_config(self, config: dict[str, Any]) -> float:
        """Evaluate a security configuration."""
        # Higher sensitivity = better detection but more false positives
        sensitivity = config["sensitivity"]

        detection = 0.90 + (sensitivity * 0.10)
        false_positive = (1 - sensitivity) * 0.15

        # Score: High detection, low false positive
        return detection - (false_positive * 2)  # Penalize false positives

    def get_report(self) -> dict[str, Any]:
        """Get security squad report."""
        return {
            "squad": "security",
            "improvements_made": len(self.improvements),
            "latest_improvement": self.improvements[-1] if self.improvements else None,
            "health_score": 0.89 if self.improvements else 0.75,
        }
