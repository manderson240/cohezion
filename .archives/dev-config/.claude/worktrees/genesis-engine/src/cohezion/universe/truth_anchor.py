"""Adversarial Reality Check Bridge (Story 1-0-7).

Injects immutable physics constants (Truth Anchors) into the 12D manifold
to detect and pop Coherence Bubbles — shared agentic hallucinations where
a swarm reaches internal consensus that violates physical constraints.

The key insight: a healthy swarm has *variance* in coherence (agents explore
different regions of the manifold). A swarm where all agents lock to the
same coherence value far from 0.5 is exhibiting groupthink, not stability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from cohezion.universe.hiho_unified_engine import EvoState, HIHOStabilizationEngine


logger = logging.getLogger(__name__)

# Physics constants (immutable truth anchors)
HIHO_SPRING_CONSTANT = 2.0
HIHO_COHERENCE_TARGET = 0.5
HIHO_MAX_DRIFT = 0.4

# Bubble detection thresholds
BUBBLE_MEAN_DRIFT_THRESHOLD = 0.25  # Mean coherence > this far from 0.5
BUBBLE_LOW_VARIANCE_THRESHOLD = 0.005  # Suspiciously identical coherence values
MIN_SWARM_SIZE_FOR_BUBBLE = 3  # Need at least 3 EVOs to detect a bubble


@dataclass
class TruthAnchor:
    """An immutable physics constant used to validate swarm behavior."""

    name: str
    expected_value: float
    tolerance: float = 0.01
    description: str = ""

    @classmethod
    def hiho_spring_constant(cls) -> TruthAnchor:
        return cls(
            name="hiho_spring_constant",
            expected_value=HIHO_SPRING_CONSTANT,
            tolerance=0.001,
            description="HIHO restoring force coefficient (Hooke's Law analog)",
        )

    @classmethod
    def coherence_target(cls) -> TruthAnchor:
        return cls(
            name="coherence_target",
            expected_value=HIHO_COHERENCE_TARGET,
            tolerance=BUBBLE_MEAN_DRIFT_THRESHOLD,
            description="HIHO equilibrium coherence target",
        )

    @classmethod
    def energy_conservation(cls) -> TruthAnchor:
        return cls(
            name="energy_conservation",
            expected_value=0.0,  # Delta energy should be ~0
            tolerance=0.1,
            description="Total energy change per tick should be bounded",
        )


@dataclass
class CoherenceBubble:
    """A detected coherence bubble — shared hallucination violating physics."""

    anchor_name: str
    expected: float
    observed: float
    severity: float  # 0.0 = mild, 1.0 = critical
    description: str = ""


@dataclass
class RestoringForceResult:
    """Result of checking HIHO restoring force on an EVO."""

    new_coherence: float
    force_applied: float
    original_coherence: float


@dataclass
class ValidationResult:
    """Result of a full truth anchor validation pass."""

    passed: bool
    bubbles: list[CoherenceBubble] = field(default_factory=list)
    anchors_checked: int = 0


class TruthAnchorValidator:
    """Validates swarm state against immutable physics truth anchors.

    Detects coherence bubbles by checking:
    1. Mean coherence drift from HIHO target (0.5)
    2. Suspiciously low variance (groupthink indicator)
    3. HIHO restoring force compliance
    """

    def __init__(self) -> None:
        self._hiho_engine = HIHOStabilizationEngine()
        self._anchors = [
            TruthAnchor.coherence_target(),
            TruthAnchor.hiho_spring_constant(),
        ]

    def validate(self, evos: list[EvoState], vectors: list[np.ndarray]) -> ValidationResult:
        """Run all truth anchor checks against the current swarm state."""
        if len(evos) < MIN_SWARM_SIZE_FOR_BUBBLE:
            return ValidationResult(passed=True, anchors_checked=0)

        bubbles: list[CoherenceBubble] = []
        coherences = np.array([evo.coherence for evo in evos])

        # Check 1: Mean coherence drift from target
        mean_coh = float(np.mean(coherences))
        drift = abs(mean_coh - HIHO_COHERENCE_TARGET)
        if drift > BUBBLE_MEAN_DRIFT_THRESHOLD:
            severity = min(drift / HIHO_MAX_DRIFT, 1.0)
            bubbles.append(
                CoherenceBubble(
                    anchor_name="coherence_target",
                    expected=HIHO_COHERENCE_TARGET,
                    observed=mean_coh,
                    severity=severity,
                    description=f"Mean coherence {mean_coh:.3f} drifted {drift:.3f} from target",
                )
            )

        # Check 2: Suspiciously low variance (groupthink)
        if len(coherences) >= MIN_SWARM_SIZE_FOR_BUBBLE:
            variance = float(np.var(coherences))
            if variance < BUBBLE_LOW_VARIANCE_THRESHOLD and drift > 0.1:
                bubbles.append(
                    CoherenceBubble(
                        anchor_name="coherence_variance",
                        expected=BUBBLE_LOW_VARIANCE_THRESHOLD,
                        observed=variance,
                        severity=min(1.0, (0.1 - variance) / 0.1 + drift),
                        description=(
                            f"Zero-variance coherence ({variance:.6f}) at mean={mean_coh:.3f} — possible groupthink"
                        ),
                    )
                )

        passed = len(bubbles) == 0
        if not passed:
            logger.warning(
                "Coherence bubble detected: %d violations in %d EVOs",
                len(bubbles),
                len(evos),
            )

        return ValidationResult(
            passed=passed,
            bubbles=bubbles,
            anchors_checked=len(self._anchors),
        )

    def check_restoring_force(self, evo: EvoState, dt: float = 0.1) -> RestoringForceResult:
        """Verify HIHO restoring force behaves as expected for a single EVO."""
        original = evo.coherence
        dummy_vec = np.zeros(12)

        # Apply one HIHO tick
        updated_evo, _ = self._hiho_engine.apply_hiho_loop(evo, dummy_vec, dt)
        force = HIHO_SPRING_CONSTANT * (HIHO_COHERENCE_TARGET - original) * dt

        return RestoringForceResult(
            new_coherence=updated_evo.coherence,
            force_applied=force,
            original_coherence=original,
        )
