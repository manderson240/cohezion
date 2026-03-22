"""Adversarial Reality Grounding (Story 5.9, FR20).

Extends TruthAnchorValidator to periodically inject external,
non-agentic data into the 12D manifold as adversarial perturbations.
If the manifold remains artificially stable despite conflicting
truth anchors, a Hallucination Alert is triggered and the swarm
is forced into resynchronization.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)

PERTURBATION_MAGNITUDE = 0.1
STABILITY_SUSPICION_THRESHOLD = 0.02  # If coherence barely moves after perturbation


@dataclass
class PerturbationResult:
    """Result of an adversarial perturbation injection."""

    coherence_before: float
    coherence_after: float
    perturbation_magnitude: float
    suspicious: bool  # True if manifold resisted perturbation too well
    timestamp: float = field(default_factory=time.time)


@dataclass
class HallucinationAlert:
    """An alert raised when swarm may be hallucinating."""

    alert_type: str
    coherence: float
    perturbation_delta: float
    description: str
    timestamp: float = field(default_factory=time.time)


class AdversarialGrounding:
    """Injects adversarial perturbations to detect hallucination.

    A healthy manifold responds to perturbations — coherence should
    shift. If it doesn't, the swarm may have locked into a shared
    hallucination (coherence bubble).
    """

    def __init__(
        self,
        magnitude: float = PERTURBATION_MAGNITUDE,
        suspicion_threshold: float = STABILITY_SUSPICION_THRESHOLD,
    ) -> None:
        self._magnitude = magnitude
        self._suspicion_threshold = suspicion_threshold
        self._alerts: list[HallucinationAlert] = []
        self._history: list[PerturbationResult] = []

    @property
    def alerts(self) -> list[HallucinationAlert]:
        return list(self._alerts)

    @property
    def history(self) -> list[PerturbationResult]:
        return list(self._history)

    def inject_perturbation(
        self,
        coherence_before: float,
        coherence_after: float,
    ) -> PerturbationResult:
        """Check if the manifold responded to a perturbation."""
        delta = abs(coherence_after - coherence_before)
        suspicious = delta < self._suspicion_threshold

        result = PerturbationResult(
            coherence_before=coherence_before,
            coherence_after=coherence_after,
            perturbation_magnitude=self._magnitude,
            suspicious=suspicious,
        )
        self._history.append(result)

        if suspicious:
            alert = HallucinationAlert(
                alert_type="coherence_bubble",
                coherence=coherence_after,
                perturbation_delta=delta,
                description=(
                    f"Manifold resisted perturbation (delta={delta:.4f} < "
                    f"{self._suspicion_threshold}). Possible hallucination."
                ),
            )
            self._alerts.append(alert)
            logger.warning("Hallucination alert: %s", alert.description)

        return result

    def generate_perturbation_vector(self, rng: np.random.Generator | None = None) -> np.ndarray:
        """Generate a random 12D perturbation vector."""
        if rng is None:
            rng = np.random.default_rng()
        vec = rng.standard_normal(12)
        vec = vec / np.linalg.norm(vec) * self._magnitude
        return vec

    def should_resync(self, consecutive_alerts: int = 3) -> bool:
        """Check if swarm should be forced into resynchronization."""
        if len(self._alerts) < consecutive_alerts:
            return False
        # Check if last N alerts are recent (within 60 seconds of each other)
        recent = self._alerts[-consecutive_alerts:]
        time_span = recent[-1].timestamp - recent[0].timestamp
        return time_span < 60.0
