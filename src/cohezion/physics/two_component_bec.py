"""Two-component exciton condensate — interacting boson model.

Implements the two-component Bose-Einstein condensate physics from:

    Qi, R., Li, Q., Nie, J., et al. (2026).
    "Two-component exciton condensates in an electron–hole bilayer."
    Nature. https://doi.org/10.1038/s41586-026-10636-y

The experiment demonstrates three condensate phases in MoSe₂/hBN/WSe₂
bilayers, controlled by an out-of-plane magnetic field:

    Phase IIA  (intravalley, two-component):
        Both flavors |ψ₁|, |ψ₂| > 0, Josephson-locked in-phase.
        Ground state is a coherent superposition of two exciton flavors.

    Phase IIB  (intervalley, two-component):
        Both |ψ₁|, |ψ₂| > 0, different valley polarization.
        Anti-phase Josephson coupling (J > 0) drives the distinction.

    Phase I    (single-component):
        One amplitude → 0. System is fully polarized in one flavor.
        First-order transition from Phase II; discontinuous order parameter.

Free energy (Landau-Ginzburg / interacting boson model):
    F = r₁|ψ₁|² + r₂|ψ₂|² + u₁|ψ₁|⁴ + u₂|ψ₂|⁴
        + 2g|ψ₁|²|ψ₂|² + 2J|ψ₁||ψ₂|cos(φ)

where φ = arg(ψ₁*ψ₂) is the relative phase, minimized over φ:
    φ_opt = 0  if J < 0 (in-phase → Phase IIA)
    φ_opt = π  if J > 0 (anti-phase → Phase IIB)

First-order transitions occur when g > √(u₁ u₂) (strong cross-repulsion).

Cohezion mapping:
    ψ₁  = fast-tier order parameter  (NPU + iGPU amplitude)
    ψ₂  = deep-tier order parameter  (CPU + cloud  amplitude)
    B   = quality_budget  (control parameter, like magnetic field)
    J   = quality-signal coupling between tiers (Josephson exchange)
    g   = resource contention (cross-repulsion between tier loads)

    Phase IIA  → HIHO hybrid mode:     both tiers active, coherent escalation
    Phase IIB  → cross-tier escalation: quality signal drives intervalley mixing
    Phase I    → single-tier dominance: budget collapse or full-cloud saturation

References:
    - Qi et al. (2026). Nature. s41586-026-10636-y.
    - Landau, L. & Lifshitz, E. (1980). Statistical Physics, §143.
    - Pethick, C. & Smith, H. (2002). Bose-Einstein Condensation in Dilute Gases.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.optimize import minimize


logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5
_DEFAULT_TOLERANCE: float = 0.05


class CondensatePhase(str, Enum):
    """Three condensate phases from Qi et al. 2026."""

    IIA = "IIA"  # intravalley two-component (in-phase Josephson)
    IIB = "IIB"  # intervalley two-component (anti-phase Josephson)
    I = "I"  # single-component (polarized)
    NORMAL = "normal"  # above critical density/temperature (no condensate)


@dataclass
class TwoComponentCondensate:
    """Landau-Ginzburg model for two-component exciton BEC.

    Parameters
    ----------
    r1, r2 : float
        Quadratic mass terms. Negative = condensation onset for that component.
        Analogous to tier readiness: negative means tier is available and active.
    u1, u2 : float
        Quartic self-interaction (must be > 0 for stability).
        Analogous to cost of overloading a single tier.
    g : float
        Cross-interaction between components. g > sqrt(u1*u2) → first-order
        phase transition. Analogous to resource contention between tiers.
    J : float
        Josephson coupling (coherent inter-component exchange).
        J < 0 → in-phase IIA (HIHO hybrid), J > 0 → anti-phase IIB (escalation).
    B : float
        Control parameter (magnetic field analog = quality_budget).
        Shifts r1 and r2 oppositely: r1(B) = r1 + b1*B, r2(B) = r2 - b2*B.
    b1, b2 : float
        Coupling of each component to the control field B.
    """

    r1: float = -1.0
    r2: float = -1.0
    u1: float = 1.0
    u2: float = 1.0
    g: float = 0.8
    J: float = -0.2
    B: float = 0.0
    b1: float = 1.0
    b2: float = 1.0

    def __post_init__(self) -> None:
        if self.u1 <= 0 or self.u2 <= 0:
            raise ValueError("Self-interaction u1, u2 must be positive for stability")

    # ── Effective mass terms ────────────────────────────────────────────

    @property
    def r1_eff(self) -> float:
        """r₁(B) = r₁ + b₁ × B — component 1 mass shifted by field."""
        return self.r1 + self.b1 * self.B

    @property
    def r2_eff(self) -> float:
        """r₂(B) = r₂ − b₂ × B — component 2 mass anti-shifted by field."""
        return self.r2 - self.b2 * self.B

    # ── Free energy ─────────────────────────────────────────────────────

    def free_energy(self, rho1: float, rho2: float) -> float:
        """Landau-Ginzburg free energy minimized over relative phase φ.

        F(ρ₁, ρ₂) = r₁ρ₁² + r₂ρ₂² + u₁ρ₁⁴ + u₂ρ₂⁴ + 2gρ₁²ρ₂²
                   + 2J|ρ₁ρ₂| × min(cos φ)

        The phase is minimized at:
            φ_opt = 0  if J < 0  → contribution = +2J ρ₁ρ₂  (negative = energy gain)
            φ_opt = π  if J > 0  → contribution = -2J ρ₁ρ₂  (energy gain for J>0)
        """
        rho1 = max(0.0, rho1)
        rho2 = max(0.0, rho2)
        quadratic = self.r1_eff * rho1**2 + self.r2_eff * rho2**2
        quartic = self.u1 * rho1**4 + self.u2 * rho2**4
        cross = 2.0 * self.g * rho1**2 * rho2**2
        josephson = -2.0 * abs(self.J) * rho1 * rho2  # always energy-lowering
        return quadratic + quartic + cross + josephson

    def minimize_free_energy(self) -> tuple[float, float, float]:
        """Find (ρ₁*, ρ₂*, F*) that minimize the free energy.

        Uses scipy.optimize.minimize with L-BFGS-B and multiple random starts
        to avoid local minima (important near first-order transitions).

        Returns
        -------
        rho1_star, rho2_star, F_star
        """

        def _f(x: np.ndarray) -> float:
            return self.free_energy(x[0], x[1])

        best_f = float("inf")
        best_x = np.array([0.0, 0.0])

        # Grid of starting points to handle first-order transitions
        starts = [
            [0.01, 0.01],
            [1.0, 0.01],
            [0.01, 1.0],
            [0.7, 0.7],
            [0.5, 0.5],
        ]
        for x0 in starts:
            try:
                result = minimize(
                    _f,
                    x0,
                    bounds=[(0.0, None), (0.0, None)],
                    method="L-BFGS-B",
                )
                if result.fun < best_f:
                    best_f = float(result.fun)
                    best_x = result.x
            except Exception:
                continue

        # Also check the trivial (normal) phase
        f_normal = self.free_energy(0.0, 0.0)
        if f_normal < best_f:
            best_f = f_normal
            best_x = np.array([0.0, 0.0])

        return float(best_x[0]), float(best_x[1]), best_f

    # ── Phase identification ─────────────────────────────────────────────

    def phase(self, tolerance: float = _DEFAULT_TOLERANCE) -> CondensatePhase:
        """Identify which of the three phases the system occupies.

        Rules (Qi et al. 2026 Fig. 2):
            NORMAL  : both ρ₁ ≈ 0 and ρ₂ ≈ 0  (uncondensed)
            Phase I : exactly one ρᵢ ≫ 0       (single-component)
            Phase IIA: both ρ₁ ≈ ρ₂ > 0, J < 0 (in-phase intravalley)
            Phase IIB: both ρ₁ ≠ ρ₂ > 0, J > 0 (anti-phase intervalley)
        """
        rho1, rho2, _ = self.minimize_free_energy()

        both_condensed = rho1 > tolerance and rho2 > tolerance
        both_normal = rho1 < tolerance and rho2 < tolerance

        if both_normal:
            return CondensatePhase.NORMAL
        if not both_condensed:
            return CondensatePhase.I
        # Both condensed — distinguish IIA vs IIB by Josephson sign
        if self.J <= 0:
            return CondensatePhase.IIA
        return CondensatePhase.IIB

    def order_parameters(self) -> dict[str, float]:
        """Return the ground-state order parameters and free energy."""
        rho1, rho2, f_star = self.minimize_free_energy()
        return {
            "rho1": rho1,
            "rho2": rho2,
            "F_star": f_star,
            "polarization": (rho1**2 - rho2**2) / max(rho1**2 + rho2**2, 1e-12),
        }

    # ── HIHO metrics ─────────────────────────────────────────────────────

    def hiho_condensate_score(self) -> float:
        """HIHO kernel on the two-component balance.

        balance = ρ₁² / (ρ₁² + ρ₂²) ∈ [0, 1]
        score   = 4 × balance × (1 - balance)  — peaks at equal components.

        score = 1.0 → perfect two-component balance (HIHO hybrid mode)
        score = 0.0 → fully single-component (Phase I or NORMAL)
        """
        rho1, rho2, _ = self.minimize_free_energy()
        n1 = rho1**2
        n2 = rho2**2
        total = n1 + n2
        if total < 1e-12:
            return 0.0
        balance = n1 / total
        return 4.0 * balance * (1.0 - balance)

    def is_hiho_condensate(self) -> bool:
        """True when the system is in the HIHO two-component balanced regime."""
        return self.hiho_condensate_score() >= 1.0 - _DEFAULT_TOLERANCE

    def is_first_order_regime(self) -> bool:
        """True when g > √(u₁ u₂) — cross-repulsion drives first-order transitions."""
        return bool(self.g > np.sqrt(self.u1 * self.u2))

    # ── Phase diagram sweep ──────────────────────────────────────────────

    def sweep_field(
        self,
        B_range: tuple[float, float] = (-3.0, 3.0),
        n_points: int = 50,
    ) -> list[dict]:
        """Sweep the control field B and record phase at each point.

        Returns a list of {B, phase, rho1, rho2, F_star, hiho_score} dicts,
        useful for plotting phase diagrams or calibrating routing thresholds.
        """
        B_values = np.linspace(B_range[0], B_range[1], n_points)
        records = []
        for B_val in B_values:
            clone = TwoComponentCondensate(
                r1=self.r1,
                r2=self.r2,
                u1=self.u1,
                u2=self.u2,
                g=self.g,
                J=self.J,
                B=float(B_val),
                b1=self.b1,
                b2=self.b2,
            )
            rho1, rho2, f_star = clone.minimize_free_energy()
            records.append(
                {
                    "B": float(B_val),
                    "phase": clone.phase().value,
                    "rho1": rho1,
                    "rho2": rho2,
                    "F_star": f_star,
                    "hiho_score": clone.hiho_condensate_score(),
                }
            )
        return records

    def to_dict(self) -> dict:
        """Serializable summary for SurrealDB traces."""
        rho1, rho2, f_star = self.minimize_free_energy()
        return {
            "phase": self.phase().value,
            "rho1": rho1,
            "rho2": rho2,
            "F_star": f_star,
            "hiho_condensate_score": self.hiho_condensate_score(),
            "is_first_order_regime": self.is_first_order_regime(),
            "B": self.B,
            "J": self.J,
            "g": self.g,
        }


# ── Cohezion routing constructors ───────────────────────────────────────────


def make_triune_bec(quality_budget: float = 0.0) -> TwoComponentCondensate:
    """Two-component BEC for Triune tier routing.

    ψ₁ = fast-tier amplitude (NPU + iGPU).
    ψ₂ = deep-tier amplitude (CPU + cloud).

    At quality_budget=0 (cost-free): HIHO Phase IIA — both tiers balanced.
    At quality_budget>0 (cost pressure): field shifts mass terms, driving
        the system toward Phase I (fast-only) or Phase IIB (escalation).
    At quality_budget<0 (quality pressure): drives toward deep-tier Phase I.

    Parameters
    ----------
    quality_budget : float
        Signed quality budget. Positive = prefer speed (fast-tier favored).
        Negative = prefer accuracy (deep-tier favored). Maps to B field.
    """
    return TwoComponentCondensate(
        r1=-1.0,  # fast tier available (condensed)
        r2=-1.0,  # deep tier available (condensed)
        u1=1.0,  # fast-tier saturation cost
        u2=1.0,  # deep-tier saturation cost
        g=0.9,  # resource contention (near first-order: g > sqrt(u1*u2)=1.0? No, 0.9 < 1)
        J=-0.3,  # negative J → in-phase IIA (HIHO hybrid) at B=0
        B=quality_budget,
        b1=1.0,
        b2=1.0,
    )


def make_flume_bec(kl_weight: float = 0.01) -> TwoComponentCondensate:
    """Two-component BEC for FLUME VAE encoder/decoder order parameters.

    ψ₁ = encoder posterior amplitude (latent distribution).
    ψ₂ = decoder likelihood amplitude (reconstruction).

    The KL weight β (A3 invariant ≤ 0.01) acts as the Josephson coupling:
    small β → weak coupling → both components active (Phase IIA, healthy VAE).
    Large β → strong posterior collapse → Phase I (encoder dominates, KL collapse).

    Parameters
    ----------
    kl_weight : float
        β-VAE KL weight. Must be ≤ 0.01 per A3 harness invariant.
    """
    return TwoComponentCondensate(
        r1=-1.0,  # posterior active
        r2=-1.0,  # likelihood active
        u1=1.0,
        u2=0.5,  # decoder less self-interacting (more expressive)
        g=0.3,  # moderate cross-interaction (encoder/decoder share capacity)
        J=-kl_weight * 10.0,  # scaled KL → Josephson coupling (negative = IIA)
        B=0.0,
        b1=0.0,
        b2=0.0,
    )


def suggest_routing_from_bec(quality_budget: float = 0.0) -> str:
    """Map two-component BEC phase to a Triune routing tier suggestion.

    Returns "npu", "igpu", "cpu", or "cloud" as a routing hint.
    """
    bec = make_triune_bec(quality_budget)
    phase = bec.phase()
    rho1, rho2, _ = bec.minimize_free_energy()

    if phase == CondensatePhase.NORMAL:
        return "igpu"  # safe default when uncondensed
    if phase == CondensatePhase.I:
        # Single-component: which one dominates?
        return "npu" if rho1 >= rho2 else "cpu"
    if phase == CondensatePhase.IIA:
        return "igpu"  # balanced HIHO hybrid — use middle tier
    # Phase IIB: cross-tier escalation
    return "cpu"
