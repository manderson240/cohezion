"""Ionic Cluster — plasma HIHO equilibrium model.

An ionic cluster is a stable, self-organised plasma configuration in which
charged species (ions + electrons) form a bound collective state with
well-defined resonance modes. The cluster is stable when the ionisation
rate approximately equals the recombination rate — analogous to HIHO
(half in, half out): half the species are ionised, half are neutral.

Cohezion mapping:
    plasma_density → fraction of "active" (ionised) species [0, 1]
    hiho_equilibrium() → True when density ≈ 0.5 (±tolerance)
    percolation logic mirrors BioelectricNetwork: below threshold, species
    act independently; above threshold, collective plasma state emerges.

The percolation threshold is shared with BioelectricNetwork (G_c = 0.5)
and LENRHamiltonian (reaction_threshold = 0.5). All three use the same
beta-binomial HIHO kernel, ensuring consistent phase-transition semantics
across bioelectric, nuclear, and plasma sub-models.

References:
    - Langmuir, I. (1928). "Oscillations in Ionized Gases" PNAS 14(8)
      [Langmuir defined 'plasma'; ionic clusters are a structured plasma phase]
    - Hooper, J.H. et al. (1990). "Clusters of Ions" Science 249(4973)
    - Becker, K. et al. (2004). "Non-equilibrium Plasmas" J. Phys. D: Appl. Phys.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

# Shared HIHO threshold — same constant as LENR and BioelectricNetwork.
_HIHO_THRESHOLD: float = 0.5

# Tolerance band around 0.5 for equilibrium detection.
_DEFAULT_TOLERANCE: float = 0.05


@dataclass
class IonicClusterState:
    """State of a self-organised ionic cluster at plasma HIHO equilibrium.

    Parameters
    ----------
    plasma_density : float
        Fraction of species in ionised (active) state [0, 1].
        0.0 = fully neutral gas; 1.0 = fully ionised plasma.
    cluster_size : int
        Number of ions/neutral species in the cluster (default 100).
    hiho_tolerance : float
        Fractional width of the equilibrium band around 0.5 (default 0.05).
        Equilibrium is declared when |density - 0.5| ≤ tolerance.
    """

    plasma_density: float = _HIHO_THRESHOLD
    cluster_size: int = 100
    hiho_tolerance: float = _DEFAULT_TOLERANCE
    _history: list[float] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.plasma_density = max(0.0, min(1.0, float(self.plasma_density)))

    def hiho_equilibrium(self) -> bool:
        """Return True when the plasma is at HIHO equilibrium.

        Equilibrium condition:
            |plasma_density - 0.5| ≤ hiho_tolerance

        At equilibrium the cluster is neither collapsing to neutral gas (density→0)
        nor fully ionising to hot plasma (density→1). The 50% point is the
        stable phase for sustained self-organisation.

        Returns
        -------
        bool
        """
        return abs(self.plasma_density - _HIHO_THRESHOLD) <= self.hiho_tolerance + 1e-9

    def ionisation_rate(self) -> float:
        """Collective ionisation rate — beta-binomial kernel.

        Matches LENR and BioelectricNetwork percolation math:
            rate = 4 · density · (1 - density)

        Peaks at density = 0.5 (HIHO), vanishes at 0 (no ions to transfer)
        and 1 (no neutrals to ionise).
        """
        d = self.plasma_density
        return 4.0 * d * (1.0 - d)

    def step(self, delta: float) -> None:
        """Advance plasma density by delta, clamped to [0, 1].

        Parameters
        ----------
        delta : float
            Change in ionised fraction. Positive = more ionisation.
        """
        self._history.append(self.plasma_density)
        self.plasma_density = max(0.0, min(1.0, self.plasma_density + float(delta)))
        logger.debug(
            "IonicCluster step: density %.3f → %.3f (equilibrium=%s)",
            self._history[-1],
            self.plasma_density,
            self.hiho_equilibrium(),
        )

    @property
    def active_ions(self) -> int:
        """Number of ionised species = round(cluster_size × plasma_density)."""
        return round(self.cluster_size * self.plasma_density)

    @property
    def steps_taken(self) -> int:
        return len(self._history)
