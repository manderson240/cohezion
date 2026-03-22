"""HIHO Vector Engine — Half-In-Half-Out stability scoring.

Computes stability scores based on the HIHO principle:
maximum stability at exactly 50% coherence overlap.
The score peaks at 0.5 and falls off symmetrically.
"""

from __future__ import annotations

import math


class HihoVectorEngine:
    """Score vectors for HIHO stability (peak at 0.5 coherence).

    The stability function is a Gaussian centered at 0.5:
        score = exp(-((x - 0.5) / sigma)^2)

    Parameters
    ----------
    sigma : float
        Width of the stability well. Smaller = sharper peak at 0.5.
        Default 0.25 gives ~0.37 score at x=0.0 or x=1.0.
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
