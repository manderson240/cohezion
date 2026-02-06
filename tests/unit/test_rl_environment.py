"""Tests for the FLUME RL environment (cohezion.rl.environment)."""

from __future__ import annotations

import gymnasium as gym
import numpy as np
import pytest

from cohezion.rl.environment import FlumeNavEnv


@pytest.fixture
def env():
    import cohezion.rl.environment  # noqa: F401

    e = gym.make("cohezion/FlumeNav-v0")
    yield e
    e.close()


class TestFlumeNavEnv:
    def test_gym_registration(self, env):
        assert env is not None
        assert env.spec.id == "cohezion/FlumeNav-v0"

    def test_observation_space(self, env):
        assert env.observation_space.shape == (256,)
        assert env.observation_space.dtype == np.float32

    def test_action_space(self, env):
        assert env.action_space.shape == (256,)

    def test_reset_returns_valid_obs(self, env):
        obs, info = env.reset(seed=42)
        assert obs.shape == (256,)
        assert obs.dtype == np.float32
        assert env.observation_space.contains(obs)
        assert "coherence" in info

    def test_step_returns_valid(self, env):
        env.reset(seed=42)
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (256,)
        assert obs.dtype == np.float32
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert "coherence" in info

    def test_episode_truncates_at_max_steps(self, env):
        env.reset(seed=42)
        for _ in range(200):
            _, _, terminated, truncated, _ = env.step(env.action_space.sample())
            if terminated or truncated:
                break
        assert truncated is True

    def test_coherence_near_one_at_start(self, env):
        _, info = env.reset(seed=42)
        # Initial state is near 0.5, so coherence should be high
        assert info["coherence"] > 0.8

    def test_render_returns_string(self):
        e = FlumeNavEnv(render_mode="ansi")
        e.reset(seed=42)
        text = e.render()
        assert isinstance(text, str)
        assert "Coherence" in text
        e.close()

    def test_deterministic_reset(self, env):
        obs1, _ = env.reset(seed=42)
        obs2, _ = env.reset(seed=42)
        np.testing.assert_array_equal(obs1, obs2)


class TestRewardShaping:
    def test_coherence_reward_peak(self):
        from cohezion.rl.reward_shaping import CoherenceReward

        cr = CoherenceReward()
        assert cr(0.5) == pytest.approx(1.0)

    def test_coherence_reward_decays(self):
        from cohezion.rl.reward_shaping import CoherenceReward

        cr = CoherenceReward()
        assert cr(0.0) < cr(0.3) < cr(0.5)

    def test_diversity_bonus(self):
        from cohezion.rl.reward_shaping import DiversityBonus

        db = DiversityBonus(min_std=0.05, scale=0.3)
        diverse = np.random.default_rng(42).normal(0.5, 0.2, (256,)).astype(np.float32)
        collapsed = np.full(256, 0.5, dtype=np.float32)
        assert db(diverse) > db(collapsed)

    def test_stability_penalty(self):
        from cohezion.rl.reward_shaping import StabilityPenalty

        sp = StabilityPenalty(threshold=0.5, scale=0.5)
        z1 = np.zeros(256, dtype=np.float32)
        z2_small = np.full(256, 0.001, dtype=np.float32)
        z2_big = np.full(256, 0.1, dtype=np.float32)
        assert sp(z1, z2_small) == 0.0  # Within threshold
        assert sp(z1, z2_big) < 0.0  # Penalty for big jump

    def test_composite_reward(self):
        from cohezion.rl.reward_shaping import CompositeReward

        cr = CompositeReward()
        state = np.random.default_rng(42).normal(0.5, 0.1, (256,)).astype(np.float32)
        reward = cr(coherence=0.5, state=state)
        assert reward > 0  # Good coherence + diverse state
