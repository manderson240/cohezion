"""Gymnasium-compatible RL environment for FLUME manifold navigation.

State:  256D latent vector (agent position in FLUME space)
Action: 256D delta vector (continuous action space)
Reward: Coherence score (peak at HIHO 0.5 target)

Register as: cohezion/FlumeNav-v0
"""

from __future__ import annotations

import logging
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces


logger = logging.getLogger(__name__)


class FlumeNavEnv(gym.Env):
    """Navigate a 256D FLUME manifold toward HIHO 0.5 coherence.

    The agent controls a position in latent space. Each step applies
    the agent's action as a delta, then runs one epoch of physics
    (either Hamiltonian or jitter). The reward is the coherence score
    relative to the HIHO 0.5 target.

    Parameters
    ----------
    z_dim : int
        Latent space dimensionality (default 256).
    max_steps : int
        Maximum steps per episode (default 200).
    dt : float
        Physics timestep (default 0.01).
    temperature : float
        Thermal noise magnitude (default 0.01).
    use_hamiltonian : bool
        If True, apply double-well Hamiltonian dynamics (default True).
    action_scale : float
        Scale factor for actions (default 0.01).
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    def __init__(
        self,
        z_dim: int = 256,
        max_steps: int = 200,
        dt: float = 0.01,
        temperature: float = 0.01,
        use_hamiltonian: bool = True,
        action_scale: float = 0.01,
        render_mode: str | None = None,
        use_composite_reward: bool = True,
    ):
        super().__init__()
        self.z_dim = z_dim
        self.max_steps = max_steps
        self.dt = dt
        self.temperature = temperature
        self.use_hamiltonian = use_hamiltonian
        self.action_scale = action_scale
        self.render_mode = render_mode
        self.use_composite_reward = use_composite_reward

        # Continuous observation and action spaces
        self.observation_space = spaces.Box(low=-2.0, high=2.0, shape=(z_dim,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(z_dim,), dtype=np.float32)

        self._state: np.ndarray | None = None
        self._prev_state: np.ndarray | None = None
        self._step_count = 0
        self._episode_coherences: list[float] = []

        if use_composite_reward:
            from cohezion.rl.reward_shaping import CompositeReward

            self._reward_fn = CompositeReward(hamiltonian_weight=0.3)
        else:
            self._reward_fn = None

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Reset environment to initial state near HIHO target."""
        super().reset(seed=seed)

        # Initialize near 0.5 with small noise
        self._state = self.np_random.normal(0.5, 0.1, (self.z_dim,)).astype(np.float32)
        self._state = np.clip(self._state, -2.0, 2.0)
        self._prev_state = None
        self._step_count = 0
        self._episode_coherences = []

        info = {"coherence": self._compute_coherence(self._state)}
        return self._state.copy(), info

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Apply action + physics, return (obs, reward, terminated, truncated, info)."""
        assert self._state is not None, "Call reset() before step()"
        self._step_count += 1
        self._prev_state = self._state.copy()

        # 1. Apply agent action (scaled delta)
        delta = action.astype(np.float32) * self.action_scale
        self._state = self._state + delta

        # 2. Apply physics
        if self.use_hamiltonian:
            self._state = self._apply_hamiltonian(self._state)
        else:
            # Simple jitter
            jitter = np.sin(self._state * 0.01) * 0.001
            self._state = self._state + jitter

        # 3. Clamp and ensure correct dtype
        self._state = np.clip(self._state, -2.0, 2.0).astype(np.float32)

        # 4. Compute reward
        coherence = self._compute_coherence(self._state)
        self._episode_coherences.append(coherence)

        reward = self._compute_reward(coherence)

        # 5. Check termination
        terminated = False
        truncated = self._step_count >= self.max_steps

        info = {
            "coherence": coherence,
            "step": self._step_count,
            "mean_episode_coherence": np.mean(self._episode_coherences),
        }

        return self._state.copy(), reward, terminated, truncated, info

    def _apply_hamiltonian(self, z: np.ndarray) -> np.ndarray:
        """Apply double-well Hamiltonian dynamics centered at 0.5.

        V(x) = (x - 0.5)^2 * (x - 0.5 - 0.3)^2 + (x - 0.5 + 0.3)^2
        Simplified to: grad = 4 * (x-0.5) * ((x-0.5)^2 - 0.09)

        This creates energy minima at x=0.5, with barriers at 0.2 and 0.8.
        """
        x = z - 0.5  # Center at origin for cleaner math
        grad = 4.0 * x * (x * x - 0.09)
        noise = self.np_random.normal(0, 1, z.shape).astype(np.float32)
        noise_scale = np.sqrt(2 * self.temperature * self.dt)

        z_new = z - self.dt * grad + noise_scale * noise
        return z_new

    def _compute_coherence(self, z: np.ndarray) -> float:
        """Compute HIHO coherence: 1.0 at mean=0.5, decays with variance."""
        n_chunks = min(12, self.z_dim)
        chunk_size = self.z_dim // n_chunks
        variance_sum = 0.0

        for c in range(n_chunks):
            start = c * chunk_size
            end = (c + 1) * chunk_size if c < n_chunks - 1 else self.z_dim
            chunk_mean = float(np.mean(z[start:end]))
            variance_sum += (chunk_mean - 0.5) ** 2

        variance = variance_sum / n_chunks
        coherence = max(0.0, 1.0 - min(variance * 4.0, 1.0))
        return coherence

    def _compute_reward(self, coherence: float) -> float:
        """Compute reward using CompositeReward or legacy logic."""
        if self._reward_fn is not None:
            return self._reward_fn(
                coherence=coherence,
                state=self._state,
                prev_state=self._prev_state,
            )

        # Legacy reward: bonus for coherence in [0.3, 0.7], penalty outside
        reward = coherence
        if 0.3 <= coherence <= 0.7:
            reward += 0.5
        if coherence < 0.1:
            reward -= 1.0
        return reward

    def render(self) -> str | None:
        """Render current state."""
        if self._state is None:
            return None

        coherence = self._compute_coherence(self._state)
        mean_val = float(np.mean(self._state))
        std_val = float(np.std(self._state))

        text = (
            f"Step {self._step_count}/{self.max_steps} | "
            f"Coherence: {coherence:.3f} | "
            f"Mean: {mean_val:.3f} | Std: {std_val:.3f}"
        )

        if self.render_mode == "human":
            print(text)
        return text


# Register the environment
gym.register(
    id="cohezion/FlumeNav-v0",
    entry_point="cohezion.rl.environment:FlumeNavEnv",
    max_episode_steps=200,
)
