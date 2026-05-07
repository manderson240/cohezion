"""Tests for the ARC-AGI-3 gymnasium wrapper."""

import gymnasium as gym
import numpy as np
import pytest

from cohezion.environments.arc_env import ARCEnvironment, MockARCGame


@pytest.fixture
def env():
    e = ARCEnvironment()
    yield e
    e.close()


class TestARCEnvironmentSpaces:
    def test_action_space_is_discrete_8(self, env):
        assert isinstance(env.action_space, gym.spaces.Discrete)
        assert env.action_space.n == 8

    def test_observation_space_shape(self, env):
        assert env.observation_space.shape == (64, 64, 3)
        assert env.observation_space.dtype == np.uint8

    def test_observation_space_bounds(self, env):
        assert env.observation_space.low.min() == 0
        assert env.observation_space.high.max() == 255


class TestARCEnvironmentReset:
    def test_reset_returns_obs_and_info(self, env):
        obs, info = env.reset()
        assert isinstance(obs, np.ndarray)
        assert isinstance(info, dict)

    def test_reset_obs_in_space(self, env):
        obs, _ = env.reset()
        assert env.observation_space.contains(obs)

    def test_reset_info_fields(self, env):
        _, info = env.reset()
        assert info["level"] == 0
        assert info["actions_taken"] == 0
        assert info["won"] is False


class TestARCEnvironmentStep:
    def test_step_returns_five_tuple(self, env):
        env.reset()
        result = env.step(1)
        assert len(result) == 5
        obs, reward, terminated, truncated, info = result
        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)

    def test_step_obs_in_space(self, env):
        env.reset()
        obs, *_ = env.step(1)
        assert env.observation_space.contains(obs)

    def test_step_efficiency_penalty(self, env):
        env.reset()
        _, reward, _, _, _ = env.step(1)
        assert reward == pytest.approx(-0.01, abs=1e-6)

    def test_step_win_reward(self, env):
        """MockARCGame wins after 10 steps — verify +1 reward on win."""
        env.reset()
        for _ in range(9):
            env.step(1)
        _, reward, terminated, _, info = env.step(1)
        assert terminated is True
        assert info["won"] is True
        assert reward == pytest.approx(0.99, abs=1e-6)  # +1.0 - 0.01

    def test_truncation_at_max_steps(self):
        env = ARCEnvironment(max_steps=5)
        env.reset()
        for _ in range(4):
            env.step(1)
        _, _, _terminated, truncated, _ = env.step(1)
        assert truncated is True
        env.close()

    def test_info_tracks_actions(self, env):
        env.reset()
        for i in range(3):
            _, _, _, _, info = env.step(i % 8)
        assert info["actions_taken"] == 3


class TestARCEnvironmentRender:
    def test_render_rgb_array(self):
        env = ARCEnvironment(render_mode="rgb_array")
        env.reset()
        frame = env.render()
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (64, 64, 3)
        env.close()

    def test_render_none_without_mode(self, env):
        env.reset()
        assert env.render() is None


class TestTo12D:
    def test_to_12d_shape(self, env):
        env.reset()
        obs = env._get_obs()
        vec = env.to_12d(obs)
        assert vec.shape == (12,)
        assert vec.dtype == np.float32

    def test_to_12d_finite(self, env):
        env.reset()
        obs = env._get_obs()
        vec = env.to_12d(obs)
        assert np.all(np.isfinite(vec))

    def test_to_12d_varies_with_obs(self, env):
        env.reset()
        v1 = env.to_12d(env._get_obs())
        for _ in range(5):
            env.step(3)
        v2 = env.to_12d(env._get_obs())
        assert not np.array_equal(v1, v2)


class TestMockARCGame:
    def test_full_reset_clears_state(self):
        game = MockARCGame()
        game.perform_action(1)
        game.full_reset()
        assert not game.win
        assert not game.lose

    def test_get_pixels_shape(self):
        game = MockARCGame()
        pixels = game.get_pixels(0, 0, 64, 64)
        assert pixels.shape == (64, 64, 3)
