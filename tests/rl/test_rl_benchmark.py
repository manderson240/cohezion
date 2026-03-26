"""Tests for RL Benchmark Runner — episode collection, capability vector, and composite scoring.

Tests:
1. run(n_episodes=2) returns BenchmarkResult with correct structure
2. run_episode returns dict with required keys
3. _build_capability_vector returns dict with all 6 keys
4. BenchmarkResult has all required fields
"""

from __future__ import annotations

import numpy as np
import pytest


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    @pytest.fixture
    def result_cls(self):
        try:
            from cohezion.rl.benchmark_runner import BenchmarkResult

            return BenchmarkResult
        except ImportError:
            pytest.skip("Benchmark runner not yet implemented")

    def test_creation_with_required_fields(self, result_cls):
        """BenchmarkResult can be created with required fields."""
        result = result_cls(
            episodes_completed=10,
            total_steps=2000,
            mean_reward=150.0,
            mean_coherence=0.55,
            final_coherence=0.6,
            composite_score=0.75,
            capability_vector={
                "coherence_amplitude": 0.8,
                "phase_locking": 0.7,
                "exotic_charge_lifetime": 0.9,
                "orbit_quality": 0.6,
                "triune_balance": 0.75,
                "recovery_basin_radius": 0.65,
            },
            episodes=[],
        )
        assert result.episodes_completed == 10
        assert result.total_steps == 2000
        assert result.mean_reward == 150.0

    def test_capability_vector_has_six_keys(self, result_cls):
        """BenchmarkResult.capability_vector has exactly 6 keys."""
        result = result_cls(
            episodes_completed=1,
            total_steps=100,
            mean_reward=100.0,
            mean_coherence=0.5,
            final_coherence=0.5,
            composite_score=0.5,
            capability_vector={
                "coherence_amplitude": 0.5,
                "phase_locking": 0.5,
                "exotic_charge_lifetime": 0.5,
                "orbit_quality": 0.5,
                "triune_balance": 0.5,
                "recovery_basin_radius": 0.5,
            },
            episodes=[],
        )
        keys = set(result.capability_vector.keys())
        expected = {
            "coherence_amplitude",
            "phase_locking",
            "exotic_charge_lifetime",
            "orbit_quality",
            "triune_balance",
            "recovery_basin_radius",
        }
        assert keys == expected

    def test_all_required_fields_present(self, result_cls):
        """BenchmarkResult has all required fields."""
        result = result_cls(
            episodes_completed=5,
            total_steps=500,
            mean_reward=100.0,
            mean_coherence=0.5,
            final_coherence=0.6,
            composite_score=0.7,
            capability_vector={
                "coherence_amplitude": 0.5,
                "phase_locking": 0.5,
                "exotic_charge_lifetime": 0.5,
                "orbit_quality": 0.5,
                "triune_balance": 0.5,
                "recovery_basin_radius": 0.5,
            },
            episodes=[],
        )
        assert hasattr(result, "episodes_completed")
        assert hasattr(result, "total_steps")
        assert hasattr(result, "mean_reward")
        assert hasattr(result, "mean_coherence")
        assert hasattr(result, "final_coherence")
        assert hasattr(result, "composite_score")
        assert hasattr(result, "capability_vector")
        assert hasattr(result, "episodes")

    def test_episodes_field_is_list(self, result_cls):
        """episodes field is a list."""
        result = result_cls(
            episodes_completed=1,
            total_steps=100,
            mean_reward=100.0,
            mean_coherence=0.5,
            final_coherence=0.5,
            composite_score=0.5,
            capability_vector={
                "coherence_amplitude": 0.5,
                "phase_locking": 0.5,
                "exotic_charge_lifetime": 0.5,
                "orbit_quality": 0.5,
                "triune_balance": 0.5,
                "recovery_basin_radius": 0.5,
            },
            episodes=[],
        )
        assert isinstance(result.episodes, list)

    def test_is_dataclass(self, result_cls):
        """BenchmarkResult is a dataclass."""
        import dataclasses

        assert dataclasses.is_dataclass(result_cls)


class TestRLBenchmarkRunner:
    """Tests for RLBenchmarkRunner class."""

    @pytest.fixture
    def runner_cls(self):
        try:
            from cohezion.rl.benchmark_runner import RLBenchmarkRunner

            return RLBenchmarkRunner
        except ImportError:
            pytest.skip("Benchmark runner not yet implemented")

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")
        return PPOTrainer

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")
        return FlumeNavEnv

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")
        return TaskGenerator

    def test_runner_creation(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """RLBenchmarkRunner initializes with required components."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert runner is not None

    def test_runner_has_ppo_trainer(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """Runner stores the PPO trainer reference."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert hasattr(runner, "ppo_trainer")

    def test_runner_has_env(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """Runner stores the environment reference."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert hasattr(runner, "env")

    def test_runner_has_task_generator(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """Runner stores the task generator reference."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert hasattr(runner, "task_generator")

    def test_run_method_exists(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """RLBenchmarkRunner has a run() method."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert hasattr(runner, "run")
        assert callable(runner.run)

    def test_run_episode_method_exists(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """RLBenchmarkRunner has a run_episode() method."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert hasattr(runner, "run_episode")
        assert callable(runner.run_episode)


class TestRunEpisodes:
    """Tests for run() method returning BenchmarkResult."""

    @pytest.fixture
    def runner_cls(self):
        try:
            from cohezion.rl.benchmark_runner import RLBenchmarkRunner

            return RLBenchmarkRunner
        except ImportError:
            pytest.skip("Benchmark runner not yet implemented")

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")
        return PPOTrainer

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")
        return FlumeNavEnv

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")
        return TaskGenerator

    def test_run_returns_benchmark_result(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run() returns a BenchmarkResult instance."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        result = runner.run(n_episodes=1)
        assert result is not None

    def test_run_two_episodes_completed(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run(n_episodes=2) completes exactly 2 episodes."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        result = runner.run(n_episodes=2, verbose=False)
        assert result.episodes_completed == 2
        assert len(result.episodes) == 2

    def test_run_episode_returns_dict(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run_episode() returns a dict with episode data."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episode_data = runner.run_episode()
        assert isinstance(episode_data, dict)

    def test_run_episode_has_required_keys(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run_episode() dict has required keys."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episode_data = runner.run_episode()
        required_keys = ["episode", "total_reward", "steps", "coherences", "biography"]
        for key in required_keys:
            assert key in episode_data, f"Missing key: {key}"

    def test_run_episode_biography_from_evo(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run_episode() biography comes from emitted EVO."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episode_data = runner.run_episode()
        assert "biography" in episode_data
        assert isinstance(episode_data["biography"], list)

    def test_run_with_task_spec(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run() accepts task_specs parameter."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        spec = gen.sample()
        result = runner.run(n_episodes=1, task_specs=[spec], verbose=False)
        assert result is not None

    def test_run_episode_uses_get_action(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run_episode() uses PPO trainer's get_action for each step."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episode_data = runner.run_episode()
        assert episode_data["steps"] > 0
        assert len(episode_data["coherences"]) == episode_data["steps"]


class TestCapabilityVector:
    """Tests for _build_capability_vector() method."""

    @pytest.fixture
    def runner_cls(self):
        try:
            from cohezion.rl.benchmark_runner import RLBenchmarkRunner

            return RLBenchmarkRunner
        except ImportError:
            pytest.skip("Benchmark runner not yet implemented")

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")
        return PPOTrainer

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")
        return FlumeNavEnv

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")
        return TaskGenerator

    def test_build_capability_vector_method_exists(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """RLBenchmarkRunner has _build_capability_vector() method."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        assert hasattr(runner, "_build_capability_vector")
        assert callable(runner._build_capability_vector)

    def test_capability_vector_returns_six_keys(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector returns dict with exactly 6 keys."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert len(cap_vec) == 6

    def test_capability_vector_has_coherence_amplitude(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector includes coherence_amplitude."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert "coherence_amplitude" in cap_vec

    def test_capability_vector_has_phase_locking(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector includes phase_locking."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert "phase_locking" in cap_vec

    def test_capability_vector_has_exotic_charge_lifetime(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector includes exotic_charge_lifetime."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert "exotic_charge_lifetime" in cap_vec

    def test_capability_vector_has_orbit_quality(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector includes orbit_quality."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert "orbit_quality" in cap_vec

    def test_capability_vector_has_triune_balance(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector includes triune_balance."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert "triune_balance" in cap_vec

    def test_capability_vector_has_recovery_basin_radius(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """_build_capability_vector includes recovery_basin_radius."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        assert "recovery_basin_radius" in cap_vec

    def test_capability_vector_values_in_range(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """Capability vector values are in [0, 1] range."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        episodes = [runner.run_episode() for _ in range(3)]
        cap_vec = runner._build_capability_vector(episodes)
        for key, value in cap_vec.items():
            assert 0.0 <= value <= 1.0, f"{key} = {value} outside [0, 1]"


class TestCompositeScore:
    """Tests for composite score computation."""

    @pytest.fixture
    def runner_cls(self):
        try:
            from cohezion.rl.benchmark_runner import RLBenchmarkRunner

            return RLBenchmarkRunner
        except ImportError:
            pytest.skip("Benchmark runner not yet implemented")

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")
        return PPOTrainer

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")
        return FlumeNavEnv

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")
        return TaskGenerator

    def test_result_has_composite_score(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """BenchmarkResult has composite_score field."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        result = runner.run(n_episodes=2, verbose=False)
        assert hasattr(result, "composite_score")

    def test_composite_score_is_float(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """composite_score is a float."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        result = runner.run(n_episodes=2, verbose=False)
        assert isinstance(result.composite_score, (float, np.floating))

    def test_composite_score_in_range(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """composite_score is in [0, 1] range."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen)
        result = runner.run(n_episodes=2, verbose=False)
        assert 0.0 <= result.composite_score <= 1.0


class TestEVOTrackerIntegration:
    """Tests for EVOTracker integration with benchmark runner."""

    @pytest.fixture
    def runner_cls(self):
        try:
            from cohezion.rl.benchmark_runner import RLBenchmarkRunner
        except ImportError:
            pytest.skip("Benchmark runner not yet implemented")
        return RLBenchmarkRunner

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")
        return PPOTrainer

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")
        return FlumeNavEnv

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")
        return TaskGenerator

    def test_runner_accepts_evo_tracker(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """RLBenchmarkRunner accepts evo_tracker parameter."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        from cohezion.rl.evo import EVOTracker

        tracker = EVOTracker()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen, evo_tracker=tracker)
        assert runner is not None

    def test_runner_with_evo_tracker_stores_it(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """Runner stores the EVOTracker reference."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        from cohezion.rl.evo import EVOTracker

        tracker = EVOTracker()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen, evo_tracker=tracker)
        assert hasattr(runner, "evo_tracker")

    def test_runner_episode_increments_tracker(self, runner_cls, trainer_cls, env_cls, gen_cls):
        """run_episode() emits EVO to tracker if provided."""
        trainer = trainer_cls()
        env = env_cls()
        gen = gen_cls()
        from cohezion.rl.evo import EVOTracker

        tracker = EVOTracker()
        runner = runner_cls(ppo_trainer=trainer, env=env, task_generator=gen, evo_tracker=tracker)
        runner.run_episode()
        assert len(tracker.active_evos) > 0
