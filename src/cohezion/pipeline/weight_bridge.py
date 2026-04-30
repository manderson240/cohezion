"""Weight bridge — transfer trained RL policy weights into the Rust FlumePhysics engine.

The PolicyNetwork has 3 weight layers (shared[0], shared[2], mean_head) but
FlumePhysics only has 2 (w1, w2). We collapse the intermediate layer via
matrix multiplication so the Rust engine gets an equivalent 2-layer network.

Mapping:
    w1, b1  <-  shared[0].weight, shared[0].bias        (256->128)
    w2, b2  <-  mean_head.weight @ shared[2].weight,     (collapsed 128->128->256)
                mean_head.bias + mean_head.weight @ shared[2].bias
    gamma   <-  ones(hidden_dim)    (LayerNorm scale)
    beta    <-  full(hidden_dim, 0.5) (LayerNorm shift to HIHO target)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch


logger = logging.getLogger(__name__)


def _import_flume_physics():
    """Import FlumePhysics from Rust extension with graceful fallback."""
    try:
        from cohezion_core.cohezion_core_rs import FlumePhysics

        return FlumePhysics
    except ImportError:
        logger.warning("cohezion_core_rs not available — FlumePhysics unavailable")
        return None


class WeightBridge:
    """Transfers trained PolicyNetwork weights into the Rust FlumePhysics engine.

    The RL policy has 3 linear layers but the Rust engine expects 2.
    We collapse the intermediate hidden layer via matrix multiplication
    to produce equivalent 2-layer weights.
    """

    @staticmethod
    def load_policy_network(checkpoint_path: str | Path) -> Any:
        """Load a trained PolicyNetwork from a .pt checkpoint.

        Parameters
        ----------
        checkpoint_path : str | Path
            Path to a .pt file containing a PolicyNetwork state_dict.

        Returns
        -------
        PolicyNetwork
            Ready-to-use policy network with loaded weights.
        """
        from cohezion.rl.trainer import PolicyNetwork

        checkpoint_path = Path(checkpoint_path)
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)

        # Infer dimensions from the state dict
        # shared.0.weight shape is [hidden, state_dim]
        hidden_dim, state_dim = state_dict["shared.0.weight"].shape
        # mean_head.weight shape is [action_dim, hidden]
        action_dim = state_dict["mean_head.weight"].shape[0]

        policy = PolicyNetwork(state_dim=state_dim, action_dim=action_dim, hidden=hidden_dim)
        policy.load_state_dict(state_dict)
        policy.eval()

        logger.info(
            "Loaded PolicyNetwork from %s (state=%d, hidden=%d, action=%d)",
            checkpoint_path,
            state_dim,
            hidden_dim,
            action_dim,
        )
        return policy

    @staticmethod
    def policy_to_flume_weights(checkpoint_path: str | Path) -> dict[str, np.ndarray]:
        """Extract and collapse policy weights for the Rust FlumePhysics engine.

        The PolicyNetwork has layers:
            shared[0]: Linear(state_dim, hidden)   -> w1, b1
            shared[2]: Linear(hidden, hidden)       -> no Rust counterpart
            mean_head: Linear(hidden, action_dim)   -> w2, b2

        We collapse shared[2] and mean_head into a single layer:
            w2 = mean_head.weight @ shared[2].weight
            b2 = mean_head.bias + mean_head.weight @ shared[2].bias

        Parameters
        ----------
        checkpoint_path : str | Path
            Path to a .pt file containing a PolicyNetwork state_dict.

        Returns
        -------
        dict[str, np.ndarray]
            Keys: w1, b1, w2, b2, gamma, beta — all float32 numpy arrays.
        """
        state_dict = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=True)

        # Layer 1: shared[0] maps directly to w1, b1
        # PyTorch Linear stores weight as [out_features, in_features]
        # Rust expects w1 as [hidden, input] — same layout
        w1 = state_dict["shared.0.weight"].numpy().astype(np.float32)
        b1 = state_dict["shared.0.bias"].numpy().astype(np.float32)

        # Layer 2: collapse shared[2] + mean_head into w2, b2
        # shared[2].weight: [hidden, hidden]
        # mean_head.weight: [action_dim, hidden]
        shared2_weight = state_dict["shared.2.weight"]
        shared2_bias = state_dict["shared.2.bias"]
        mean_weight = state_dict["mean_head.weight"]
        mean_bias = state_dict["mean_head.bias"]

        # Matrix multiply: [action_dim, hidden] @ [hidden, hidden] = [action_dim, hidden]
        w2 = (mean_weight @ shared2_weight).numpy().astype(np.float32)
        b2 = (mean_bias + mean_weight @ shared2_bias).numpy().astype(np.float32)

        # LayerNorm defaults: gamma=1 (scale), beta=0.5 (HIHO target shift)
        hidden_dim = w1.shape[0]
        gamma = np.ones(hidden_dim, dtype=np.float32)
        beta = np.full(hidden_dim, 0.5, dtype=np.float32)

        logger.info(
            (
                "Extracted weights — w1: %s (norm=%.3f), w2: %s (norm=%.3f), b1 norm=%.3f, b2 "
                "norm=%.3f"
            ),
            w1.shape,
            np.linalg.norm(w1),
            w2.shape,
            np.linalg.norm(w2),
            np.linalg.norm(b1),
            np.linalg.norm(b2),
        )

        return {
            "w1": w1,
            "b1": b1,
            "w2": w2,
            "b2": b2,
            "gamma": gamma,
            "beta": beta,
        }

    @staticmethod
    def policy_to_flume_physics(
        checkpoint_path: str | Path,
        delta_scale: float = 0.01,
        hiho_damping: float = 0.01,
    ):
        """Convert a trained policy checkpoint into a FlumePhysics instance.

        Parameters
        ----------
        checkpoint_path : str | Path
            Path to a .pt file containing a PolicyNetwork state_dict.
        delta_scale : float
            Scale factor for state updates per epoch.
        hiho_damping : float
            HIHO attractor strength toward 0.5 equilibrium.

        Returns
        -------
        FlumePhysics
            Rust physics engine initialized with trained weights.

        Raises
        ------
        RuntimeError
            If the Rust extension is not available.
        """
        FlumePhysics = _import_flume_physics()
        if FlumePhysics is None:
            raise RuntimeError(
                "cohezion_core_rs not available — cannot create FlumePhysics. "
                "Build with: cd src/cohezion_core && maturin develop --release"
            )

        weights = WeightBridge.policy_to_flume_weights(checkpoint_path)

        physics = FlumePhysics(
            weights["w1"],
            weights["b1"],
            weights["w2"],
            weights["b2"],
            weights["gamma"],
            weights["beta"],
            delta_scale=delta_scale,
            hiho_damping=hiho_damping,
        )

        logger.info(
            "Created FlumePhysics from %s (delta_scale=%.4f, hiho_damping=%.4f)",
            checkpoint_path,
            delta_scale,
            hiho_damping,
        )
        return physics

    @staticmethod
    def validate_coherence(
        physics: Any,
        n_agents: int = 100,
        n_epochs: int = 100,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run a short simulation to validate coherence of transferred weights.

        Creates test agents near the HIHO target (N(0.5, 0.25)) and runs
        them through the physics engine to check coherence stays in bounds.

        Parameters
        ----------
        physics : FlumePhysics
            A Rust physics engine instance to validate.
        n_agents : int
            Number of test agents.
        n_epochs : int
            Number of simulation epochs.
        seed : int
            Random seed for agent initialization.

        Returns
        -------
        dict
            mean_coherence: float, pct_within_bounds: float, valid: bool.
            valid is True if mean_coherence is in [0.3, 0.7].
        """
        rng = np.random.default_rng(seed)
        agents = rng.normal(0.5, 0.25, (n_agents, 256)).astype(np.float32)

        evolved = physics.simulate_epochs_navigated(agents, n_epochs)
        stats = physics.compute_batch_stats(evolved)

        mean_coherence = float(stats.get("mean_coherence", 0.0))
        pct_within = float(stats.get("pct_within_bounds", 0.0))
        valid = 0.3 <= mean_coherence <= 0.7

        logger.info(
            "Validation: mean_coherence=%.4f, pct_within_bounds=%.1f%%, valid=%s",
            mean_coherence,
            pct_within * 100 if pct_within <= 1.0 else pct_within,
            valid,
        )

        return {
            "mean_coherence": mean_coherence,
            "pct_within_bounds": pct_within,
            "valid": valid,
        }
