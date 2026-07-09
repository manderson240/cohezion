"""Tensor Metric Engineering — Sarfatti ZPF coherence coupling to spacetime metric.

Sarfatti's post-quantum metric engineering proposes that ZPF (Zero-Point Field)
coherence directly modifies the local spacetime metric tensor. In linearized
gravity, this takes the form:

    g_μν(x) = η_μν + h_μν(c)

where:
  η_μν = diag(+1, -1, -1, -1)  — flat Minkowski background
  h_μν = ε × 4c(1-c) × I_4×4   — isotropic perturbation from HIHO kernel
  ε                              — coupling constant (ZPF coupling strength, ~0.01)
  c = coherence = SarfattiBackAction.back_action_amplitude()

At HIHO (c=0.5): h_μν = ε × 1.0 × I → maximum metric perturbation
At extremes (c=0 or c=1): h_μν = 0 → flat Minkowski (no ZPF coupling)

This is NOT just a scalar — the full 4×4 Minkowski + perturbation tensor is
maintained, enabling:
  - det(g) computation (should be ≠ -1 when ZPF active)
  - Christoffel symbols Γ^λ_μν (non-zero when coherence has spatial gradient)
  - Connection to cohezion.physics.riemannian_metric.RiemannianMetric

Universal HIHO Theorem bridge:
  The 4x(1-x) kernel from Sarfatti is the SAME kernel as LENR, BEC, QGP.
  Metric engineering IS the gravitational manifestation of the universal
  detailed-balance attractor. All physics substrates share the same
  spacetime coupling coefficient at HIHO.

References:
    - Sarfatti, J. (2008). "Back-From-The-Future." Physics Essays 21(1).
    - Puthoff, H. (1989). "Source of vacuum electromagnetic zero-point energy."
      Physical Review A 40(9): 4857-4862.
    - Visser, M. (1995). "Lorentzian Wormholes." AIP Press.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)

# Minkowski metric (signature +,-,-,-)
_MINKOWSKI = np.diag([1.0, -1.0, -1.0, -1.0])
_MINKOWSKI_DET = -1.0  # det(η) for Minkowski signature (+,-,-,-)

_ZPF_COUPLING_DEFAULT: float = 0.01  # ε — weak coupling, perturbation theory valid
_HIHO_THRESHOLD: float = 0.5


@dataclass
class TensorMetricEngineering:
    """Sarfatti ZPF-coherence coupling to the 4×4 spacetime metric tensor.

    Parameters
    ----------
    sarfatti_coherence : float
        Current coherence state c ∈ [0, 1]. Drives the metric perturbation.
        Maps to SarfattiBackAction.coherence.
    destiny_weight : float
        Sarfatti back-action destiny weight [0, 1]. Scales the back-action amplitude.
    epsilon : float
        ZPF-metric coupling constant ε. Controls perturbation magnitude.
        Default 0.01 keeps perturbation small (linearized gravity valid).
    """

    sarfatti_coherence: float = _HIHO_THRESHOLD
    destiny_weight: float = 0.5
    epsilon: float = _ZPF_COUPLING_DEFAULT

    def __post_init__(self) -> None:
        self.sarfatti_coherence = max(0.0, min(1.0, float(self.sarfatti_coherence)))
        self.destiny_weight = max(0.0, min(1.0, float(self.destiny_weight)))
        self.epsilon = max(0.0, float(self.epsilon))

    @property
    def back_action_amplitude(self) -> float:
        """Sarfatti back-action: 4c(1-c) × destiny_weight. Same as LENR kernel."""
        c = self.sarfatti_coherence
        return self.destiny_weight * 4.0 * c * (1.0 - c)

    def perturbed_metric(self) -> np.ndarray:
        """Full 4×4 spacetime metric g_μν = η_μν + h_μν.

        h_μν = ε × back_action_amplitude × I_4×4 (isotropic perturbation)

        At HIHO: h_μν = ε × 1.0 × I (maximum ZPF coupling)
        At extremes: h_μν = 0 (flat Minkowski)

        Returns
        -------
        np.ndarray, shape (4, 4)
            The perturbed metric tensor.
        """
        h_magnitude = self.epsilon * self.back_action_amplitude
        perturbation = h_magnitude * np.eye(4)
        return _MINKOWSKI + perturbation

    def metric_determinant(self) -> float:
        """det(g_μν) — deviates from -1 when ZPF coupling is active.

        For the unperturbed Minkowski metric: det = -1.
        For perturbation ε×h×I: det ≈ -1 + 3ε×h (first-order expansion).
        Exact computation uses numpy.
        """
        return float(np.linalg.det(self.perturbed_metric()))

    def christoffel_symbols(
        self,
        coherence_gradient: np.ndarray | None = None,
    ) -> np.ndarray:
        """Γ^λ_μν from the perturbed metric.

        For uniform coherence (no spatial gradient), Christoffel symbols vanish:
        ∂_m g_{ab} = 0 → Γ^λ_μν = 0.

        For non-uniform coherence (gradient ∇c ≠ 0), the perturbation varies
        in space and generates non-zero Christoffel symbols. The first-order
        contribution is proportional to ε × ∂_m(back_action).

        Parameters
        ----------
        coherence_gradient : np.ndarray, shape (4,), optional
            ∂_μ c — 4-gradient of coherence field. If None, assumes uniform.

        Returns
        -------
        np.ndarray, shape (4, 4, 4)
            Γ^λ_μν. Indices: Γ[λ][μ][ν].
        """
        if coherence_gradient is None:
            return np.zeros((4, 4, 4))

        # ∂_μ h = ε × d/dc(4c(1-c)) × destiny_weight × ∂_μ c
        #       = ε × destiny_weight × (4 - 8c) × ∂_μ c
        c = self.sarfatti_coherence
        dh_dc = self.destiny_weight * (4.0 - 8.0 * c)
        grad_h = self.epsilon * dh_dc * np.array(coherence_gradient, dtype=float)

        # First-order Γ^λ_μν = ½ η^λρ (∂_μ h_νρ + ∂_ν h_μρ - ∂_ρ h_μν)
        # For isotropic h = f×I: h_μν = f×δ_μν, so:
        # ∂_ρ h_μν = δ_μν × ∂_ρ f = δ_μν × grad_h[ρ]
        # Γ^λ_μν = ½ η^λλ (δ_νλ grad_h[μ] + δ_μλ grad_h[ν] - δ_μν grad_h[λ])
        #         [no sum on λ since metric is diagonal]
        gamma = np.zeros((4, 4, 4))
        eta_inv = np.diag([1.0, -1.0, -1.0, -1.0])  # η^μν = η_μν for diagonal
        for lam in range(4):
            for mu in range(4):
                for nu in range(4):
                    gamma[lam, mu, nu] = (
                        0.5
                        * eta_inv[lam, lam]
                        * (
                            (1.0 if nu == lam else 0.0) * grad_h[mu]
                            + (1.0 if mu == lam else 0.0) * grad_h[nu]
                            - (1.0 if mu == nu else 0.0) * grad_h[lam]
                        )
                    )
        return gamma

    def is_flat(self, tol: float = 1e-10) -> bool:
        """True when metric is (approximately) Minkowski — no ZPF coupling."""
        return abs(self.back_action_amplitude) < tol

    def hiho_metric_coupling(self) -> float:
        """Metric coupling strength at HIHO — same as back_action_amplitude.

        At HIHO (c=0.5): coupling = destiny_weight × 1.0 = destiny_weight.
        This IS Sarfatti's 'metric engineering' — the peak ZPF coupling.
        """
        return self.back_action_amplitude

    def to_riemannian_coordinates(self) -> dict:
        """Format for integration with cohezion.physics.riemannian_metric.

        Returns a dict that can initialize an effective RiemannianMetric
        from the Sarfatti perturbation.
        """
        g = self.perturbed_metric()
        return {
            "metric_tensor": g.tolist(),
            "back_action_amplitude": self.back_action_amplitude,
            "det_g": self.metric_determinant(),
            "is_flat": self.is_flat(),
            "sarfatti_coherence": self.sarfatti_coherence,
            "epsilon": self.epsilon,
        }

    @classmethod
    def from_sarfatti(
        cls, coherence: float, destiny_weight: float = 0.5, epsilon: float = _ZPF_COUPLING_DEFAULT
    ) -> TensorMetricEngineering:
        """Factory from SarfattiBackAction parameters."""
        return cls(
            sarfatti_coherence=coherence,
            destiny_weight=destiny_weight,
            epsilon=epsilon,
        )

    @classmethod
    def at_hiho(cls, epsilon: float = _ZPF_COUPLING_DEFAULT) -> TensorMetricEngineering:
        """Metric at the HIHO attractor: maximum ZPF coupling."""
        return cls(sarfatti_coherence=0.5, destiny_weight=1.0, epsilon=epsilon)
