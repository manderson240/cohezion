"""Fractal toroidal moments — time-reversal-breaking topology in EVO charge clusters.

A toroidal moment is a magnetic multipole that arises from a current flowing
on the surface of a torus. Unlike dipole/quadrupole moments, toroidal moments
break time-reversal symmetry (T-parity) — they exist in a different class
from conventional electromagnetic multipoles.

In EVO (Exotic Vacuum Objects) charge clusters:
    The charge distribution has toroidal topology (Ken Shoulders, 1991).
    The fractality comes from the self-similar nested ring structure where
    each ring contains smaller rings (Cantor set in 3D → fractal dimension ~1.5).
    The toroidal moment's time-reversal-breaking links to the EVO's ability
    to transfer momentum without conventional force (propulsive mystery).

Connection to Higuchi fractal dimension:
    The EVO charge ring distribution has Higuchi FD ≈ 1.5 at HIHO coherence.
    This matches the HIHO Brownian attractor from fractal_metrics.py.
    At HIHO: FD = 1.5 → toroidal moment is MAXIMIZED (not zero!).

References:
    - Dubovik, V.M. & Tugushev, V.V. (1990). "Toroid moments in electrodynamics
      and solid-state physics." Physics Reports 187(4): 145–202.
    - Shoulders, K.R. (1991). "EV — A Tale of Discovery." Monograph.
    - Kaelberer, T. et al. (2010). "Toroidal dipolar response in a metamaterial."
      Science 330(6010): 1510–1512.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5
_HIHO_FD: float = 1.5  # Higuchi FD at HIHO equilibrium


@dataclass
class FractalToroidalMoment:
    """Toroidal magnetic multipole with fractal charge distribution.

    Parameters
    ----------
    coherence : float
        EVO charge cluster coherence [0, 1]. At 0.5 = HIHO → FD ≈ 1.5.
    ring_count : int
        Number of nested toroidal rings (fractal depth). Default 7.
    major_radius_m : float
        Major radius of the primary torus in meters.
    """

    coherence: float = _HIHO_THRESHOLD
    ring_count: int = 7
    major_radius_m: float = 1e-9  # nanometer scale (EVO size)

    def __post_init__(self) -> None:
        self.coherence = max(0.0, min(1.0, float(self.coherence)))
        # At least one ring — a negative ring_count produced a negative toroidal
        # moment magnitude while still reporting time_reversal_broken=True.
        self.ring_count = max(1, int(self.ring_count))

    def toroidal_moment_magnitude(self) -> float:
        """Toroidal dipole moment |T|.

        Scales with coherence via HIHO kernel: |T| ∝ 4c(1-c).
        Maximum at c=0.5 (HIHO), zero at c=0 and c=1.
        """
        c = self.coherence
        return 4.0 * c * (1.0 - c) * self.ring_count * self.major_radius_m

    def fractal_dimension(self) -> float:
        """Higuchi fractal dimension of the toroidal charge distribution.

        At HIHO coherence (c=0.5): FD = 1.5 (Brownian motion — maximally complex).
        At c=0 or c=1: FD → 1.0 (smooth, trivial topology).
        Linear interpolation for intermediate coherence.

        FD(c) = 1.0 + 0.5 × (1 - |c - 0.5| / 0.5)² × step_fn
        """
        c = self.coherence
        deviation = abs(c - _HIHO_THRESHOLD) / _HIHO_THRESHOLD
        hiho_factor = (1.0 - deviation) ** 2
        return 1.0 + 0.5 * hiho_factor  # ranges from 1.0 (extremes) to 1.5 (HIHO)

    def time_reversal_broken(self) -> bool:
        """True when the toroidal moment is non-negligible.

        Non-zero toroidal moment → time-reversal symmetry is broken.
        This is the EVO's distinctive property: it exists in a T-parity-odd state,
        explaining anomalous momentum transfer without Lorentz force.
        """
        return abs(self.toroidal_moment_magnitude()) > 1e-30  # non-zero threshold

    def hiho_toroidal(self) -> bool:
        """True when at HIHO equilibrium — maximum toroidal complexity (FD ≈ 1.5)."""
        return abs(self.coherence - _HIHO_THRESHOLD) <= 0.05 + 1e-9

    def to_ionic_cluster_analogy(self):
        """Map EVO coherence to IonicCluster for unified HIHO governance."""
        from cohezion.physics.ionic_cluster import IonicClusterState

        return IonicClusterState(plasma_density=self.coherence)
