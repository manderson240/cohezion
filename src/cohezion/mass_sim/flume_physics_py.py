"""Pure-Python FlumePhysics fallback for when the Rust extension is unavailable.

Implements the same interface as cohezion_core_rs.FlumePhysics using numpy.
~10x slower than Rust+rayon but functionally identical.

Architecture:
  - 2-layer MLP (z_dim -> hidden_dim -> z_dim) with LayerNorm
  - HIHO damping: attractor toward 0.5 equilibrium
  - Delta scaling: controls step size per epoch
"""

from __future__ import annotations

import numpy as np


class FlumePhysicsPy:
    """Pure-Python implementation of the FLUME physics engine.

    Parameters match the Rust constructor exactly:
        w1: [hidden_dim, z_dim] - first layer weights
        b1: [hidden_dim] - first layer bias
        w2: [z_dim, hidden_dim] - second layer weights
        b2: [z_dim] - second layer bias
        gamma: [hidden_dim] - LayerNorm scale
        beta: [hidden_dim] - LayerNorm shift
        delta_scale: float - step size multiplier
        hiho_damping: float - attractor strength toward 0.5
    """

    def __init__(
        self,
        w1: np.ndarray,
        b1: np.ndarray,
        w2: np.ndarray,
        b2: np.ndarray,
        gamma: np.ndarray,
        beta: np.ndarray,
        *,
        delta_scale: float = 0.01,
        hiho_damping: float = 0.05,
    ):
        self.w1 = np.asarray(w1, dtype=np.float32)
        self.b1 = np.asarray(b1, dtype=np.float32)
        self.w2 = np.asarray(w2, dtype=np.float32)
        self.b2 = np.asarray(b2, dtype=np.float32)
        self.gamma = np.asarray(gamma, dtype=np.float32)
        self.beta = np.asarray(beta, dtype=np.float32)
        self.delta_scale = delta_scale
        self.hiho_damping = hiho_damping

    def _forward(self, z: np.ndarray) -> np.ndarray:
        """Single forward pass: z -> delta_z.

        z: [batch, z_dim]
        returns: [batch, z_dim] delta to apply
        """
        # Layer 1: z_dim -> hidden_dim
        h = z @ self.w1.T + self.b1  # [batch, hidden_dim]

        # LayerNorm
        mean = h.mean(axis=-1, keepdims=True)
        var = h.var(axis=-1, keepdims=True)
        h_norm = (h - mean) / np.sqrt(var + 1e-5)
        h_norm = self.gamma * h_norm + self.beta

        # ReLU activation
        h_act = np.maximum(h_norm, 0)

        # Layer 2: hidden_dim -> z_dim
        delta = h_act @ self.w2.T + self.b2  # [batch, z_dim]

        return delta

    def _step(self, z: np.ndarray) -> np.ndarray:
        """Single simulation step with HIHO damping.

        z: [batch, z_dim]
        returns: [batch, z_dim] updated states
        """
        # Compute delta from network
        delta = self._forward(z)

        # Apply delta with scaling
        z_new = z + delta * self.delta_scale

        # HIHO damping: pull toward 0.5 equilibrium
        z_new = z_new + self.hiho_damping * (0.5 - z_new)

        return z_new.astype(np.float32)

    def simulate_epochs_batch(self, agents: np.ndarray, n_epochs: int) -> np.ndarray:
        """Simulate agents for n_epochs without navigation.

        Parameters
        ----------
        agents : np.ndarray
            Shape [n_agents, z_dim], current states.
        n_epochs : int
            Number of epochs to simulate.

        Returns
        -------
        np.ndarray
            Shape [n_agents, z_dim], evolved states.
        """
        current = np.asarray(agents, dtype=np.float32)
        for _ in range(n_epochs):
            current = self._step(current)
        return current

    def simulate_epochs_navigated(self, agents: np.ndarray, n_epochs: int) -> np.ndarray:
        """Simulate with navigator (adds small noise for exploration).

        Same as batch but with stochastic perturbation per epoch.
        """
        current = np.asarray(agents, dtype=np.float32)
        for _ in range(n_epochs):
            current = self._step(current)
            # Navigator: small Gaussian noise for exploration
            noise = np.random.randn(*current.shape).astype(np.float32) * 0.001
            current = current + noise
        return current

    def compute_batch_stats(self, agents: np.ndarray) -> dict:
        """Compute population statistics matching Rust output format.

        Parameters
        ----------
        agents : np.ndarray
            Shape [n_agents, z_dim].

        Returns
        -------
        dict
            Keys: mean_coherence, std_coherence, mean_norm, pct_within_bounds,
                  dim_means, dim_stds, min_coherence, max_coherence.
        """
        agents = np.asarray(agents, dtype=np.float32)

        # Coherence: mean of each agent's dimensions (how close to 0.5)
        agent_means = agents.mean(axis=1)  # [n_agents]

        # Per-dimension statistics
        dim_means = agents.mean(axis=0).tolist()  # [z_dim]
        dim_stds = agents.std(axis=0).tolist()  # [z_dim]

        # Norms
        norms = np.linalg.norm(agents, axis=1)  # [n_agents]

        # Within HIHO bounds [0.3, 0.7]
        is_in_bounds = (agents >= 0.3) & (agents <= 0.7)
        # fraction of agents where all dims in range (backward compatibility)
        pct_within = float(np.all(is_in_bounds, axis=1).mean())
        # fraction of all (agent, dim) pairs in bounds
        pct_elements_within = float(is_in_bounds.mean())
        # fraction of agents where >80% of dims are in bounds
        pct_majority = float((is_in_bounds.mean(axis=1) > 0.8).mean())

        return {
            "mean_coherence": float(agent_means.mean()),
            "std_coherence": float(agent_means.std()),
            "min_coherence": float(agent_means.min()),
            "max_coherence": float(agent_means.max()),
            "mean_norm": float(norms.mean()),
            "pct_within_bounds": pct_within,
            "pct_elements_within_bounds": pct_elements_within,
            "pct_agents_majority_in_bounds": pct_majority,
            "dim_means": dim_means,
            "dim_stds": dim_stds,
            "n_agents": int(agents.shape[0]),
            "z_dim": int(agents.shape[1]),
        }
