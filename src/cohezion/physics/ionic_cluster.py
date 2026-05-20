"""Itonic / Ionic cluster plasma resonance module.

Models self-organizing ion cluster modes in weakly ionized plasma. The HIHO
phase transition (Gamma_c = 172 coupling parameter) maps directly to Cohezion's
HIHO dynamic equilibrium — the same 50% threshold governs plasma crystallization,
bioelectric gap junction percolation, and LENR lattice coherence.

References:
    Briggs (1971). Plasma Physics 13(5). Magnetized plasma column oscillations.
    Sato et al. (1988). Phys. Rev. Lett. 61(7). Unmagnetized plasma modes.
    Ichimaru (1982). Rev. Mod. Phys. 54(4). Strongly coupled plasma physics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5  # shared with LENRHamiltonian and BioelectricNetwork


@dataclass
class IonicClusterState:
    """Plasma crystal / itonic cluster resonance state.

    Tracks ionization fraction as it evolves toward or away from the HIHO
    equilibrium point. The beta-binomial ionisation_rate() kernel mirrors
    LENR reaction_rate() — both are peaked at 0.5 by the same invariant.
    """

    plasma_density: float = 0.0  # ionised fraction [0, 1]
    cluster_size: int = 100  # number of ions in cluster
    hiho_tolerance: float = 0.05  # equilibrium band width ±

    _history: list[float] = field(default_factory=list, repr=False, compare=False)

    def hiho_equilibrium(self) -> bool:
        """True when |plasma_density - 0.5| ≤ hiho_tolerance."""
        return abs(self.plasma_density - _HIHO_THRESHOLD) <= self.hiho_tolerance

    def ionisation_rate(self) -> float:
        """Beta-binomial ionisation rate, peaks at plasma_density = 0.5.

        rate = 4 * density * (1 - density)   ∈ [0, 1]
        Mirrors LENRHamiltonian.reaction_rate() with the same kernel.
        """
        d = self.plasma_density
        return 4.0 * d * (1.0 - d)

    def step(self, delta: float) -> None:
        """Advance plasma density by delta, clamped to [0, 1]."""
        self._history.append(self.plasma_density)
        self.plasma_density = max(0.0, min(1.0, self.plasma_density + delta))
        logger.debug(
            "IonicCluster step: density=%.3f rate=%.4f equilibrium=%s",
            self.plasma_density,
            self.ionisation_rate(),
            self.hiho_equilibrium(),
        )

    @property
    def active_ions(self) -> int:
        """Number of active (ionized) ions in the cluster."""
        return round(self.cluster_size * self.plasma_density)

    @property
    def steps_taken(self) -> int:
        return len(self._history)


__all__ = ["IonicClusterState"]
