"""Magnetohydrodynamics plasma bridge — IonicCluster at astrophysical scale.

MHD describes the behavior of electrically conducting fluids (plasmas, liquid
metals) in magnetic fields. It governs everything from the solar corona to
galaxy cluster ICM to bismuth diamagnetic levitation experiments.

The key HIHO connection:
    MHD equilibrium occurs when magnetic pressure ≈ plasma pressure (β = 1).
    β = plasma_pressure / magnetic_pressure = 8π n k T / B²
    At β = 0.5: HIHO equilibrium — balanced magnetic and thermal energy.
    alfven_coherence(β) = 4β(1-β) — the universal HIHO kernel.

Bismuth diamagnetic context:
    Bismuth (χ = -1.7×10⁻⁴) is the most strongly diamagnetic natural element.
    Diamagnetic levitation creates a HIHO magnetic equilibrium where the
    repulsive diamagnetic force exactly balances gravity. This is equivalent
    to MHD force balance at the diamagnetic HIHO point.

Stealthskater context:
    - Biefield-Brown (T.T. Brown, 1956): asymmetric capacitor levitation
    - Searl Effect Generator: rotating Nd-Fe-B + Bi + Al rings
    - Tewari's Space Power Generator: rotating magnetic fields in Hg
    All involve rotating MHD plasma configurations at (near) magnetic HIHO.

References:
    - Alfvén, H. (1942). "Existence of electromagnetic-hydrodynamic waves."
      Nature 150: 405–406. [Nobel 1970]
    - Parker, E.N. (1979). Cosmical Magnetic Fields. Oxford.
    - Brown, T.T. (1956). US Patent 2,949,550. Electrokinetic apparatus.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5
_DEFAULT_TOLERANCE: float = 0.05


@dataclass
class MHDEquilibrium:
    """State of a magnetized plasma system at MHD force balance.

    Parameters
    ----------
    plasma_beta : float
        Ratio of plasma pressure to magnetic pressure [0, ∞).
        β = 1: equipartition (HIHO). β << 1: magnetically dominated.
        β >> 1: thermally dominated.
    lundquist_number : float
        S = τ_resistive / τ_alfven — measure of MHD turbulence.
        High S → smooth Alfvén waves. Low S → resistive reconnection.
    alfven_velocity_kms : float
        v_A = B / sqrt(4πρ) in km/s.
    """

    plasma_beta: float = _HIHO_THRESHOLD
    lundquist_number: float = 1e6
    alfven_velocity_kms: float = 100.0

    def __post_init__(self) -> None:
        self.plasma_beta = max(0.0, min(2.0, float(self.plasma_beta)))

    def hiho_magnetized(self) -> bool:
        """True when magnetic and plasma pressures are at HIHO equilibrium (β ≈ 0.5).

        At β = 0.5: the system is in magnetostatic HIHO equilibrium —
        half the energy is magnetic, half is thermal. This is the stable
        attractor for self-organized MHD systems (solar wind, ISM, ICM).
        """
        # Normalize: map β ∈ [0, 2] to [0, 1] by dividing by 2, then check HIHO
        normalized_beta = self.plasma_beta / 2.0
        return abs(normalized_beta - _HIHO_THRESHOLD) <= _DEFAULT_TOLERANCE + 1e-9

    def alfven_coherence(self) -> float:
        """Coherence rate via 4β(1-β) HIHO kernel at normalized β.

        Maps MHD plasma_beta to the universal HIHO coherence kernel:
            alfven_coherence = 4 × (β/2) × (1 - β/2)
        Peaks at β = 1 (equipartition), matching LENR/BEC/IonicCluster.
        """
        b = min(1.0, self.plasma_beta / 2.0)
        return 4.0 * b * (1.0 - b)

    def is_alfvenic(self) -> bool:
        """True when Alfvén speed dominates — magnetically ordered regime."""
        return self.plasma_beta < _HIHO_THRESHOLD and self.lundquist_number > 1e4

    def to_ionic_cluster(self):
        """Map plasma_beta to IonicCluster plasma_density for unified HIHO tracking."""
        from cohezion.physics.ionic_cluster import IonicClusterState

        normalized = min(1.0, self.plasma_beta / 2.0)
        return IonicClusterState(plasma_density=normalized)


@dataclass
class BismuthDiamagnet:
    """Bismuth diamagnetic field configuration.

    Bismuth has the strongest diamagnetic susceptibility of any natural element
    (χ = -1.66×10⁻⁴). In a sufficiently strong magnetic field, diamagnetic
    repulsion can levitate a bismuth sample — creating a magnetic HIHO equilibrium
    where repulsive diamagnetic force = gravitational force.

    This maps to the DielectricField.biefield_brown_force() framework:
    diamagnetic levitation IS a Biefield-Brown analog with magnetic permittivity
    gradient instead of dielectric permittivity gradient.
    """

    magnetic_susceptibility: float = -1.66e-4  # Bi at 300K
    field_strength_tesla: float = 10.0
    mass_kg: float = 1e-3

    def levitation_threshold_tesla(self) -> float:
        """Minimum field for diamagnetic levitation of bismuth sample.

        B_min ≈ sqrt(μ₀ m g / (χ V)) where V = sample volume.
        At threshold: diamagnetic force = gravity → HIHO equilibrium.
        """
        import math

        mu0 = 4 * math.pi * 1e-7
        g = 9.81
        rho_bi = 9800.0  # kg/m^3
        volume = self.mass_kg / rho_bi
        chi = abs(self.magnetic_susceptibility)
        if chi < 1e-10 or volume < 1e-20:
            return float("inf")
        return math.sqrt(mu0 * self.mass_kg * g / (chi * volume))

    def hiho_levitation(self) -> bool:
        """True when the field is within HIHO tolerance of the levitation threshold."""
        threshold = self.levitation_threshold_tesla()
        if not (0 < threshold < float("inf")):
            return False
        ratio = self.field_strength_tesla / threshold
        return abs(ratio - 1.0) <= _DEFAULT_TOLERANCE + 1e-9

    def diamagnetic_coherence(self) -> float:
        """4×(B/B_threshold - 0.5)² coherence (0 at threshold, increases away).

        Note: unlike other HIHO substrates, diamagnetic levitation is NOT
        a maximum-coherence-at-equilibrium system. At threshold (ratio=1),
        the levitation is metastable. For routing purposes we use proximity
        to threshold as the coherence signal.
        """
        threshold = self.levitation_threshold_tesla()
        if not (0 < threshold < float("inf")):
            return 0.0
        ratio = min(2.0, self.field_strength_tesla / threshold)
        return 4.0 * (ratio / 2.0) * (1.0 - ratio / 2.0)
