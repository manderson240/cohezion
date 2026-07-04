"""Thermodynamic derivation of gravity following Isichei & Magueijo 2026 (arXiv:2511.22221).

GR emerges as a degenerate Otto thermodynamic cycle. Adding work-producing legs
(controlled Lorentz violation + energy-momentum non-conservation) generates
late-time cosmic acceleration without a cosmological constant.

Wired into cosmogony.py Step 3→4 (SO(12) Symmetric Vacuum → Fabric Differentiation):
the fabric-differentiation transition is the cosmogonic epoch where the Otto work
legs drive ∂_μT^μν ≠ 0, seeding structural asymmetry from the symmetric vacuum.

Reference: Isichei & Magueijo (2026, PRL) — arXiv:2511.22221, DOI:10.1103/tvmx-qk3k
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class OttoWorkLeg:
    """A work-producing leg in the thermodynamic gravity Otto cycle.

    lorentz_violation: ε parameter measuring departure from LLI (0 = pure GR)
    entropy_flux: δS contribution of this leg
    """

    lorentz_violation: float = 0.0  # ε ∈ [0, 1]
    entropy_flux: float = 0.0  # δS


@dataclass
class ThermodynamicGravity:
    """Otto cycle model of emergent gravity with work-producing legs.

    dS = δQ/T + δW_extra, where δW_extra drives ∂_μT^μν ≠ 0
    At ε=0: degenerate Otto cycle → standard GR.
    At ε>0: non-degenerate cycle → late-time acceleration without Λ.
    """

    temperature: float = 1.0  # T in natural units
    work_legs: list[OttoWorkLeg] = field(default_factory=list)

    def entropy_change(self, heat_flux: float) -> float:
        """dS = δQ/T + Σ δW_extra / T for all work legs."""
        work_entropy = sum(leg.entropy_flux for leg in self.work_legs)
        return heat_flux / self.temperature + work_entropy / self.temperature

    def lorentz_violation_parameter(self) -> float:
        """ε: mean departure from local Lorentz invariance across work legs."""
        if not self.work_legs:
            return 0.0
        return sum(leg.lorentz_violation for leg in self.work_legs) / len(self.work_legs)

    def is_standard_gr(self, tol: float = 1e-9) -> bool:
        """True when ε ≈ 0: degenerate Otto cycle = standard GR."""
        return abs(self.lorentz_violation_parameter()) < tol

    def acceleration_term(self) -> float:
        """Late-time acceleration proxy: Σ ε * δS for each work leg.

        Positive value replaces the cosmological constant Λ.
        """
        return sum(leg.lorentz_violation * leg.entropy_flux for leg in self.work_legs)


def donnan_potential_to_work_leg(
    membrane_charge_density: float,
    ionic_strength: float,
    temperature: float = 1.0,
    valence: float = 1.0,
) -> OttoWorkLeg:
    """Convert Donnan equilibrium potential to an OttoWorkLeg.

    Structural connection (Hernández et al. 2026, Polymers 18, 1596):
      - PEL/EDL interface → E6 focusing sphere (Mereon r=3.078)
      - Donnan saturation ceiling → OttoWorkLeg entropy_flux ceiling
      - High membrane charge → large ε (departure from GR-like equilibrium)

    The Donnan potential sets the maximum electrochemical work extractable
    before the ionic distribution saturates — exactly analogous to the maximum
    δS contribution of a work leg before ε→1 kills the cycle efficiency.

    φ_D = (RT/zF) * arcsinh(ρ_fix / (2c_s))  [linearised Donnan]

    where ρ_fix = membrane_charge_density, c_s = ionic_strength (mol/m³).

    Parameters
    ----------
    membrane_charge_density : float
        Fixed charge density ρ_fix in the PEL (mol/m³, positive = cationic).
    ionic_strength : float
        Background ionic strength c_s (mol/m³).
    temperature : float
        Reduced thermal energy kT/e (dimensionless, default 1).
    valence : float
        Counter-ion valence z (default monovalent).

    Returns
    -------
    OttoWorkLeg
        lorentz_violation = normalised |φ_D| / (π/2)  ∈ [0, 1]
        entropy_flux = |φ_D| * temperature  (work capacity proxy)
    """
    if ionic_strength <= 0:
        raise ValueError("ionic_strength must be positive")
    ratio = abs(membrane_charge_density) / (2.0 * ionic_strength * abs(valence))
    phi_donnan = (temperature / abs(valence)) * math.asinh(ratio)

    # Normalise ε to [0,1]: arcsinh saturates → ε approaches 1 asymptotically
    epsilon = (2.0 / math.pi) * math.atan(abs(phi_donnan))
    delta_s = abs(phi_donnan) * temperature

    return OttoWorkLeg(lorentz_violation=epsilon, entropy_flux=delta_s)
