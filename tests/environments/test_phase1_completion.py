"""TDD: Phase 1 completion tests — observation normalization, SwarmEnv polish,
PPO compatibility, and evaluation API readiness.

These tests validate production-readiness for the Anthropic Universes portfolio.
"""

from __future__ import annotations

import numpy as np
import pytest


# --- Phase 1A: ManifoldEnv observation normalization ---


class TestManifoldEnvNormalization:
    """ManifoldEnv should work with gymnasium normalization wrappers."""

    def test_observation_space_bounded(self):
        """Observation space must have finite bounds for normalization."""
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(seed=42)
        assert np.all(np.isfinite(env.observation_space.low))
        assert np.all(np.isfinite(env.observation_space.high))

    def test_observations_within_bounds(self):
        """All observations should be within declared bounds."""
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(seed=42, max_steps=50)
        obs, _ = env.reset()
        assert env.observation_space.contains(obs), f"Reset obs out of bounds: {obs}"
        for _ in range(20):
            action = env.action_space.sample()
            obs, _, term, trunc, _ = env.step(action)
            assert env.observation_space.contains(obs), f"Step obs out of bounds: {obs}"
            if term or trunc:
                break

    def test_normalize_observation_wrapper(self):
        """NormalizeObservation wrapper should work without errors."""
        from gymnasium.wrappers import NormalizeObservation

        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(seed=42, max_steps=20)
        wrapped = NormalizeObservation(env)
        obs, _ = wrapped.reset()
        assert obs.shape == (19,)
        for _ in range(10):
            obs, _, term, trunc, _ = wrapped.step(env.action_space.sample())
            assert obs.shape == (19,)
            if term or trunc:
                break


# --- Phase 1A: Curriculum reward correctness ---


class TestCurriculumReward:
    """3-stage curriculum reward should produce correct stage transitions."""

    def test_stage_1_at_start(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(seed=42)
        _, info = env.reset()
        _, _, _, _, info = env.step(env.action_space.sample())
        assert info["curriculum_stage"] == 1

    def test_episode_stats_populated(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(seed=42, max_steps=30)
        env.reset()
        for _ in range(20):
            _, _, term, trunc, info = env.step(env.action_space.sample())
            if term or trunc:
                break
        assert "avg_coherence" in info
        assert "avg_energy" in info
        assert "hiho_time_ratio" in info
        assert "convergence_step" in info
        assert info["avg_coherence"] > 0


# --- Phase 1B: SwarmEnv polish ---


class TestSwarmEnvPolish:
    """SwarmEnv should be production-ready with PettingZoo compliance."""

    def test_instantiation(self):
        from cohezion.environments.swarm_env import SwarmEnv

        env = SwarmEnv(n_agents=4)
        assert len(env.agents) == 4

    def test_reset_returns_correct_shapes(self):
        from cohezion.environments.swarm_env import SwarmEnv

        env = SwarmEnv(n_agents=3)
        obs, info = env.reset()
        assert len(obs) == 3
        for agent_id, agent_obs in obs.items():
            assert agent_obs.shape == (19,)

    def test_step_with_random_actions(self):
        from cohezion.environments.swarm_env import SwarmEnv

        env = SwarmEnv(n_agents=2)
        obs, _ = env.reset()
        actions = {a: np.random.uniform(-0.5, 0.5, 12).astype(np.float32) for a in env.agents}
        obs2, rewards, terms, truncs, infos = env.step(actions)
        assert len(obs2) == 2
        assert len(rewards) == 2
        for r in rewards.values():
            assert isinstance(r, float)

    def test_cooperative_reward_structure(self):
        """Reward should include both individual and collective components."""
        from cohezion.environments.swarm_env import SwarmEnv

        env = SwarmEnv(n_agents=4)
        env.reset()
        actions = {a: np.zeros(12, dtype=np.float32) for a in env.agents}
        _, rewards, _, _, _ = env.step(actions)
        # All agents with same action should get similar rewards
        reward_values = list(rewards.values())
        assert max(reward_values) - min(reward_values) < 1.0

    def test_gymnasium_registry(self):
        """SwarmEnv should be registered with gymnasium."""
        import gymnasium as gym

        # Import triggers registration
        from cohezion.environments import swarm_env as _  # noqa: F401

        spec = gym.spec("Cohezion/SwarmEnv-v0")
        assert spec is not None

    def test_scalability_2_to_8_agents(self):
        """SwarmEnv should work with 2-8 agents."""
        from cohezion.environments.swarm_env import SwarmEnv

        for n in [2, 4, 8]:
            env = SwarmEnv(n_agents=n)
            obs, _ = env.reset()
            assert len(obs) == n
            actions = {a: np.zeros(12, dtype=np.float32) for a in env.agents}
            obs2, _, _, _, _ = env.step(actions)
            assert len(obs2) == n


# --- Phase 1C: UniverseEvaluator integration ---


class TestEvaluatorIntegration:
    """UniverseEvaluator should produce meaningful, distinguishing results."""

    def test_greedy_beats_random_on_stability(self):
        """Greedy HIHO policy should have more stability than random."""
        from cohezion.environments.manifold_env import ManifoldEnv
        from cohezion.eval.universe_evaluator import (
            UniverseEvaluator,
            greedy_hiho_policy,
            random_policy,
        )

        env = ManifoldEnv(max_steps=50, seed=42)
        evaluator = UniverseEvaluator(n_bootstrap=50)
        greedy = evaluator.evaluate_policy(
            env, greedy_hiho_policy, n_episodes=5, policy_name="greedy"
        )
        random_eval = evaluator.evaluate_policy(
            env, random_policy, n_episodes=5, policy_name="random"
        )
        assert greedy.mean_stability_duration >= random_eval.mean_stability_duration

    def test_bootstrap_ci_populated(self):
        """Bootstrap confidence intervals should be computed."""
        from cohezion.environments.manifold_env import ManifoldEnv
        from cohezion.eval.universe_evaluator import UniverseEvaluator, zero_policy

        env = ManifoldEnv(max_steps=20, seed=42)
        evaluator = UniverseEvaluator(n_bootstrap=50)
        result = evaluator.evaluate_policy(env, zero_policy, n_episodes=5, policy_name="zero")
        lo, hi = result.mean_reward_ci
        assert lo <= result.mean_reward <= hi or lo == hi == 0.0
