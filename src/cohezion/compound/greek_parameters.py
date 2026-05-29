"""Greek letter control parameters for the Universe Research Engineer compound loop.

Five dimensionless forces governing compound loop dynamics:
  α (alpha)  — learning rate: how fast the URE learns from simulation runs
  Ω (omega)  — Sarfatti destiny attractor: the HIHO fixed point (0.5)
  γ (gamma)  — HIHO coherence kernel: 4x(1-x), peaks at x=0.5
  δ (delta)  — R0 adversarial perturbation: how hard the challenger hits
  β (beta)   — KL regularization weight: FLUME VAE collapse guard (A3 invariant)

Equation of motion:
  x(t+1) = x(t) + α×γ(x(t)) − δ×r0(x(t)) + β×(Ω − x(t))
             learning   HIHO pull   adversarial   destiny pull

At HIHO (x=0.5): γ(0.5)=1.0 (maximum learning), Ω−x=0 (at attractor).
System self-organizes at x=0.5 because all four forces balance there.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.5


@dataclass
class GreekParameters:
    """Five-force control system for the Universe Research Engineer.

    Parameters
    ----------
    alpha : float
        Learning rate — SkillRefiner step size per compound cycle [0.001, 0.1].
    omega : float
        Sarfatti Omega point = HIHO destiny attractor = 0.5.
    delta : float
        Adversarial perturbation magnitude from R0 challenger [0, 0.1].
    beta : float
        KL regularization weight (FLUME VAE A3 invariant) = 0.01.
    """

    alpha: float = 0.05
    omega: float = _HIHO_THRESHOLD
    delta: float = 0.05
    beta: float = 0.01  # A3 invariant: never exceed 0.015

    def __post_init__(self) -> None:
        self.alpha = max(0.0, min(1.0, float(self.alpha)))
        self.omega = max(0.0, min(1.0, float(self.omega)))
        self.delta = max(0.0, min(0.5, float(self.delta)))
        self.beta = max(0.0, min(0.015, float(self.beta)))  # A3 collapse guard

    def gamma(self, x: float) -> float:
        """HIHO coherence kernel γ(x) = 4x(1-x). Universal attractor formula."""
        return 4.0 * x * (1.0 - x)

    def update(self, x: float, r0_score: float = 0.5) -> float:
        """One timestep of the URE equation of motion.

        Corrected formulation — learning is directional toward Omega:

          x(t+1) = x(t) + (α×γ(x) + β − δ×r0) × (Ω − x)

        The coefficient (α×γ+β−δ×r0) modulates the STRENGTH of the destiny pull.
        γ(x) is maximum at HIHO (x=0.5): the attractor is most powerful there.
        x=0.5 (Omega) is always a STABLE fixed point when α×γ(Ω)+β > δ×r0,
        which holds with the default parameters (0.06 > 0.025). ✓

        Parameters
        ----------
        x : float
            Current coherence state [0, 1].
        r0_score : float
            R0 adversarial challenge score [0, 1]. Default 0.5 (neutral challenge).

        Returns
        -------
        float
            Next coherence state, clamped to [0, 1].
        """
        x = max(0.0, min(1.0, float(x)))
        # Modulated destiny pull: HIHO kernel × direction + regularization − adversarial
        coefficient = self.alpha * self.gamma(x) + self.beta - self.delta * r0_score
        dx = coefficient * (self.omega - x)
        return max(0.0, min(1.0, x + dx))

    def converged(self, x: float, tol: float = 0.05) -> bool:
        """True when the loop has reached the Omega (HIHO) attractor."""
        return abs(x - self.omega) <= tol

    def trajectory(
        self,
        x0: float = 0.1,
        steps: int = 50,
        r0_fn: Callable[[float], float] | None = None,
    ) -> list[float]:
        """Simulate the compound loop trajectory over N steps.

        Parameters
        ----------
        x0 : float
            Initial coherence state.
        steps : int
            Number of update steps.
        r0_fn : callable, optional
            Function mapping x → r0_score. Defaults to gamma(x) (self-challenge).

        Returns
        -------
        list[float]
            Sequence of coherence states x(0), x(1), ..., x(steps).
        """
        if r0_fn is None:
            r0_fn = self.gamma
        path = [max(0.0, min(1.0, float(x0)))]
        x = path[0]
        for _ in range(steps):
            x = self.update(x, r0_score=r0_fn(x))
            path.append(x)
        return path

    def steps_to_convergence(
        self,
        x0: float = 0.1,
        max_steps: int = 200,
        tol: float = 0.05,
    ) -> int:
        """Return number of steps to reach Omega attractor, or max_steps if not."""
        x = max(0.0, min(1.0, float(x0)))
        for step in range(max_steps):
            if self.converged(x, tol):
                return step
            x = self.update(x)
        return max_steps

    def to_dict(self) -> dict[str, float]:
        """Serialize all five Greek parameters for logging/SurrealDB storage."""
        return {
            "alpha": self.alpha,
            "omega": self.omega,
            "delta": self.delta,
            "beta": self.beta,
            "gamma_at_hiho": self.gamma(self.omega),
        }
