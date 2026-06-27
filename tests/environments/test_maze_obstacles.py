"""Tests for ManifoldEnv maze-obstacle mode (Task #101)."""

import numpy as np
import pytest

from cohezion.environments.manifold_env import ManifoldEnv


class TestMazeObstacles:
    """Discriminating tests for the maze-obstacle reward penalty."""

    def test_make_maze_creates_obstacle_mode_env(self):
        """T1: make_maze() must return an env with obstacle_mode=True and obstacles set.

        Wrong implementation: obstacle_mode=False (default ctor) — would fail this test.
        """
        env = ManifoldEnv.make_maze()
        assert env.obstacle_mode is True, "make_maze() must set obstacle_mode=True"
        assert len(env.obstacles) > 0, "make_maze() must populate obstacles from MAZE_OBSTACLES"
        assert env.obstacles == ManifoldEnv.MAZE_OBSTACLES, (
            "make_maze() must use ManifoldEnv.MAZE_OBSTACLES as obstacle list"
        )

    def test_step_inside_obstacle_penalises_reward(self):
        """T2: Stepping into an obstacle region must decrease reward by -1.0 vs no-obstacle env.

        Wrong implementation: obstacle penalty always 0 — rewards would be equal.
        This test discriminates the active gate from the no-op.
        """
        # Use a trivially simple obstacle centred at (0.5, 0.5) with large radius
        # so that a default initial position (near 0.5) is guaranteed to be inside.
        big_obstacle = [(0.5, 0.5, 2.0)]  # radius 2.0 covers the whole space

        env_maze = ManifoldEnv(
            seed=42,
            obstacle_mode=True,
            obstacles=big_obstacle,  # type: ignore[arg-type]
        )
        env_plain = ManifoldEnv(seed=42, obstacle_mode=False)

        env_maze.reset(seed=42)
        env_plain.reset(seed=42)

        # Use the same deterministic action for both
        action = np.zeros(12, dtype=np.float32)

        _, reward_maze, _, _, _ = env_maze.step(action)
        _, reward_plain, _, _, _ = env_plain.step(action)

        assert reward_maze < reward_plain, (
            f"Expected maze reward ({reward_maze:.4f}) < plain reward ({reward_plain:.4f}). "
            "Obstacle penalty (-1.0) must reduce the reward when inside an obstacle."
        )
        assert pytest.approx(reward_maze, abs=1e-5) == reward_plain - 1.0, (
            f"Expected penalty of exactly -1.0: maze={reward_maze:.4f}, plain={reward_plain:.4f}."
        )
