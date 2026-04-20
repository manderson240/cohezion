"""Reward shaping functions for FLUME navigation RL.

Provides composable reward components that can be combined
for different training objectives.
"""

from __future__ import annotations

import math

import numpy as np


class CoherenceReward:
    """Reward based on HIHO coherence (peak at 0.5).

    Parameters
    ----------
    target : float
        Target coherence value (default 0.5).
    sigma : float
        Width of the Gaussian reward peak (default 0.25).
    scale : float
        Maximum reward magnitude (default 1.0).
    """

    def __init__(self, target: float = 0.5, sigma: float = 0.25, scale: float = 1.0) -> None:
        self.target = target
        self.sigma = sigma
        self.scale = scale

    def __call__(self, coherence: float) -> float:
        deviation = (coherence - self.target) / self.sigma
        return self.scale * math.exp(-(deviation * deviation))


class DiversityBonus:
    """Bonus reward for maintaining diverse latent dimensions.

    Penalizes collapse where all dimensions converge to the same value.
    Rewards when the standard deviation across dimensions is healthy.

    Parameters
    ----------
    min_std : float
        Minimum acceptable std for full bonus (default 0.05).
    scale : float
        Maximum bonus (default 0.3).
    """

    def __init__(self, min_std: float = 0.05, scale: float = 0.3) -> None:
        self.min_std = min_std
        self.scale = scale

    def __call__(self, state: np.ndarray) -> float:
        std = float(np.std(state))
        if std >= self.min_std:
            return self.scale
        return self.scale * (std / self.min_std)


class StabilityPenalty:
    """Penalty for large state changes (encourages smooth trajectories).

    Parameters
    ----------
    threshold : float
        Maximum acceptable delta norm before penalty (default 0.5).
    scale : float
        Maximum penalty magnitude (default 0.5).
    """

    def __init__(self, threshold: float = 0.5, scale: float = 0.5) -> None:
        self.threshold = threshold
        self.scale = scale

    def __call__(self, prev_state: np.ndarray, curr_state: np.ndarray) -> float:
        delta_norm = float(np.linalg.norm(curr_state - prev_state))
        if delta_norm <= self.threshold:
            return 0.0
        excess = (delta_norm - self.threshold) / self.threshold
        return -self.scale * min(excess, 1.0)


class HamiltonianReward:
    """Reward based on negative Hamiltonian potential energy.

    Lower potential energy = higher reward. Uses HIHO_WELL potential
    which has its minimum at the HIHO 0.5 target.

    Parameters
    ----------
    potential : str
        Potential type: "hiho_well", "double_well", or "harmonic".
    scale : float
        Reward scaling factor (default 0.5).
    """

    def __init__(self, potential: str = "hiho_well", scale: float = 0.5) -> None:
        from cohezion.physics.hamiltonian import HamiltonianDynamics, PotentialType

        pot_type = PotentialType(potential)
        self.dynamics = HamiltonianDynamics(potential=pot_type)
        self.scale = scale

    def __call__(self, state: np.ndarray) -> float:
        """Compute reward as negative mean potential energy."""
        energy = self.dynamics.energy(state)
        # Negative energy = reward (lower energy is better)
        return self.scale * float(-np.mean(energy))


class CompositeReward:
    """Combine multiple reward components with weights.

    Parameters
    ----------
    coherence_weight : float
        Weight for CoherenceReward (default 1.0).
    diversity_weight : float
        Weight for DiversityBonus (default 0.3).
    stability_weight : float
        Weight for StabilityPenalty (default 0.2).
    hamiltonian_weight : float
        Weight for HamiltonianReward (default 0.0, opt-in).
    """

    def __init__(
        self,
        coherence_weight: float = 1.0,
        diversity_weight: float = 0.3,
        stability_weight: float = 0.2,
        hamiltonian_weight: float = 0.0,
    ) -> None:
        self.coherence_reward = CoherenceReward()
        self.diversity_bonus = DiversityBonus()
        self.stability_penalty = StabilityPenalty()
        self.hamiltonian_reward = HamiltonianReward() if hamiltonian_weight > 0 else None
        self.coherence_weight = coherence_weight
        self.diversity_weight = diversity_weight
        self.stability_weight = stability_weight
        self.hamiltonian_weight = hamiltonian_weight

    def __call__(
        self,
        coherence: float,
        state: np.ndarray,
        prev_state: np.ndarray | None = None,
    ) -> float:
        reward = self.coherence_weight * self.coherence_reward(coherence)
        reward += self.diversity_weight * self.diversity_bonus(state)
        if prev_state is not None:
            reward += self.stability_weight * self.stability_penalty(prev_state, state)
        if self.hamiltonian_reward is not None:
            reward += self.hamiltonian_weight * self.hamiltonian_reward(state)
        return reward
