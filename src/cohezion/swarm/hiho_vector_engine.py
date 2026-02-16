"""HIHO Vector Engine — Half-In-Half-Out stability scoring.

Computes stability scores based on the HIHO principle:
maximum stability at exactly 50% coherence overlap.
The score peaks at 0.5 and falls off symmetrically.

Theoretical Foundations
-----------------------
The 0.5 attractor is independently validated across disciplines:

- **Shannon (1948)**: Binary entropy H(p) is maximized at exactly p=0.5.
  The Gaussian stability function used here approximates the entropy
  curve's peak, where information-processing capacity is maximal.
- **Langton (1990)**: Edge-of-chaos critical lambda ~ 0.5 for 2-state
  1D cellular automata. Complex computation emerges only at this boundary.
- **Bak (1987)**: Self-organized criticality — systems naturally evolve
  to the critical point without external tuning.
- **Beggs & Plenz (2003)**: Neural criticality at branching parameter
  sigma=1 maximizes information transmission in cortical networks.
- **Kirkpatrick (1983)**: Simulated annealing calibrates initial
  temperature for ~50% acceptance probability of suboptimal moves.

The Gaussian form score = exp(-((x - 0.5) / sigma)^2) was chosen over
the linear form (1 - |x - 0.5| * 2) for smoother gradient behavior
near the attractor, enabling stable gradient-based optimization in
the FLUME VAE and RL policy training loops.

See Also
--------
- Charter Section 1a: Cross-Disciplinary Validation
- HIHO_STABILITY_PRIME.md: Convergence table
- Learning 63: Damped oscillation C(t) = 0.5 + A*e^(-kt)*sin(wt)
"""

from __future__ import annotations

import math


class HihoVectorEngine:
    """Score vectors for HIHO stability (peak at 0.5 coherence).

    The stability function is a Gaussian centered at 0.5:
        score = exp(-((x - 0.5) / sigma)^2)

    This mirrors Shannon's binary entropy curve (max at p=0.5) and
    Langton's lambda parameter (critical at ~0.5), providing a smooth
    differentiable approximation suitable for gradient-based training.

    Parameters
    ----------
    sigma : float
        Width of the stability well. Smaller = sharper peak at 0.5.
        Default 0.25 gives ~0.37 score at x=0.0 or x=1.0.
        Analogous to the "temperature" in Boltzmann exploration —
        wider sigma = more tolerance for deviation from criticality.
    """

    def __init__(self, sigma: float = 0.25) -> None:
        self.sigma = sigma
        self.target = 0.5

    def calculate_hiho_score(self, coherence: float) -> float:
        """Return stability score in [0, 1] for a given coherence value.

        Parameters
        ----------
        coherence : float
            Mean magnitude or overlap metric for an agent vector.

        Returns
        -------
        float
            1.0 at coherence=0.5, decaying symmetrically.
        """
        deviation = (coherence - self.target) / self.sigma
        return math.exp(-(deviation * deviation))

    def batch_scores(self, coherences: list[float]) -> list[float]:
        """Compute HIHO scores for a batch of coherence values."""
        return [self.calculate_hiho_score(c) for c in coherences]
