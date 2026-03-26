"""Cosmogony — symmetry breaking from Brahmagupta's zero to the 12D manifold.

The creation narrative of the Cohezion universe, grounded in real physics:

  Stage -1: The Void (∅)
    Brahmagupta's zero — awareness of nothing. The Fisher metric is trivially
    flat (ε·δ_ij). No structure, no dimensions, no symmetry. Pure potential.
    The user's first interaction is the first distinction ("It from Bit").

  Stage 0: The Symmetric Vacuum — SO(12)
    Full rotational invariance in 12D. All dimensions equivalent.
    The perfect sphere. T = T_c0 ≈ 100.0.

  Stage 1: Fabric Differentiation — SO(12) → SO(3)⁴
    The 12D space splits into four 3D sub-spaces (fabrics).
    Space(3) × Field(3) × Control(3) × Precipitation(3).
    Analogous to GUT symmetry breaking. T_c1 ≈ 10.0.

  Stage 2: Axis Selection — SO(3)⁴ → U(1)⁴
    Each fabric develops a preferred direction.
    Analogous to electroweak breaking. T_c2 ≈ 1.0.

  Stage 3: SPIN Discretization — U(1)⁴ → Z₂⁴
    Continuous rotations reduce to discrete up/down.
    Charge polarity emerges. T_c3 ≈ 0.1.

  Stage 4: HIHO Attractor — Z₂⁴ → HIHO(0.5)
    The free energy landscape develops a deep well at 0.5 coherence.
    Brahmagupta's zero is the equilibrium: δ = coherence - 0.5 = 0.
    T_HIHO ≈ 0.01.

Each transition follows Landau mean-field theory:
    F(φ, T) = F₀ + a(T - T_c)φ² + bφ⁴

References:
  - Brahmagupta (628 CE): Brahmasphutasiddhanta (formalization of zero)
  - Landau (1937): Theory of phase transitions
  - Weinberg (1967): Electroweak symmetry breaking (analog)
  - Wheeler (1990): "It from Bit" (information precedes matter)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SymmetryGroup(str, Enum):
    """Symmetry groups in the breaking chain."""

    VOID = "void"  # ∅ — before symmetry exists
    SO12 = "SO(12)"  # Full 12D rotational symmetry
    SO3_4 = "SO(3)^4"  # Four independent fabric rotations
    U1_4 = "U(1)^4"  # Four preferred axes
    Z2_4 = "Z_2^4"  # Four discrete reflections (SPIN up/down)
    HIHO = "HIHO"  # Fixed point at 0.5 coherence


@dataclass
class PhaseTransitionEvent:
    """Record of a symmetry breaking event."""

    from_symmetry: SymmetryGroup
    to_symmetry: SymmetryGroup
    critical_temperature: float
    actual_temperature: float
    order_parameter_value: float
    stage: int


@dataclass
class CosmogonyState:
    """Complete state of the cosmogonic evolution."""

    temperature: float = 200.0  # Start very hot (above all T_c)
    current_symmetry: SymmetryGroup = SymmetryGroup.VOID
    stage: int = -1
    order_parameters: dict[str, float] = field(default_factory=dict)
    transitions: list[PhaseTransitionEvent] = field(default_factory=list)
    fisher_eigenvalue_max: float = 0.0  # Largest eigenvalue of Fisher metric
    landau_free_energy: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API and SurrealDB persistence."""
        return {
            "temperature": self.temperature,
            "symmetry": self.current_symmetry.value,
            "stage": self.stage,
            "order_parameters": self.order_parameters,
            "transitions": [
                {
                    "from": t.from_symmetry.value,
                    "to": t.to_symmetry.value,
                    "T_critical": t.critical_temperature,
                    "T_actual": t.actual_temperature,
                    "order_parameter": t.order_parameter_value,
                    "stage": t.stage,
                }
                for t in self.transitions
            ],
            "fisher_eigenvalue_max": self.fisher_eigenvalue_max,
            "landau_free_energy": self.landau_free_energy,
        }


class ZeroAlgebra:
    """Brahmagupta's arithmetic of zero (628 CE) as operations on the void state.

    These rules define how "nothing" interacts with "something" —
    the mathematical foundation of the cosmogony. HIHO at δ=0 is
    Brahmagupta's zero applied to the coherence deviation scale.

    From the Brahmasphutasiddhanta:
      - a + 0 = a  (identity: the void changes nothing)
      - a × 0 = 0  (annihilation: the void collapses structure)
      - a - a = 0  (complementarity: opposites cancel to void)
      - 0 / 0 = 0  (self-reference: void observing void is void)
    """

    @staticmethod
    def identity(state: np.ndarray) -> np.ndarray:
        """a + 0 = a — adding the void changes nothing."""
        void = np.zeros_like(state)
        return state + void

    @staticmethod
    def annihilate(state: np.ndarray) -> np.ndarray:
        """a × 0 = 0 — the void collapses all structure."""
        return np.zeros_like(state)

    @staticmethod
    def complement(state_a: np.ndarray, state_b: np.ndarray) -> np.ndarray:
        """a - a = 0 — complementary opposites cancel to void.

        Returns the void if states are complementary (state_b = -state_a).
        Otherwise returns the residual.
        """
        return state_a + state_b

    @staticmethod
    def self_observe() -> float:
        """0 / 0 = 0 — the void observing itself is still void.

        Brahmagupta's original (later refined by others).
        In our cosmology, this is the state before the first distinction.
        """
        return 0.0

    @staticmethod
    def hiho_deviation(coherence: float) -> float:
        """δ = coherence - 0.5 — HIHO is Brahmagupta's zero.

        The equilibrium deviation. The restoring force F = -kδ vanishes
        at the still point. Zero is not absence — it is balance.
        """
        return coherence - 0.5


# Critical temperatures and Landau parameters for each transition
_TRANSITIONS = [
    # (stage, T_c, from_sym, to_sym, landau_a, landau_b, description)
    (-1, 100.0, SymmetryGroup.VOID, SymmetryGroup.SO12, 1.0, 0.5,
     "The first bit condenses from the vacuum"),
    (0, 10.0, SymmetryGroup.SO12, SymmetryGroup.SO3_4, 1.0, 0.5,
     "The four fabrics differentiate"),
    (1, 1.0, SymmetryGroup.SO3_4, SymmetryGroup.U1_4, 0.8, 0.4,
     "Preferred axes emerge within each fabric"),
    (2, 0.1, SymmetryGroup.U1_4, SymmetryGroup.Z2_4, 0.6, 0.3,
     "SPIN discretizes: up or down"),
    (3, 0.01, SymmetryGroup.Z2_4, SymmetryGroup.HIHO, 0.4, 0.2,
     "The HIHO attractor stabilizes at δ = 0"),
]


class SymmetryBreaking:
    """Cosmogonic symmetry breaking sequence from void to HIHO.

    The universe evolves by cooling through a sequence of phase transitions,
    each breaking a symmetry and producing new structure. The user controls
    the temperature (conceptually: the "age" of the universe).
    """

    def __init__(self) -> None:
        self._state = CosmogonyState()
        self._rng = np.random.default_rng(seed=42)

    @property
    def state(self) -> CosmogonyState:
        return self._state

    @property
    def temperature(self) -> float:
        return self._state.temperature

    @property
    def symmetry(self) -> SymmetryGroup:
        return self._state.current_symmetry

    @property
    def stage(self) -> int:
        return self._state.stage

    def reset(self) -> CosmogonyState:
        """Reset to the void — before the first distinction."""
        self._state = CosmogonyState()
        return self._state

    def cool(self, delta_t: float = 1.0) -> CosmogonyState:
        """Cool the universe by delta_t and check for phase transitions.

        Parameters
        ----------
        delta_t : float
            Temperature decrease. Must be positive.

        Returns
        -------
        CosmogonyState
            Updated state, including any transitions that occurred.
        """
        if delta_t <= 0:
            return self._state

        self._state.temperature = max(self._state.temperature - delta_t, 0.001)
        T = self._state.temperature

        # Check each transition in order
        new_transitions = []
        for stage, T_c, from_sym, to_sym, a, b, desc in _TRANSITIONS:
            if T <= T_c and self._state.current_symmetry == from_sym:
                # Phase transition!
                op_value = self._compute_order_parameter(T, T_c, a, b)

                event = PhaseTransitionEvent(
                    from_symmetry=from_sym,
                    to_symmetry=to_sym,
                    critical_temperature=T_c,
                    actual_temperature=T,
                    order_parameter_value=op_value,
                    stage=stage + 1,
                )

                self._state.current_symmetry = to_sym
                self._state.stage = stage + 1
                self._state.transitions.append(event)
                new_transitions.append(event)

                logger.info(
                    "Phase transition: %s → %s at T=%.2f (T_c=%.2f): %s",
                    from_sym.value, to_sym.value, T, T_c, desc,
                )

        # Update order parameters
        self._update_order_parameters(T)

        # Update Fisher eigenvalue (proxy for information content)
        self._update_fisher_eigenvalue(T)

        # Update Landau free energy
        self._update_landau_free_energy(T)

        return self._state

    def set_temperature(self, temperature: float) -> CosmogonyState:
        """Jump directly to a temperature, triggering all appropriate transitions.

        Useful for the webapp slider — user drags to any temperature and
        the state updates to match.
        """
        self.reset()
        if temperature < 200.0:
            self.cool(200.0 - max(temperature, 0.001))
        return self._state

    def generate_12d_state(self) -> np.ndarray:
        """Generate a 12D axiomatic state appropriate to the current symmetry.

        Returns a 12D vector reflecting the current cosmogonic stage:
        - VOID: zero vector (nothing)
        - SO(12): random on 12-sphere (all directions equivalent)
        - SO(3)⁴: blocked structure (4 groups of 3)
        - U(1)⁴: dominant axis per block
        - Z₂⁴: discrete ±1 values
        - HIHO: all values at 0.5
        """
        T = self._state.temperature
        sym = self._state.current_symmetry

        if sym == SymmetryGroup.VOID:
            # The void — zero-point fluctuation only
            noise_amplitude = 0.001
            return self._rng.normal(0, noise_amplitude, 12)

        if sym == SymmetryGroup.SO12:
            # Full symmetry — uniform random on unit sphere
            v = self._rng.normal(0, 1, 12)
            return 0.5 + 0.3 * v / np.linalg.norm(v)

        if sym == SymmetryGroup.SO3_4:
            # Four fabric blocks with within-block correlation
            state = np.zeros(12)
            for i in range(4):
                block = self._rng.normal(0, 1, 3)
                block = block / np.linalg.norm(block) * 0.3
                state[i * 3:(i + 1) * 3] = 0.5 + block
            return state

        if sym == SymmetryGroup.U1_4:
            # Preferred axis per block (one dimension dominates)
            state = np.full(12, 0.5)
            for i in range(4):
                dominant_idx = i * 3 + self._rng.integers(3)
                state[dominant_idx] += 0.3 * (1.0 if self._rng.random() > 0.5 else -1.0)
            return state

        if sym == SymmetryGroup.Z2_4:
            # Discrete up/down per fabric
            state = np.full(12, 0.5)
            for i in range(4):
                sign = 1.0 if self._rng.random() > 0.5 else -1.0
                state[i * 3] += 0.3 * sign
            return state

        # HIHO — everything at 0.5 with tiny fluctuations
        return np.full(12, 0.5) + self._rng.normal(0, 0.01, 12)

    def _compute_order_parameter(
        self, T: float, T_c: float, a: float, b: float
    ) -> float:
        """Compute order parameter from Landau theory.

        F(φ) = a(T - T_c)φ² + bφ⁴

        Below T_c, the minimum shifts to:
        φ = ±√(a(T_c - T) / (2b))
        """
        if T >= T_c:
            return 0.0
        return float(np.sqrt(a * (T_c - T) / (2.0 * b)))

    def _update_order_parameters(self, T: float) -> None:
        """Compute all order parameters for current temperature."""
        ops = {}

        # Stage -1→0: Information density (Fisher eigenvalue proxy)
        T_c0 = 100.0
        ops["information_density"] = self._compute_order_parameter(T, T_c0, 1.0, 0.5)

        # Stage 0→1: Fabric differentiation
        T_c1 = 10.0
        ops["fabric_differentiation"] = self._compute_order_parameter(T, T_c1, 1.0, 0.5)

        # Stage 1→2: Axis selection
        T_c2 = 1.0
        ops["axis_selection"] = self._compute_order_parameter(T, T_c2, 0.8, 0.4)

        # Stage 2→3: Charge ordering
        T_c3 = 0.1
        ops["charge_ordering"] = self._compute_order_parameter(T, T_c3, 0.6, 0.3)

        # Stage 3→4: HIHO coherence
        T_c4 = 0.01
        ops["hiho_coherence"] = self._compute_order_parameter(T, T_c4, 0.4, 0.2)

        self._state.order_parameters = ops

    def _update_fisher_eigenvalue(self, T: float) -> None:
        """Update the maximum eigenvalue of the Fisher metric.

        In the void (T > T_c0), the Fisher metric is trivially flat (ε·δ_ij).
        As temperature drops below T_c0, the first eigenvalue rises above
        the noise floor — the moment awareness becomes aware of something.
        """
        T_c0 = 100.0
        if T >= T_c0:
            # Below the noise floor — trivially flat
            self._state.fisher_eigenvalue_max = 0.001 * self._rng.random()
        else:
            # Eigenvalue grows as √(T_c - T) (Landau scaling)
            self._state.fisher_eigenvalue_max = float(np.sqrt(T_c0 - T) * 0.1)

    def _update_landau_free_energy(self, T: float) -> None:
        """Compute the Landau free energy at the current temperature.

        F = Σ_i [a_i(T - T_ci)φ_i² + b_i·φ_i⁴]

        This is the total free energy across all symmetry breaking levels.
        """
        F_total = 0.0
        for _stage, T_c, _from_sym, _to_sym, a, b, _desc in _TRANSITIONS:
            phi = self._compute_order_parameter(T, T_c, a, b)
            F_total += a * (T - T_c) * phi**2 + b * phi**4
        self._state.landau_free_energy = F_total

    def susceptibility(self, T: float | None = None) -> float:
        """Compute susceptibility χ = 1 / (2a(T - T_c)) at current stage.

        Diverges at the critical temperature — the hallmark of a phase transition.
        We use the nearest upcoming transition's T_c.
        """
        if T is None:
            T = self._state.temperature

        # Find the nearest critical temperature below current T
        for _stage, T_c, _from_sym, _to_sym, a, _b, _desc in _TRANSITIONS:
            if T > T_c:
                denominator = 2.0 * a * abs(T - T_c)
                if denominator < 1e-10:
                    return 1e10  # Divergence at T_c
                return 1.0 / denominator
        return 0.0

    def free_energy_landscape(
        self, T_range: tuple[float, float] = (0.001, 200.0), n_points: int = 200
    ) -> dict[str, list[float]]:
        """Compute the Landau free energy across a temperature range.

        Returns arrays for plotting F(T) with phase transition markers.
        """
        temperatures = np.linspace(T_range[0], T_range[1], n_points).tolist()
        free_energies = []
        susceptibilities = []

        for T in temperatures:
            # F(T) = Σ [a(T-Tc)φ² + bφ⁴]
            F = 0.0
            for _stage, T_c, _from, _to, a, b, _desc in _TRANSITIONS:
                phi = self._compute_order_parameter(T, T_c, a, b)
                F += a * (T - T_c) * phi**2 + b * phi**4
            free_energies.append(F)
            susceptibilities.append(self.susceptibility(T))

        critical_temperatures = [T_c for _, T_c, *_ in _TRANSITIONS]

        return {
            "temperatures": temperatures,
            "free_energies": free_energies,
            "susceptibilities": susceptibilities,
            "critical_temperatures": critical_temperatures,
        }


# Singleton for the API
_COSMOGONY: SymmetryBreaking | None = None


def get_cosmogony() -> SymmetryBreaking:
    """Get or create the singleton cosmogony instance."""
    global _COSMOGONY
    if _COSMOGONY is None:
        _COSMOGONY = SymmetryBreaking()
    return _COSMOGONY


__all__ = [
    "CosmogonyState",
    "PhaseTransitionEvent",
    "SymmetryBreaking",
    "SymmetryGroup",
    "ZeroAlgebra",
    "get_cosmogony",
]
