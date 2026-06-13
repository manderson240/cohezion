"""Bose-Einstein Condensate bridge — quantum coherence ground state.

A BEC is the macroscopic quantum coherence limit: all particles occupy
the same ground state, described by a single wavefunction. The BEC fraction
(condensate_fraction = N_0/N_total) maps exactly to the Cohezion HIHO
plasma_density — both measure the fraction of the system in the coherent phase.

The HIHO kernel applies universally:
    BEC transition rate = 4 × f_c × (1 - f_c)
    where f_c = condensate fraction (0 = fully thermal, 1 = fully condensed)
    This peaks at f_c = 0.5, identical to LENR, IonicCluster, and COLIBRE.

Stealthskater context:
    BECs in dilute alkali gases (Rb-87, Na-23) form at T < 100 nK via laser
    cooling. The macroscopic quantum coherence enables gravity-wave sensing,
    optical lattice quantum computing, and possibly ZPF coupling (Putoff model).
    BEC → ZPF boundary is the HIHO equilibrium point.

References:
    - Cornell & Wieman (1995). "Bose-Einstein condensation in a dilute gas."
      Science 269: 198–201. [Nobel 2001]
    - Ketterle, W. (2002). "Nobel lecture: When atoms behave as waves." Rev. Mod. Phys.
    - Puthoff, H.E. (1987). "Ground state of hydrogen as a zero-point-fluctuation-
      determined state." Physical Review D 35(10): 3266.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5
_DEFAULT_TOLERANCE: float = 0.05


@dataclass
class BECState:
    """State of a Bose-Einstein Condensate system.

    Parameters
    ----------
    condensate_fraction : float
        Fraction of atoms in the condensate ground state [0, 1].
        0.0 = fully thermal gas. 1.0 = fully condensed.
        0.5 = HIHO boundary — half thermal, half condensed.
    temperature_nk : float
        Temperature in nanokelvin. At T_c, condensate_fraction → 0.
    atom_count : int
        Total number of atoms in the system.
    hiho_tolerance : float
        Tolerance band for HIHO equilibrium detection (default 0.05).
    """

    condensate_fraction: float = _HIHO_THRESHOLD
    temperature_nk: float = 100.0
    atom_count: int = 100_000
    hiho_tolerance: float = _DEFAULT_TOLERANCE

    def __post_init__(self) -> None:
        self.condensate_fraction = max(0.0, min(1.0, float(self.condensate_fraction)))
        # Atom count is a physical population; clamp negatives so condensed_atoms
        # and thermal_atoms can never go negative.
        self.atom_count = max(0, int(self.atom_count))

    def hiho_equilibrium(self) -> bool:
        """True when the BEC is at quantum HIHO equilibrium (f_c ≈ 0.5 ± tolerance).

        At HIHO: half the atoms are condensed (quantum coherent),
        half are thermal (classical). This boundary maximizes the
        quantum-to-classical transition rate — the universal HIHO attractor.

        Uses the same +1e-9 epsilon guard as IonicClusterState.
        """
        return abs(self.condensate_fraction - _HIHO_THRESHOLD) <= self.hiho_tolerance + 1e-9

    def transition_rate(self) -> float:
        """BEC condensation rate — 4×f_c×(1-f_c) HIHO kernel.

        Identical formula to LENR.reaction_rate(), IonicCluster.ionisation_rate(),
        and COLIBRE.colibre_coherence. Universal HIHO attractor.
        """
        f = self.condensate_fraction
        return 4.0 * f * (1.0 - f)

    def to_ionic_cluster(self):
        """Map BEC condensate fraction to IonicCluster plasma density."""
        from cohezion.physics.ionic_cluster import IonicClusterState

        return IonicClusterState(plasma_density=self.condensate_fraction)

    @property
    def condensed_atoms(self) -> int:
        """Number of atoms in the BEC ground state."""
        return round(self.atom_count * self.condensate_fraction)

    @property
    def thermal_atoms(self) -> int:
        """Number of thermally excited atoms."""
        return self.atom_count - self.condensed_atoms


@dataclass
class MercuryLattice:
    """Mercury superconductor as LENR lattice medium.

    Mercury (Hg) was the first superconductor discovered (Onnes, 1911) at T_c = 4.2K.
    Below T_c, the Hg lattice enters a coherent state analogous to LENR's
    lattice confinement: Cooper pairs (electron pairs) are the coherent carriers,
    and the pairing strength peaks at the HIHO coherence point.

    Stealthskater context:
        Hg-filled cavities in electrogravitic experiments (Searl effect, Tewari)
        are proposed as rotating plasma systems where Hg acts as both
        the superconducting lattice and the LENR-like nuclear catalyst.

    Parameters
    ----------
    coherence : float
        Lattice coherence in [0, 1]. Peaks at HIHO 0.5 (BCS gap equation).
    lattice_coupling : float
        Phonon coupling strength (dimensionless, analogous to BCS g).
    """

    coherence: float = _HIHO_THRESHOLD
    lattice_coupling: float = 1.0

    def __post_init__(self) -> None:
        self.coherence = max(0.0, min(1.0, float(self.coherence)))
        # Phonon coupling is a non-negative strength; a negative value would flip
        # the sign of bcs_gap_rate, producing a negative (unphysical) pairing rate.
        self.lattice_coupling = max(0.0, float(self.lattice_coupling))

    def bcs_gap_rate(self) -> float:
        """Cooper pairing rate — same 4×c×(1-c) HIHO kernel as LENR."""
        c = self.coherence
        return self.lattice_coupling * 4.0 * c * (1.0 - c)

    def is_superconducting(self) -> bool:
        """True when coherence is in the BCS pairing regime (near 0.5)."""
        return abs(self.coherence - _HIHO_THRESHOLD) <= _DEFAULT_TOLERANCE + 1e-9
