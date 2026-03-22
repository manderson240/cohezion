"""Lifecycle Pre-Simulation (Story 5.8, FR19).

Models the 12D trajectory of a proposed implementation lifecycle
before commit, detecting architectural collisions and "Coherence Debt"
early. Projects where coherence will drop or topological knots will form.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)

COHERENCE_DROP_THRESHOLD = 0.15  # Flag if projected drop > this
KNOT_DISTANCE_THRESHOLD = 0.1  # Flag if trajectory self-intersects within this


@dataclass
class SimulationStep:
    """A single step in the lifecycle pre-simulation."""

    phase: str  # "requirement" | "architecture" | "code" | "test"
    position: list[float]  # 12D coordinate
    coherence: float
    description: str = ""


@dataclass
class TopologicalKnot:
    """A detected self-intersection in the 12D trajectory."""

    step_a: int
    step_b: int
    distance: float
    description: str = ""


@dataclass
class PreSimResult:
    """Result of a lifecycle pre-simulation."""

    plan_id: str
    steps: list[SimulationStep]
    coherence_drops: list[tuple[int, float]]  # (step_index, drop_amount)
    knots: list[TopologicalKnot]
    passed: bool
    blocking_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "steps": len(self.steps),
            "coherence_drops": len(self.coherence_drops),
            "knots": len(self.knots),
            "passed": self.passed,
            "blocking_errors": self.blocking_errors,
        }


class LifecyclePreSimulator:
    """Simulates implementation lifecycle trajectories in 12D space."""

    def __init__(
        self,
        coherence_threshold: float = COHERENCE_DROP_THRESHOLD,
        knot_threshold: float = KNOT_DISTANCE_THRESHOLD,
    ) -> None:
        self._coherence_threshold = coherence_threshold
        self._knot_threshold = knot_threshold

    def simulate(
        self,
        plan_id: str,
        steps: list[SimulationStep],
    ) -> PreSimResult:
        """Run pre-simulation on a proposed lifecycle plan."""
        coherence_drops: list[tuple[int, float]] = []
        blocking_errors: list[str] = []

        # Check coherence drops
        for i in range(1, len(steps)):
            drop = steps[i - 1].coherence - steps[i].coherence
            if drop > self._coherence_threshold:
                coherence_drops.append((i, drop))
                blocking_errors.append(
                    f"Coherence drop at step {i} ({steps[i].phase}): "
                    f"{drop:.3f} > {self._coherence_threshold}"
                )

        # Check topological knots (self-intersections)
        knots = self._detect_knots(steps)
        for knot in knots:
            blocking_errors.append(
                f"Topological knot between steps {knot.step_a} and {knot.step_b}: "
                f"distance {knot.distance:.4f}"
            )

        passed = len(blocking_errors) == 0

        result = PreSimResult(
            plan_id=plan_id,
            steps=steps,
            coherence_drops=coherence_drops,
            knots=knots,
            passed=passed,
            blocking_errors=blocking_errors,
        )

        if not passed:
            logger.warning(
                "Pre-simulation FAILED for %s: %d blocking errors",
                plan_id,
                len(blocking_errors),
            )

        return result

    def _detect_knots(self, steps: list[SimulationStep]) -> list[TopologicalKnot]:
        """Detect topological knots (trajectory self-intersections)."""
        knots: list[TopologicalKnot] = []
        positions = [np.array(s.position) for s in steps]

        for i in range(len(positions)):
            for j in range(i + 2, len(positions)):  # Skip adjacent
                dist = float(np.linalg.norm(positions[i] - positions[j]))
                if dist < self._knot_threshold:
                    knots.append(
                        TopologicalKnot(
                            step_a=i,
                            step_b=j,
                            distance=dist,
                            description=f"{steps[i].phase} collides with {steps[j].phase}",
                        )
                    )
        return knots
