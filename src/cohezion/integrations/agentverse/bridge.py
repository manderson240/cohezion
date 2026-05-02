"""AgentVerseBridge - Protocol bridge between AgentVerse and Cohezion.

Connects AgentVerse agent message protocol to Cohezion's CompoundExecutor
for coherence-aware multi-agent execution with vault integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)

HIHO_LOW = 0.4
HIHO_HIGH = 0.6


@dataclass
class CoherenceViolation:
    """Represents a HIHO band violation."""

    agent: str
    coherence: float
    severity: str
    message: str


@dataclass
class AgentVerseBridge:
    """Bridge connecting AgentVerse messages to Cohezion's compound executor.

    This bridge enables AgentVerse multi-agent protocols to leverage
    Cohezion's coherence tracking, HIHO band monitoring, and vault
    persistence.

    Parameters
    ----------
    executor : Any
        CompoundExecutor instance for task execution
    model_router : Any, optional
        Optional model router for skill selection

    Attributes
    ----------
    metrics : list[dict]
        Tracks coherence metrics from each agent execution
    """

    executor: Any
    model_router: Any | None = None
    metrics: list[dict[str, Any]] = field(default_factory=list)

    def on_agent_message(
        self,
        agent_name: str,
        message: str,
        skill_name: str,
    ) -> Any:
        """Handle an AgentVerse agent message through Cohezion's executor.

        Parameters
        ----------
        agent_name : str
            Name of the agent sending the message
        message : str
            Message content from the agent
        skill_name : str
            Cohezion skill to use for execution

        Returns
        -------
        Any
            Execution result from CompoundExecutor
        """
        logger.info(
            "Bridge routing message from agent=%s skill=%s",
            agent_name,
            skill_name,
        )

        result = self.executor.execute_task(
            task_description=message,
            skill_name=skill_name,
            operation_type="generate",
        )

        self.metrics.append(
            {
                "agent": agent_name,
                "skill": skill_name,
                "coherence": result.metrics.get("coherence", 0.5),
                "alignment": result.metrics.get("alignment", {}),
                "success": result.success,
                "duration_seconds": result.duration_seconds,
            }
        )

        return result

    def route_message(
        self,
        agent_name: str,
        message: str,
    ) -> dict[str, Any]:
        """Route a message to appropriate model/executor.

        Parameters
        ----------
        agent_name : str
            Name of the agent
        message : str
            Message to route

        Returns
        -------
        dict[str, Any]
            Routing decision with model and skill
        """
        if self.model_router:
            model = self.model_router.select_model(message)
            return {"model": model, "agent": agent_name}

        return {"model": "default", "agent": agent_name}

    def get_coherence_trajectory(self) -> list[dict[str, Any]]:
        """Get the coherence trajectory across all agent executions.

        Returns
        -------
        list[dict[str, Any]]
            List of coherence metrics over time
        """
        return list(self.metrics)

    def get_average_coherence(self) -> float:
        """Compute average coherence across all executions.

        Returns
        -------
        float
            Average coherence score
        """
        if not self.metrics:
            return 0.0

        coherences = [m["coherence"] for m in self.metrics if "coherence" in m]
        if not coherences:
            return 0.0

        return sum(coherences) / len(coherences)

    def check_hiho_violations(self) -> list[CoherenceViolation]:
        """Check for HIHO band violations.

        HIHO band is [0.4, 0.6] - coherence outside this range
        indicates degraded system performance.

        Returns
        -------
        list[CoherenceViolation]
            List of detected violations
        """
        violations = []

        for m in self.metrics:
            coherence = m.get("coherence", 0.5)
            agent = m.get("agent", "unknown")

            if coherence < HIHO_LOW:
                violations.append(
                    CoherenceViolation(
                        agent=agent,
                        coherence=coherence,
                        severity="CRITICAL" if coherence < 0.3 else "WARNING",
                        message=f"Coherence {coherence:.2f} below HIHO band ({HIHO_LOW})",
                    )
                )
            elif coherence > HIHO_HIGH:
                violations.append(
                    CoherenceViolation(
                        agent=agent,
                        coherence=coherence,
                        severity="WARNING",
                        message=f"Coherence {coherence:.2f} above HIHO band ({HIHO_HIGH})",
                    )
                )

        return violations

    def reset(self) -> None:
        """Clear all metrics (for new benchmark run)."""
        self.metrics = []

    def log_inflection_to_vault(self, violation: CoherenceViolation) -> str:
        """Log a critical inflection point to vault.

        Parameters
        ----------
        violation : CoherenceViolation
            The violation to log

        Returns
        -------
        str
            Path to vault log entry
        """
        logger.warning(
            "Critical inflection: agent=%s coherence=%.2f",
            violation.agent,
            violation.coherence,
        )
        return f"/vault/inflections/{violation.agent}_{violation.severity}"

    def export_trajectory(self) -> dict[str, Any]:
        """Export trajectory data for vault persistence.

        Returns
        -------
        dict[str, Any]
            Trajectory data with metrics and trend
        """
        trajectory = {
            "metrics": list(self.metrics),
            "coherence_trend": [m["coherence"] for m in self.metrics],
            "average_coherence": self.get_average_coherence(),
            "violation_count": len(self.check_hiho_violations()),
        }
        return trajectory
