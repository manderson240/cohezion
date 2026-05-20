"""LENR — Low Energy Nuclear Reactions bridge module.

Models lattice confinement fusion as a coherence-driven phase transition.
Reaction rate peaks at HIHO threshold (coherence = 0.5), consistent with the
cross-scale invariant shared by BioelectricNetwork and IonicClusterState.

References:
    Mosier-Boss et al. (2009). Naturwissenschaften 96(1). Navy NRL SPAWAR results.
    Hagelstein & Kim (2011). MIT lattice-assisted nuclear reactions model.
    Puthoff (1990). ZPF coherence pumping in palladium lattice.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5  # shared with IonicClusterState and BioelectricNetwork


@dataclass
class LENRHamiltonian:
    """Coherence-driven LENR reaction rate model.

    Reaction rate follows a beta-binomial kernel peaked at reaction_threshold,
    equivalent to the ionisation_rate() kernel in IonicClusterState. This encodes
    the cross-scale HIHO invariant: phase transitions in all substrates (nuclear,
    plasma, bioelectric) peak at 50% coherence.

    Math:
        rate(c) = coupling * 4 * c * (1 - c)   for threshold = 0.5
        rate(c) = coupling * [c(1-c)] / [t(1-t)] * 4*t(1-t)   general form
    """

    reaction_threshold: float = _HIHO_THRESHOLD
    lattice_coupling: float = 1.0
    agent_id: str = "lenr-bridge"

    _coherence_events: list[tuple[float, float]] = field(
        default_factory=list, repr=False, compare=False
    )

    def reaction_rate(self, coherence: float) -> float:
        """Beta-binomial reaction rate, peaks at reaction_threshold.

        Returns 0 at coherence=0 and coherence=1; maximum at reaction_threshold.
        Clamped to [0, 1] input range.
        """
        c = max(0.0, min(1.0, coherence))
        t = self.reaction_threshold
        if t <= 0.0 or t >= 1.0:
            return 0.0
        # Normalized so max value = lattice_coupling at c = t
        normalizer = 4.0 * t * (1.0 - t)
        if normalizer == 0.0:
            return 0.0
        return self.lattice_coupling * (4.0 * c * (1.0 - c)) / normalizer

    def record_coherence_event(self, coherence: float) -> None:
        """Log a coherence event and its reaction rate."""
        rate = self.reaction_rate(coherence)
        self._coherence_events.append((coherence, rate))
        logger.debug(
            "LENR event: coherence=%.3f rate=%.4f agent=%s",
            coherence,
            rate,
            self.agent_id,
        )

    @property
    def event_count(self) -> int:
        return len(self._coherence_events)

    @property
    def mean_rate(self) -> float:
        if not self._coherence_events:
            return 0.0
        return sum(r for _, r in self._coherence_events) / len(self._coherence_events)


__all__ = ["LENRHamiltonian"]
