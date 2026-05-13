"""
JEPAWorldModel with SurrealDB Persistence

Extends base JEPAWorldModel with trajectory storage and dream rollouts.

Usage:
    from cohezion.world_model.jepa_world_model import JEPAWorldModel, generate_synthetic_training_data
    from cohezion.persistence.genesis_persistence import SurrealDBConnection

    db = SurrealDBConnection()
    model = JEPAWorldModelPersistent(
        db_connection=db,
        state_dim=12,
        action_dim=12
    )

    # Training with auto-storage
    data = generate_synthetic_training_data(n_samples=100)
    metrics = model.train_epoch_with_persistence(data)

    # Dream rollouts
    imagined = model.dream_rollout(n_steps=50)
"""

import time
from collections.abc import Callable

import numpy as np

from cohezion.world_model.jepa_world_model import JEPAWorldModel


class JEPAWorldModelPersistent(JEPAWorldModel):
    """JEPA World Model with SurrealDB persistence and dream rollouts."""

    def __init__(self, db_connection=None, *args, buffer_size: int = 100, **kwargs):
        """
        Initialize with SurrealDB connection.

        Args:
            db_connection: SurrealDBConnection or None for local-only mode
            buffer_size: Number of trajectories to buffer before DB flush
        """
        super().__init__(*args, **kwargs)
        self.db = db_connection
        self.trajectory_buffer = []
        self.buffer_size = buffer_size

    def store_trajectory(
        self,
        state: np.ndarray,
        action: np.ndarray,
        next_state: np.ndarray,
        reward: float = 0.0,
        info: dict | None = None,
    ) -> bool:
        """
        Store a single trajectory transition.

        Buffers locally and flushes to SurrealDB when buffer is full.
        """
        trajectory = {
            "state": state.tolist() if hasattr(state, "tolist") else state,
            "action": action.tolist() if hasattr(action, "tolist") else action,
            "next_state": next_state.tolist() if hasattr(next_state, "tolist") else next_state,
            "reward": float(reward),
            "timestamp": time.time(),
            "info": info or {},
        }

        self.trajectory_buffer.append(trajectory)

        if len(self.trajectory_buffer) >= self.buffer_size and self.db:
            return self._flush_buffer()
        return True

    def _flush_buffer(self) -> bool:
        """Flush local buffer to SurrealDB."""
        if not self.db or not self.trajectory_buffer:
            return False

        try:
            # Store to SurrealDB if method exists
            if hasattr(self.db, "create"):
                for traj in self.trajectory_buffer:
                    self.db.create("trajectory", traj)
            elif hasattr(self.db, "store"):
                for traj in self.trajectory_buffer:
                    self.db.store(traj)
            else:
                # Store to internal list
                if not hasattr(self.db, "_trajectories"):
                    self.db._trajectories = []
                self.db._trajectories.extend(self.trajectory_buffer)

            self.trajectory_buffer = []
            return True
        except Exception as e:
            print(f"Error flushing buffer: {e}")
            return False

    def load_trajectories(self, n: int = 100, filter_func: Callable | None = None) -> list[dict]:
        """Load trajectories from SurrealDB."""
        if self.db is None:
            return []

        try:
            # Flush buffer first
            if self.trajectory_buffer:
                self._flush_buffer()

            # Load from database
            if hasattr(self.db, "query"):
                trajs = self.db.query(f"SELECT * FROM trajectory LIMIT {n}")
            elif hasattr(self.db, "load"):
                trajs = self.db.load(n)
            elif hasattr(self.db, "_trajectories"):
                trajs = self.db._trajectories[-n:]
            else:
                trajs = []

            if filter_func:
                trajs = [t for t in trajs if filter_func(t)]

            return trajs
        except Exception as e:
            print(f"Error loading trajectories: {e}")
            return []

    def dream_rollout(
        self, n_steps: int = 50, temperature: float = 0.7, start_state: np.ndarray | None = None
    ) -> list[dict]:
        """
        Generate imagined trajectory using world model.

        Args:
            n_steps: Number of steps to imagine
            temperature: 0=deterministic, 1=highly random
            start_state: Starting state (or sample from history)

        Returns:
            List of imagined trajectory steps
        """
        if self.db is None:
            return self._synthetic_dream(n_steps)

        # Load past trajectories for context
        past = self.load_trajectories(n=1000)

        if len(past) < 10:
            return self._synthetic_dream(n_steps)

        # Determine starting state
        if start_state is None:
            start_state = np.array(past[-1]["next_state"])

        # Generate imagined trajectory
        imagined = []
        state = start_state

        for step in range(n_steps):
            # Sample action from past trajectories
            if past:
                action = np.array(past[np.random.randint(len(past))]["action"])
            else:
                action = np.random.randn(self.action_dim) * 0.1

            # Predict next state using learned model
            next_state = self.predict_next_state(state, action)

            # Add imagination noise scaled by temperature
            noise = np.random.randn(*next_state.shape) * temperature * 0.1
            next_state = next_state + noise

            imagined.append(
                {
                    "state": state.copy(),
                    "action": action.copy(),
                    "next_state": next_state.copy(),
                    "step": step,
                    "imagined": True,
                }
            )

            state = next_state

        return imagined

    def _synthetic_dream(self, n_steps: int) -> list[dict]:
        """Fallback synthetic dream rollouts."""
        return [{"step": i, "synthetic": True} for i in range(n_steps)]

    def train_epoch_with_persistence(self, data: list, batch_size: int = 32) -> dict:
        """
        Train and store trajectories to SurrealDB.

        Args:
            data: List of (state, action, next_state, reward) tuples
            batch_size: Training batch size

        Returns:
            Training metrics
        """
        # Standard training
        metrics = super().train_epoch(data, batch_size)

        # Store transitions to SurrealDB
        for batch in data:
            if len(batch) == 3:  # (state, action, next_state)
                state, action, next_state = batch
                reward = 0.0
            elif len(batch) == 4:  # (state, action, next_state, reward)
                state, action, next_state, reward = batch[:4]
            else:
                continue

            self.store_trajectory(np.array(state), np.array(action), np.array(next_state), float(reward))

        # Flush remaining buffer
        if self.trajectory_buffer:
            self._flush_buffer()

        return metrics


# Backwards compatibility alias
JEPAWorldModelWithPersistence = JEPAWorldModelPersistent
