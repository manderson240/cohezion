r"""Poincare Markov Chain & State Transition Matrix Engine
=========================================================
Implements Markov Chain stochastic state transition matrices P_ij
on high-dimensional Poincaré manifolds (12D, 2048D).

Formulation:
  - Transition Probability: P(S_{t+1} = j | S_t = i) = softmax(-d_H(u_i, u_j) / tau)
  - Stationary Distribution: \pi P = \pi
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND


@dataclass(frozen=True, slots=True)
class MarkovStateTransition:
    current_state_idx: int
    next_state_idx: int
    probability: float
    entropy: float


class PoincareMarkovChain:
    """Stochastic Markov Chain transition engine over Poincaré manifold states."""

    def __init__(self, states: Sequence[PoincarePoint], temperature: float = 1.0) -> None:
        if not states:
            raise ValueError("Markov chain requires at least one state point")
        self.states = tuple(states)
        self.temperature = temperature
        self.transition_matrix = self._compute_transition_matrix()

    def _compute_transition_matrix(self) -> list[list[float]]:
        n = len(self.states)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]

        for i in range(n):
            distances = [PoincareManifoldND.distance(self.states[i], self.states[j]) for j in range(n)]
            logits = [-d / max(1e-4, self.temperature) for d in distances]
            max_logit = max(logits)
            exp_logits = [math.exp(l - max_logit) for l in logits]
            sum_exp = sum(exp_logits)
            matrix[i] = [e / sum_exp for e in exp_logits]

        return matrix

    def predict_next_state(self, current_idx: int) -> MarkovStateTransition:
        """Predict stochastic next state transition and calculate transition entropy."""
        n = len(self.states)
        if current_idx < 0 or current_idx >= n:
            raise ValueError(f"State index {current_idx} out of bounds")

        probs = self.transition_matrix[current_idx]
        next_idx = max(range(n), key=lambda j: probs[j])

        entropy = -sum(p * math.log(p + 1e-12) for p in probs)

        return MarkovStateTransition(
            current_state_idx=current_idx,
            next_state_idx=next_idx,
            probability=round(probs[next_idx], 4),
            entropy=round(entropy, 4),
        )
