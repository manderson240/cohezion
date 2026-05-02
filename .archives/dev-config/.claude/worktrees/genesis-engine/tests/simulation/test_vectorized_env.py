"""Tests for the Vectorized Environment and Curriculum Scheduler."""

import numpy as np

from cohezion.simulation.rl_framework import NUM_ACTIONS, STATE_DIM
from cohezion.simulation.vectorized_env import (
    CurriculumConfig,
    CurriculumScheduler,
    ScheduleType,
    VectorizedHihoEnv,
)


# ---------------------------------------------------------------------------
# VectorizedHihoEnv tests
# ---------------------------------------------------------------------------


class TestVectorizedHihoEnv:
    def test_creation(self):
        env = VectorizedHihoEnv(num_envs=4, grid_size=32, max_steps=100)
        assert env.num_envs == 4
        assert env.observation_shape == (STATE_DIM,)
        assert env.num_actions == NUM_ACTIONS

    def test_reset_shape(self):
        env = VectorizedHihoEnv(num_envs=4)
        obs = env.reset()
        assert obs.shape == (4, STATE_DIM)
        assert not np.any(np.isnan(obs))

    def test_step_shape(self):
        env = VectorizedHihoEnv(num_envs=4, max_steps=100)
        env.reset()
        actions = np.array([0, 1, 2, 3])
        obs, rewards, dones, infos = env.step(actions)

        assert obs.shape == (4, STATE_DIM)
        assert rewards.shape == (4,)
        assert dones.shape == (4,)
        assert len(infos) == 4

    def test_step_rewards_bounded(self):
        env = VectorizedHihoEnv(num_envs=8, max_steps=100)
        env.reset()

        for _ in range(10):
            actions = np.random.randint(0, NUM_ACTIONS, size=8)
            _, rewards, _, _ = env.step(actions)
            # Rewards should be finite
            assert np.all(np.isfinite(rewards))

    def test_auto_reset_on_done(self):
        env = VectorizedHihoEnv(num_envs=2, max_steps=5)
        env.reset()

        # Step until at least one environment terminates
        for _ in range(10):
            actions = np.array([0, 0])
            obs, _, dones, infos = env.step(actions)

            if np.any(dones):
                # After auto-reset, obs should be valid (not NaN)
                for i in range(2):
                    if dones[i]:
                        assert not np.any(np.isnan(obs[i]))
                        assert "episode_reward" in infos[i]
                break

    def test_episode_stats_tracking(self):
        env = VectorizedHihoEnv(num_envs=2, max_steps=10)
        env.reset()

        for _ in range(20):
            actions = np.random.randint(0, NUM_ACTIONS, size=2)
            env.step(actions)

        stats = env.get_episode_stats()
        assert "episode_counts" in stats
        assert "total_episodes" in stats
        assert stats["total_episodes"] >= 0

    def test_different_seeds(self):
        env1 = VectorizedHihoEnv(num_envs=2, base_seed=42)
        env2 = VectorizedHihoEnv(num_envs=2, base_seed=99)
        obs1 = env1.reset()
        obs2 = env2.reset()
        # Different seeds should produce different initial states
        assert not np.allclose(obs1, obs2)

    def test_reproducibility_same_seed(self):
        env1 = VectorizedHihoEnv(num_envs=2, base_seed=42)
        env2 = VectorizedHihoEnv(num_envs=2, base_seed=42)
        obs1 = env1.reset()
        obs2 = env2.reset()
        np.testing.assert_array_equal(obs1, obs2)


# ---------------------------------------------------------------------------
# CurriculumScheduler tests
# ---------------------------------------------------------------------------


class TestCurriculumScheduler:
    def test_initial_difficulty(self):
        config = CurriculumConfig(initial_difficulty=0.2)
        scheduler = CurriculumScheduler(config)
        assert scheduler.current_difficulty == 0.2

    def test_warmup_phase_no_change(self):
        config = CurriculumConfig(
            initial_difficulty=0.1,
            warmup_episodes=10,
            schedule_type=ScheduleType.ADAPTIVE,
        )
        scheduler = CurriculumScheduler(config)

        for _ in range(9):
            scheduler.record_episode(reward=10.0, success=True)

        # Still in warmup, difficulty unchanged
        assert scheduler.current_difficulty == 0.1

    def test_adaptive_increases_on_success(self):
        config = CurriculumConfig(
            initial_difficulty=0.1,
            warmup_episodes=5,
            performance_window=10,
            target_success_rate=0.7,
            step_size=0.1,
            schedule_type=ScheduleType.ADAPTIVE,
        )
        scheduler = CurriculumScheduler(config)

        # Warmup
        for _ in range(5):
            scheduler.record_episode(reward=5.0, success=True)

        # 10 successes should trigger difficulty increase
        for _ in range(10):
            scheduler.record_episode(reward=5.0, success=True)

        assert scheduler.current_difficulty > 0.1

    def test_adaptive_decreases_on_failure(self):
        config = CurriculumConfig(
            initial_difficulty=0.1,
            max_difficulty=1.0,
            warmup_episodes=5,
            performance_window=10,
            step_size=0.2,
            schedule_type=ScheduleType.ADAPTIVE,
            target_success_rate=0.7,
        )
        scheduler = CurriculumScheduler(config)

        # First push difficulty up via successes
        for _ in range(5):
            scheduler.record_episode(reward=10.0, success=True)
        for _ in range(15):
            scheduler.record_episode(reward=10.0, success=True)

        high_diff = scheduler.current_difficulty
        assert high_diff > 0.1  # Should have increased

        # Now sustained failures should decrease difficulty
        for _ in range(20):
            scheduler.record_episode(reward=0.0, success=False)

        assert scheduler.current_difficulty < high_diff

    def test_linear_schedule(self):
        config = CurriculumConfig(
            initial_difficulty=0.0,
            max_difficulty=1.0,
            warmup_episodes=0,
            schedule_type=ScheduleType.LINEAR,
        )
        scheduler = CurriculumScheduler(config)

        for _ in range(500):
            scheduler.record_episode(reward=1.0, success=True)

        # Should have progressed partway
        assert 0.0 < scheduler.current_difficulty <= 1.0

    def test_step_schedule(self):
        config = CurriculumConfig(
            initial_difficulty=0.0,
            max_difficulty=1.0,
            warmup_episodes=0,
            step_size=0.2,
            schedule_type=ScheduleType.STEP,
        )
        scheduler = CurriculumScheduler(config)

        for _ in range(100):
            scheduler.record_episode(reward=1.0, success=True)

        # Should have increased by step_size
        assert scheduler.current_difficulty >= 0.2

    def test_max_difficulty_cap(self):
        config = CurriculumConfig(
            initial_difficulty=0.9,
            max_difficulty=1.0,
            warmup_episodes=0,
            step_size=0.5,
            schedule_type=ScheduleType.ADAPTIVE,
            performance_window=5,
            target_success_rate=0.5,
        )
        scheduler = CurriculumScheduler(config)

        for _ in range(100):
            scheduler.record_episode(reward=10.0, success=True)

        assert scheduler.current_difficulty <= 1.0

    def test_get_env_params(self):
        scheduler = CurriculumScheduler(CurriculumConfig(initial_difficulty=0.5))
        params = scheduler.get_env_params()

        assert "grid_size" in params
        assert "max_steps" in params
        assert "noise_scale" in params
        assert "energy_drain" in params
        assert "hiho_tolerance" in params
        assert params["grid_size"] >= 32

    def test_stats(self):
        scheduler = CurriculumScheduler()
        for i in range(10):
            scheduler.record_episode(reward=float(i), success=i > 5)

        stats = scheduler.get_stats()
        assert "current_difficulty" in stats
        assert "episode_count" in stats
        assert stats["episode_count"] == 10
