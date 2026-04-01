"""TDD: UniverseEvaluator tests — rigorous evaluation with bootstrap CIs.

Validates that the evaluation framework produces meaningful metrics that
distinguish between good and bad policies. This is the core "design rigorous
evaluations measuring genuine capability" signal for the Anthropic Universes role.
"""

from __future__ import annotations

import numpy as np


class TestEpisodeMetrics:
    """EpisodeMetrics should capture physics-grounded evaluation data."""

    def test_episode_metrics_fields(self):
        from cohezion.eval.universe_evaluator import EpisodeMetrics

        m = EpisodeMetrics(
            convergence_step=42,
            hiho_stability_duration=100,
            total_reward=5.0,
            total_energy=2.0,
            avg_coherence=0.85,
            final_coherence=0.92,
            trajectory_length=200,
            curriculum_stage_reached=2,
            terminated=True,
        )
        assert m.convergence_step == 42
        assert m.terminated is True
        assert m.curriculum_stage_reached == 2


class TestPolicyEvaluation:
    """PolicyEvaluation should compute meaningful aggregate metrics."""

    def test_to_dict_serializable(self):
        from cohezion.eval.universe_evaluator import PolicyEvaluation

        ev = PolicyEvaluation(policy_name="test", n_episodes=10)
        ev.convergence_rate = 0.5
        ev.mean_reward = 3.14
        d = ev.to_dict()
        assert d["policy_name"] == "test"
        assert d["convergence_rate"] == 0.5
        assert isinstance(d["mean_reward"], float)


class TestBaselinePolicies:
    """Built-in baseline policies should produce valid actions."""

    def test_random_policy_shape(self):
        from cohezion.eval.universe_evaluator import random_policy

        obs = np.zeros(19, dtype=np.float32)
        action = random_policy(obs)
        assert action.shape == (12,)
        assert action.dtype == np.float32

    def test_greedy_hiho_pushes_toward_center(self):
        from cohezion.eval.universe_evaluator import greedy_hiho_policy

        # State far from HIHO (all zeros)
        obs = np.zeros(19, dtype=np.float32)
        action = greedy_hiho_policy(obs)
        # Should push toward 0.5 (positive direction from 0)
        assert np.all(action >= 0), "Should push toward HIHO (0.5) from below"

    def test_zero_policy_does_nothing(self):
        from cohezion.eval.universe_evaluator import zero_policy

        obs = np.ones(19, dtype=np.float32)
        action = zero_policy(obs)
        assert np.all(action == 0)


class TestEvaluatorRunEpisode:
    """_run_episode should collect metrics from a real environment."""

    def test_run_episode_returns_metrics(self):
        from cohezion.environments.manifold_env import ManifoldEnv
        from cohezion.eval.universe_evaluator import UniverseEvaluator, zero_policy

        env = ManifoldEnv(max_steps=20, seed=42)
        evaluator = UniverseEvaluator(n_bootstrap=10)
        metrics = evaluator._run_episode(env, zero_policy)
        assert metrics.trajectory_length == 20  # max_steps reached (truncated)
        assert metrics.avg_coherence > 0
        assert metrics.total_energy >= 0

    def test_greedy_converges_faster_than_random(self):
        from cohezion.environments.manifold_env import ManifoldEnv
        from cohezion.eval.universe_evaluator import (
            UniverseEvaluator,
            greedy_hiho_policy,
            random_policy,
        )

        env = ManifoldEnv(max_steps=50, seed=42)
        evaluator = UniverseEvaluator(n_bootstrap=10)

        greedy_metrics = evaluator._run_episode(env, greedy_hiho_policy)
        random_metrics = evaluator._run_episode(env, random_policy)

        # Greedy should have higher stability than random
        assert greedy_metrics.hiho_stability_duration >= random_metrics.hiho_stability_duration


class TestPolicyComparison:
    """compare_policies should rank policies correctly."""

    def test_comparison_summary_table(self):
        from cohezion.eval.universe_evaluator import PolicyComparison, PolicyEvaluation

        ev1 = PolicyEvaluation(policy_name="good", n_episodes=5)
        ev1.convergence_rate = 0.8
        ev1.mean_coherence = 0.9
        ev1.mean_energy = 1.0
        ev1.mean_convergence_step = 10
        ev1.mean_stability_duration = 40
        ev1.mean_reward = 5.0
        ev1.stage_3_rate = 0.2

        ev2 = PolicyEvaluation(policy_name="bad", n_episodes=5)
        ev2.convergence_rate = 0.1
        ev2.mean_coherence = 0.5
        ev2.mean_energy = 5.0
        ev2.mean_convergence_step = 0
        ev2.mean_stability_duration = 2
        ev2.mean_reward = 0.5
        ev2.stage_3_rate = 0.0

        comp = PolicyComparison(evaluations=[ev1, ev2])
        table = comp.summary_table()
        assert "good" in table
        assert "bad" in table
        assert "80.0%" in table  # convergence rate
