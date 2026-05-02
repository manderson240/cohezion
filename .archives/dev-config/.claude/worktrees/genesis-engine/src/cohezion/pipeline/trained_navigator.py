"""Trained navigator — wraps a PolicyNetwork for use in mass simulation.

Replaces the Rust FlumePhysics navigator with a Python RL policy
that has been trained on the FlumeNav-v0 environment. This allows
comparing trained vs random navigation coherence.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch


logger = logging.getLogger(__name__)


class TrainedNavigator:
    """Wrap a trained PolicyNetwork for batch navigation in mass_sim.

    Parameters
    ----------
    checkpoint_path : str or Path
        Path to a .pt file containing a PolicyNetwork state_dict.
    action_scale : float
        Scale factor applied to policy output (default 0.01).
    """

    def __init__(
        self,
        checkpoint_path: str | Path,
        action_scale: float = 0.01,
    ) -> None:
        from cohezion.pipeline.weight_bridge import WeightBridge

        self.policy = WeightBridge.load_policy_network(checkpoint_path)
        self.action_scale = action_scale
        self._checkpoint_path = Path(checkpoint_path)
        logger.info(
            "TrainedNavigator loaded from %s (action_scale=%.4f)",
            checkpoint_path,
            action_scale,
        )

    def navigate_batch(self, states: np.ndarray) -> np.ndarray:
        """Compute navigation deltas for a batch of agent states.

        Parameters
        ----------
        states : np.ndarray
            Shape [n_agents, z_dim], current agent positions in latent space.

        Returns
        -------
        np.ndarray
            Shape [n_agents, z_dim], delta vectors to apply to agent states.
            These are already scaled by action_scale.
        """
        with torch.no_grad():
            state_tensor = torch.FloatTensor(states)
            mean, _std = self.policy(state_tensor)
            # Use deterministic mean action (no sampling during simulation)
            deltas = mean.numpy()

        return deltas.astype(np.float32) * self.action_scale

    def navigate_single(self, state: np.ndarray) -> np.ndarray:
        """Compute navigation delta for a single agent state.

        Parameters
        ----------
        state : np.ndarray
            Shape [z_dim], single agent position.

        Returns
        -------
        np.ndarray
            Shape [z_dim], delta vector.
        """
        return self.navigate_batch(state[np.newaxis])[0]

    @property
    def checkpoint_path(self) -> Path:
        """Path to the loaded checkpoint."""
        return self._checkpoint_path
