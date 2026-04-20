"""Seed-based agent population generation.

Each agent is a unique initial 256D latent state vector.
Deterministic: same seed + agent count always produces identical population.
"""

from __future__ import annotations

import numpy as np


class AgentFactory:
    """Generate initial latent states for agent populations."""

    @staticmethod
    def create_batch(
        n_agents: int,
        seed: int,
        z_dim: int = 256,
        distribution: str = "normal",
    ) -> np.ndarray:
        """Create agent population as [n_agents, z_dim] float32 array.

        Parameters
        ----------
        n_agents : int
            Number of agents to generate.
        seed : int
            RNG seed for reproducibility.
        z_dim : int
            Latent space dimensionality (default 256).
        distribution : str
            One of "normal", "uniform", "sphere".

        Returns
        -------
        np.ndarray
            Shape [n_agents, z_dim], dtype float32.
        """
        rng = np.random.default_rng(seed)

        if distribution == "normal":
            # Gaussian centered at HIHO target (0.5) with tight spread
            return rng.normal(0.5, 0.25, (n_agents, z_dim)).astype(np.float32)
        elif distribution == "uniform":
            # Uniform on [0, 1] centered at HIHO target (0.5)
            return rng.uniform(0.0, 1.0, (n_agents, z_dim)).astype(np.float32)
        elif distribution == "sphere":
            # Small sphere surface centered at HIHO target (0.5)
            raw = rng.normal(0, 1, (n_agents, z_dim)).astype(np.float32)
            norms = np.linalg.norm(raw, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-8)  # Avoid division by zero
            return (raw / norms * 0.25 + 0.5).astype(np.float32)
        else:
            raise ValueError(f"Unknown distribution: {distribution}")
