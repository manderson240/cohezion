"""Quadrature Nexus Scenario Dispatch.

Routes agentic scenarios to the 4 Quadrature Fabrics:
- Space: navigation scenarios (spatial exploration)
- Field: maintenance scenarios (coherence under perturbation)
- Control: judgment scenarios (decision-making under competing objectives)
- Precipitation: interruption scenarios (context recovery)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cohezion.universe.scenarios import Scenario, ScenarioType


logger = logging.getLogger(__name__)

# Fabric mapping: ScenarioType → Quadrature Fabric name
SCENARIO_FABRIC_MAP: dict[ScenarioType, str] = {
    ScenarioType.NAVIGATION: "space",
    ScenarioType.MAINTENANCE: "field",
    ScenarioType.JUDGMENT: "control",
    ScenarioType.INTERRUPTION: "precipitation",
}


@dataclass
class DispatchResult:
    """Result of dispatching a scenario to a fabric."""

    fabric: str
    scenario_type: ScenarioType
    success: bool
    swarm_id: str = ""
    message: str = ""


@dataclass
class NexusScenarioDispatcher:
    """Dispatch scenarios across the 4 Quadrature Fabrics.

    Uses QuadratureNexus for topology management while implementing
    its own scenario routing logic.
    """

    dispatch_log: list[dict[str, str]] = field(default_factory=list)
    nexus: Any = field(default=None)

    def __post_init__(self) -> None:
        """Initialize nexus and fabric swarms."""
        try:
            from cohezion.swarm.executive import QuadratureNexus
            from cohezion.swarm.topology import NodeRole

            self.nexus = QuadratureNexus()
            nexus = self.nexus

            # Create fabric swarms for each quadrature fabric
            for fabric, role in [
                ("space", NodeRole.ENGINEER),
                ("field", NodeRole.BIOLOGIST),
                ("control", NodeRole.ARCHITECT),
                ("precipitation", NodeRole.QUANTUM_HW),
            ]:
                _ = nexus.create_fabric_swarm(fabric, role)
        except Exception:
            # Graceful fallback: dispatcher works without full nexus
            logger.debug("QuadratureNexus unavailable, using lightweight dispatch")
            self.nexus = object()

    def get_fabric_for_type(self, scenario_type: ScenarioType) -> str:
        """Get the fabric name for a scenario type.

        Args:
            scenario_type: The type of scenario

        Returns:
            Fabric name (space, field, control, precipitation)
        """
        return SCENARIO_FABRIC_MAP[scenario_type]

    def dispatch(self, scenario: Scenario) -> DispatchResult:
        """Dispatch a scenario to the appropriate quadrature fabric.

        Args:
            scenario: Scenario to dispatch

        Returns:
            DispatchResult with fabric assignment and status
        """
        fabric = self.get_fabric_for_type(scenario.type)

        # Record dispatch event
        self.dispatch_log.append(
            {
                "scenario": scenario.description,
                "fabric": fabric,
                "type": scenario.type.value,
            }
        )

        # Record via perception layer if available
        self._record_perception(scenario, fabric)

        logger.info(f"Dispatched '{scenario.description}' to {fabric.upper()} fabric")

        return DispatchResult(
            fabric=fabric,
            scenario_type=scenario.type,
            success=True,
            message=f"Routed to {fabric} fabric",
        )

    def dispatch_batch(self, scenarios: list[Scenario]) -> list[DispatchResult]:
        """Dispatch multiple scenarios to their fabrics.

        Args:
            scenarios: List of scenarios to dispatch

        Returns:
            List of DispatchResults
        """
        return [self.dispatch(s) for s in scenarios]

    def _record_perception(self, scenario: Scenario, fabric: str) -> None:
        """Record dispatch event via perception layer (non-blocking).

        Args:
            scenario: Dispatched scenario
            fabric: Target fabric
        """
        try:
            from cohezion.compound.executor_types import ExecutionResult
            from cohezion.compound.journey_tracker import OperationType

            nexus = self.nexus
            if hasattr(nexus, "perception"):
                nexus.perception.perceive_step(  # type: ignore[union-attr]
                    f"Dispatch {scenario.type.value} → {fabric}",
                    ExecutionResult(
                        success=True,
                        output=f"Scenario '{scenario.description}' dispatched",
                        metrics={},
                        duration_seconds=0.01,
                    ),
                    OperationType.TRANSFORM.value,
                )
        except Exception:
            logger.debug("Perception recording skipped", exc_info=True)
