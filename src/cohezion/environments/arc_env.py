"""ARCEnvironment — Gymnasium wrapper for ARC-AGI-3 interactive games.

Wraps the arcengine SDK into a standard Gymnasium interface so that
JEPA world models, SurpriseExplorer, and standard RL algorithms (PPO, SAC)
can interact with ARC-AGI-3 games through a uniform API.

Observation space: Box(0, 255, (64, 64, 3), uint8) — RGB grid
Action space: Discrete(8) — RESET(0) + ACTION1..ACTION7
Reward: +1 on level completion, -0.01 per step (efficiency penalty)
"""

from __future__ import annotations

import logging
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces


logger = logging.getLogger(__name__)


class MockARCGame:
    """Lightweight mock that satisfies the ARCBaseGame protocol for testing.

    Returns deterministic grid patterns so tests can validate the wrapper
    without needing real ARC game assets.
    """

    def __init__(self) -> None:
        self.game_id = "mock-arc"
        self._grid = np.zeros((64, 64, 3), dtype=np.uint8)
        self._level = 0
        self._won = False
        self._lost = False
        self._step_count = 0

    def full_reset(self) -> None:
        self._grid = np.zeros((64, 64, 3), dtype=np.uint8)
        self._level = 0
        self._won = False
        self._lost = False
        self._step_count = 0

    def get_pixels(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        return self._grid[y : y + height, x : x + width].copy()

    def perform_action(self, action_value: int) -> None:
        """Simulate performing an action. Advances step count."""
        self._step_count += 1
        # Paint a simple pattern based on action to make observations vary
        color = min(action_value * 36, 255)
        self._grid[: self._step_count % 64, :, 0] = color
        # Auto-win after 10 steps on first level for testing
        if self._step_count >= 10 and self._level == 0:
            self._won = True

    def next_level(self) -> None:
        self._level += 1
        self._won = False
        self._step_count = 0

    @property
    def win(self) -> bool:
        return self._won

    @property
    def lose(self) -> bool:
        return self._lost


class ARCEnvironment(gym.Env):
    """Gymnasium wrapper for ARC-AGI-3 interactive games.

    Enables:
    - Standard RL training (PPO, SAC) via Stable-Baselines3
    - JEPA world model training (predict next frame from action)
    - Surprise-driven exploration (high JEPA prediction error = novel state)

    Parameters
    ----------
    game : object or None
        An ARCBaseGame instance (or MockARCGame for testing).
        If None, creates a MockARCGame.
    max_steps : int
        Maximum steps before truncation (default: 200).
    render_mode : str or None
        Rendering mode. Only "rgb_array" is supported.
    """

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(
        self,
        game: Any | None = None,
        max_steps: int = 200,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()

        self.game = game if game is not None else MockARCGame()
        self.max_steps = max_steps
        self.render_mode = render_mode

        # 8 discrete actions: RESET(0) + ACTION1..ACTION7
        self.action_space = spaces.Discrete(8)

        # 64x64 RGB grid observation
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=(64, 64, 3),
            dtype=np.uint8,
        )

        self._step_count = 0
        self._total_reward = 0.0
        self._current_level = 0

    def reset(
        self,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Reset game to initial state."""
        super().reset(seed=seed)
        self.game.full_reset()
        self._step_count = 0
        self._total_reward = 0.0
        self._current_level = 0
        return self._get_obs(), self._get_info(won=False)

    def step(
        self,
        action: int,
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Execute one action in the ARC game.

        Returns (observation, reward, terminated, truncated, info).
        """
        action = int(action)
        self._step_count += 1

        # Dispatch action to the game
        self.game.perform_action(action)

        # Check terminal conditions
        won = bool(self.game.win)
        lost = bool(self.game.lose)
        terminated = won or lost
        truncated = self._step_count >= self.max_steps

        # Reward: +1 for win, -1 for loss, -0.01 per step (efficiency)
        reward = -0.01
        if won:
            reward += 1.0
            self._current_level += 1
        elif lost:
            reward -= 1.0

        self._total_reward += reward
        obs = self._get_obs()
        info = self._get_info(won=won)

        return obs, reward, terminated, truncated, info

    def render(self) -> np.ndarray | None:
        """Return RGB array of current game state."""
        if self.render_mode == "rgb_array":
            return self._get_obs()
        return None

    def _get_obs(self) -> np.ndarray:
        """Get 64x64x3 RGB observation from the game grid."""
        pixels = self.game.get_pixels(0, 0, 64, 64)
        obs = np.asarray(pixels, dtype=np.uint8)
        # Ensure correct shape even if game returns differently
        if obs.shape != (64, 64, 3):
            obs = (
                obs.reshape(64, 64, 3)
                if obs.size == 64 * 64 * 3
                else np.zeros(
                    (64, 64, 3),
                    dtype=np.uint8,
                )
            )
        return obs

    def _get_info(self, won: bool) -> dict[str, Any]:
        return {
            "level": self._current_level,
            "actions_taken": self._step_count,
            "won": won,
            "total_reward": self._total_reward,
        }

    def to_12d(self, obs: np.ndarray) -> np.ndarray:
        """Project observation to 12D manifold for JEPA/FLUME encoding.

        Extracts structural features from the 64x64 grid:
        - Grid entropy (information density)
        - Color channel statistics
        - Spatial symmetry measures
        - Pattern complexity via gradient magnitude
        """
        obs_float = obs.astype(np.float32) / 255.0

        # Channel means and stds (6 features)
        channel_means = obs_float.mean(axis=(0, 1))  # 3D
        channel_stds = obs_float.std(axis=(0, 1))  # 3D

        # Spatial gradient magnitude (complexity proxy)
        gray = obs_float.mean(axis=2)
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        grad_mag = float(np.sqrt(dx[:63, :].ravel() ** 2 + dy[:, :63].ravel() ** 2).mean())

        # Horizontal symmetry
        h_sym = float(1.0 - np.abs(gray - gray[:, ::-1]).mean())

        # Vertical symmetry
        v_sym = float(1.0 - np.abs(gray - gray[::-1, :]).mean())

        # Entropy (from grayscale histogram)
        hist, _ = np.histogram(gray, bins=32, range=(0.0, 1.0))
        probs = hist / hist.sum() if hist.sum() > 0 else hist
        probs = probs[probs > 0]
        entropy = float(-np.sum(probs * np.log2(probs))) / 5.0  # normalized

        # Fill density (fraction of non-zero pixels)
        fill = float(np.count_nonzero(gray) / gray.size)

        # Diagonal symmetry
        d_sym = float(1.0 - np.abs(gray - gray.T).mean())

        return np.array(
            [
                *channel_means,
                *channel_stds,
                grad_mag,
                h_sym,
                v_sym,
                entropy,
                fill,
                d_sym,
            ],
            dtype=np.float32,
        )


# Register with gymnasium
gym.register(
    id="Cohezion/ARCEnv-v0",
    entry_point="cohezion.environments.arc_env:ARCEnvironment",
    max_episode_steps=200,
)

__all__ = ["ARCEnvironment", "MockARCGame"]
