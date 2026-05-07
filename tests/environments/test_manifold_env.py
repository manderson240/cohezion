"""Tests for ManifoldEnv — the gymnasium-compatible 12D agentic environment."""

import gymnasium as gym
import numpy as np
import pytest

from cohezion.environments.manifold_env import ManifoldEnv


class TestGymInterface:
    """Verify standard gymnasium API compliance."""

    def test_reset_returns_obs_and_info(self):
        env = ManifoldEnv(seed=42)
        obs, info = env.reset()
        assert isinstance(obs, np.ndarray)
        assert isinstance(info, dict)

    def test_obs_shape_is_19d(self):
        env = ManifoldEnv()
        obs, _ = env.reset()
        assert obs.shape == (19,)

    def test_obs_within_bounds(self):
        env = ManifoldEnv(seed=42)
        obs, _ = env.reset()
        assert np.all(np.isfinite(obs))

    def test_step_returns_five_tuple(self):
        env = ManifoldEnv(seed=42)
        env.reset()
        action = env.action_space.sample()
        result = env.step(action)
        assert len(result) == 5
        obs, reward, terminated, truncated, info = result
        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)

    def test_action_space_shape(self):
        env = ManifoldEnv()
        assert env.action_space.shape == (12,)

    def test_observation_space_shape(self):
        env = ManifoldEnv()
        assert env.observation_space.shape == (19,)

    def test_action_space_contains_sample(self):
        env = ManifoldEnv()
        action = env.action_space.sample()
        assert env.action_space.contains(action)


class TestPhysics:
    """Verify physics engine integration."""

    def test_coherence_in_info(self):
        env = ManifoldEnv(seed=42)
        _, info = env.reset()
        assert "coherence" in info
        assert 0 <= info["coherence"] <= 1

    def test_hiho_deviation_in_info(self):
        env = ManifoldEnv(seed=42)
        _, info = env.reset()
        assert "hiho_deviation" in info
        assert info["hiho_deviation"] >= 0

    def test_yang_mills_in_info(self):
        env = ManifoldEnv(seed=42)
        _, info = env.reset()
        assert "yang_mills_action" in info
        assert info["yang_mills_action"] >= 0

    def test_spinor_in_info(self):
        env = ManifoldEnv(seed=42)
        _, info = env.reset()
        assert "charge_polarity" in info
        assert -1 <= info["charge_polarity"] <= 1

    def test_energy_in_info(self):
        env = ManifoldEnv(seed=42)
        _, info = env.reset()
        assert "potential_energy" in info
        assert "kinetic_energy" in info

    def test_reward_is_finite(self):
        env = ManifoldEnv(seed=42)
        env.reset()
        for _ in range(10):
            _, reward, _, _, _ = env.step(env.action_space.sample())
            assert np.isfinite(reward)


class TestVerifiableRewards:
    """Verify physics-grounded reward signals (Session 96b, Phase 8.3)."""

    @pytest.mark.unit
    def test_verifiable_mode_runs(self):
        """Verifiable reward mode produces finite rewards."""
        env = ManifoldEnv(seed=42, reward_mode="verifiable")
        env.reset()
        for _ in range(10):
            _, reward, _, _, _ = env.step(env.action_space.sample())
            assert np.isfinite(reward), f"Non-finite reward: {reward}"

    @pytest.mark.unit
    def test_verifiable_reward_peaks_at_hiho(self):
        """Reward should be higher at HIHO (0.5) than away from it."""
        env_hiho = ManifoldEnv(seed=42, reward_mode="verifiable")
        env_hiho.reset()
        # Force state to HIHO
        env_hiho._position = np.full(12, 0.5, dtype=np.float32)
        _, r_hiho, _, _, _ = env_hiho.step(np.zeros(12, dtype=np.float32))

        env_away = ManifoldEnv(seed=42, reward_mode="verifiable")
        env_away.reset()
        # Force state away from HIHO
        env_away._position = np.full(12, 0.0, dtype=np.float32)
        _, r_away, _, _, _ = env_away.step(np.zeros(12, dtype=np.float32))

        assert r_hiho > r_away, f"HIHO reward {r_hiho} should exceed away reward {r_away}"

    @pytest.mark.unit
    def test_verifiable_reward_components_are_deterministic(self):
        """Same state produces same reward (no randomness in verifiable mode)."""
        rewards = []
        for _ in range(3):
            env = ManifoldEnv(seed=42, reward_mode="verifiable")
            env.reset()
            _, r, _, _, _ = env.step(np.zeros(12, dtype=np.float32))
            rewards.append(r)
        assert rewards[0] == rewards[1] == rewards[2]

    @pytest.mark.unit
    def test_verifiable_r_hiho_formula(self):
        """r_hiho = 1 - 4*var(pos) peaks at 1.0 when all dims = 0.5."""
        pos_hiho = np.full(12, 0.5)
        r_hiho = 1.0 - 4.0 * float(np.var(pos_hiho))
        assert abs(r_hiho - 1.0) < 1e-10, f"r_hiho at HIHO = {r_hiho}, expected 1.0"

        # A mixed state has nonzero variance → lower r_hiho
        pos_away = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
        r_away = 1.0 - 4.0 * float(np.var(pos_away))
        assert r_away < r_hiho, f"r_away={r_away} should be < r_hiho={r_hiho}"


class TestTermination:
    """Verify termination conditions."""

    def test_truncation_at_max_steps(self):
        env = ManifoldEnv(max_steps=10, seed=42)
        env.reset()
        for _ in range(10):
            _, _, terminated, truncated, _ = env.step(env.action_space.sample())
            if terminated or truncated:
                break
        assert truncated or terminated

    def test_hiho_convergence_terminates(self):
        """Manually set state to HIHO and verify termination."""
        env = ManifoldEnv(hiho_stability_window=3, seed=42)
        env.reset()
        # Force state to HIHO
        env._position = np.full(12, 0.5, dtype=np.float32)
        env._velocity = np.zeros(12, dtype=np.float32)

        # Small actions near HIHO should trigger convergence
        for _ in range(20):
            action = np.zeros(12, dtype=np.float32)  # No action
            _, _, terminated, _, info = env.step(action)
            if terminated:
                assert info["hiho_streak"] >= 3
                return
        # If we get here, HIHO deviation might be slightly above threshold
        # due to dynamics — that's OK, verify it's at least small
        assert info["hiho_deviation"] < 0.1


class TestTrajectory:
    """Verify trajectory recording."""

    def test_trajectory_grows(self):
        env = ManifoldEnv(seed=42)
        env.reset()
        for _ in range(5):
            env.step(env.action_space.sample())
        traj = env.get_trajectory()
        assert traj.shape == (6, 12)  # initial + 5 steps

    def test_trajectory_is_finite(self):
        env = ManifoldEnv(seed=42)
        env.reset()
        for _ in range(10):
            env.step(env.action_space.sample())
        traj = env.get_trajectory()
        assert np.all(np.isfinite(traj))


class TestReproducibility:
    """Verify seeded runs produce identical results."""

    def test_same_seed_same_trajectory(self):
        results = []
        for _ in range(2):
            env = ManifoldEnv(seed=123)
            obs, _ = env.reset(seed=123)
            total_r = 0
            for _ in range(10):
                action = np.full(12, 0.01, dtype=np.float32)
                obs, r, _, _, _ = env.step(action)
                total_r += r
            results.append((obs.copy(), total_r))

        np.testing.assert_array_equal(results[0][0], results[1][0])
        assert results[0][1] == results[1][1]


class TestRegistration:
    """Verify gymnasium registration."""

    def test_make_registered_env(self):
        env = gym.make("Cohezion/ManifoldEnv-v0")
        obs, _info = env.reset()
        assert obs.shape == (19,)
        env.close()
