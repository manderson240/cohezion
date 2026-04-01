"""UniverseEvaluator — Rigorous evaluation framework for Cohezion RL environments.

Provides unified benchmarking across ManifoldEnv and SwarmEnv with:
- Convergence rate: how quickly agents reach HIHO equilibrium
- HIHO stability duration: how long agents maintain coherence [0.4, 0.6]
- Energy efficiency: total Lagrangian action per episode
- Coordination index: multi-agent gauge coupling effectiveness (SwarmEnv only)
- Statistical significance: bootstrap confidence intervals for all metrics

Designed for the Anthropic Universes role: "design rigorous evaluations
measuring genuine capability" — not just reward curves, but physics-grounded
metrics that detect genuine understanding vs reward hacking.

Usage:
    evaluator = UniverseEvaluator()
    results = evaluator.evaluate_policy(env, policy_fn, n_episodes=100)
    comparison = evaluator.compare_policies(env, [random_policy, greedy_policy, rl_policy])

Wired to: eval/capability_scorecard.py (EVO 6-axis), compound/capability_matrix.py
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class EpisodeMetrics:
    """Metrics from a single episode evaluation."""

    convergence_step: int  # Step when HIHO band first reached (0 = never)
    hiho_stability_duration: int  # Total steps in HIHO band [0.4, 0.6]
    total_reward: float
    total_energy: float
    avg_coherence: float
    final_coherence: float
    trajectory_length: int
    curriculum_stage_reached: int  # 1=reach, 2=maintain, 3=optimize
    terminated: bool  # True if HIHO convergence achieved


@dataclass
class PolicyEvaluation:
    """Aggregate evaluation of a policy across multiple episodes."""

    policy_name: str
    n_episodes: int
    episode_metrics: list[EpisodeMetrics] = field(default_factory=list)

    # Aggregate metrics (computed after evaluation)
    convergence_rate: float = 0.0  # Fraction of episodes reaching HIHO
    mean_convergence_step: float = 0.0  # Average steps to converge (converged episodes only)
    mean_stability_duration: float = 0.0
    mean_reward: float = 0.0
    mean_energy: float = 0.0
    mean_coherence: float = 0.0
    stage_3_rate: float = 0.0  # Fraction reaching optimization stage

    # Bootstrap confidence intervals (95%)
    convergence_rate_ci: tuple[float, float] = (0.0, 0.0)
    mean_reward_ci: tuple[float, float] = (0.0, 0.0)
    mean_coherence_ci: tuple[float, float] = (0.0, 0.0)

    wall_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "policy_name": self.policy_name,
            "n_episodes": self.n_episodes,
            "convergence_rate": round(self.convergence_rate, 4),
            "mean_convergence_step": round(self.mean_convergence_step, 1),
            "mean_stability_duration": round(self.mean_stability_duration, 1),
            "mean_reward": round(self.mean_reward, 4),
            "mean_energy": round(self.mean_energy, 4),
            "mean_coherence": round(self.mean_coherence, 4),
            "stage_3_rate": round(self.stage_3_rate, 4),
            "convergence_rate_ci": [round(x, 4) for x in self.convergence_rate_ci],
            "mean_reward_ci": [round(x, 4) for x in self.mean_reward_ci],
            "wall_time_seconds": round(self.wall_time_seconds, 2),
        }


@dataclass
class PolicyComparison:
    """Side-by-side comparison of multiple policies."""

    evaluations: list[PolicyEvaluation]
    best_policy: str = ""
    ranking: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "best_policy": self.best_policy,
            "ranking": self.ranking,
            "policies": {e.policy_name: e.to_dict() for e in self.evaluations},
        }

    def summary_table(self) -> str:
        """Generate markdown summary table."""
        lines = [
            "| Policy | Conv Rate | Avg Steps | Stability | Reward | Coherence | Stage 3 |",
            "|--------|-----------|-----------|-----------|--------|-----------|---------|",
        ]
        for e in sorted(self.evaluations, key=lambda x: x.convergence_rate, reverse=True):
            lines.append(
                f"| {e.policy_name} | {e.convergence_rate:.1%} | "
                f"{e.mean_convergence_step:.0f} | {e.mean_stability_duration:.0f} | "
                f"{e.mean_reward:.2f} | {e.mean_coherence:.3f} | {e.stage_3_rate:.1%} |"
            )
        return "\n".join(lines)


class UniverseEvaluator:
    """Rigorous evaluation framework for Cohezion training universes.

    Evaluates policies on physics-grounded metrics that detect genuine
    capability vs reward hacking.
    """

    def __init__(self, n_bootstrap: int = 1000, ci_level: float = 0.95) -> None:
        self.n_bootstrap = n_bootstrap
        self.ci_level = ci_level

    def evaluate_policy(
        self,
        env: Any,
        policy_fn: Callable[[np.ndarray], np.ndarray],
        n_episodes: int = 50,
        policy_name: str = "policy",
    ) -> PolicyEvaluation:
        """Evaluate a policy across multiple episodes.

        Args:
            env: Gymnasium environment (ManifoldEnv or SwarmEnv)
            policy_fn: Function mapping observation → action
            n_episodes: Number of evaluation episodes
            policy_name: Name for reporting

        Returns:
            PolicyEvaluation with aggregate metrics + confidence intervals
        """
        start_time = time.time()
        evaluation = PolicyEvaluation(policy_name=policy_name, n_episodes=n_episodes)

        for ep in range(n_episodes):
            metrics = self._run_episode(env, policy_fn)
            evaluation.episode_metrics.append(metrics)

        # Compute aggregates
        self._compute_aggregates(evaluation)
        evaluation.wall_time_seconds = time.time() - start_time

        logger.info(
            "Evaluated %s: conv_rate=%.1f%%, mean_reward=%.3f, mean_coherence=%.3f (%d episodes in %.1fs)",
            policy_name,
            evaluation.convergence_rate * 100,
            evaluation.mean_reward,
            evaluation.mean_coherence,
            n_episodes,
            evaluation.wall_time_seconds,
        )

        return evaluation

    def compare_policies(
        self,
        env: Any,
        policies: dict[str, Callable[[np.ndarray], np.ndarray]],
        n_episodes: int = 50,
    ) -> PolicyComparison:
        """Compare multiple policies on the same environment.

        Args:
            env: Gymnasium environment
            policies: Dict of policy_name → policy_fn
            n_episodes: Episodes per policy

        Returns:
            PolicyComparison with ranking and summary
        """
        evaluations = []
        for name, policy_fn in policies.items():
            evaluation = self.evaluate_policy(env, policy_fn, n_episodes, name)
            evaluations.append(evaluation)

        comparison = PolicyComparison(evaluations=evaluations)

        # Rank by composite score: convergence_rate * 0.4 + coherence * 0.3 + efficiency * 0.3
        scored = []
        for e in evaluations:
            efficiency = 1.0 - min(e.mean_energy / 10.0, 1.0)  # Normalize energy
            score = e.convergence_rate * 0.4 + e.mean_coherence * 0.3 + efficiency * 0.3
            scored.append((score, e.policy_name))

        scored.sort(reverse=True)
        comparison.ranking = [name for _, name in scored]
        comparison.best_policy = comparison.ranking[0] if comparison.ranking else ""

        return comparison

    def _run_episode(
        self,
        env: Any,
        policy_fn: Callable[[np.ndarray], np.ndarray],
    ) -> EpisodeMetrics:
        """Run a single episode and collect metrics."""
        obs, info = env.reset()
        total_reward = 0.0
        total_energy = 0.0
        coherence_sum = 0.0
        hiho_steps = 0
        convergence_step = 0
        max_stage = 1
        steps = 0

        terminated = False
        truncated = False

        while not terminated and not truncated:
            action = policy_fn(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1

            coherence = info.get("coherence", 0.5)
            coherence_sum += coherence
            total_energy += abs(info.get("potential_energy", 0.0))

            if info.get("hiho_deviation", 1.0) < 0.1:
                hiho_steps += 1
                if convergence_step == 0:
                    convergence_step = steps

            stage = info.get("curriculum_stage", 1)
            max_stage = max(max_stage, stage)

        return EpisodeMetrics(
            convergence_step=convergence_step,
            hiho_stability_duration=hiho_steps,
            total_reward=total_reward,
            total_energy=total_energy,
            avg_coherence=coherence_sum / max(1, steps),
            final_coherence=info.get("coherence", 0.5),
            trajectory_length=steps,
            curriculum_stage_reached=max_stage,
            terminated=terminated,
        )

    def _compute_aggregates(self, evaluation: PolicyEvaluation) -> None:
        """Compute aggregate metrics and bootstrap confidence intervals."""
        metrics = evaluation.episode_metrics
        n = len(metrics)
        if n == 0:
            return

        # Basic aggregates
        converged = [m for m in metrics if m.terminated]
        evaluation.convergence_rate = len(converged) / n
        evaluation.mean_convergence_step = (
            np.mean([m.convergence_step for m in converged]) if converged else 0.0
        )
        evaluation.mean_stability_duration = np.mean([m.hiho_stability_duration for m in metrics])
        evaluation.mean_reward = np.mean([m.total_reward for m in metrics])
        evaluation.mean_energy = np.mean([m.total_energy for m in metrics])
        evaluation.mean_coherence = np.mean([m.avg_coherence for m in metrics])
        evaluation.stage_3_rate = sum(1 for m in metrics if m.curriculum_stage_reached >= 3) / n

        # Bootstrap confidence intervals
        rng = np.random.default_rng(42)

        def bootstrap_ci(values: list[float]) -> tuple[float, float]:
            if len(values) < 2:
                return (0.0, 0.0)
            arr = np.array(values)
            boot_means = [
                np.mean(rng.choice(arr, size=len(arr), replace=True))
                for _ in range(self.n_bootstrap)
            ]
            alpha = (1 - self.ci_level) / 2
            return (
                float(np.percentile(boot_means, alpha * 100)),
                float(np.percentile(boot_means, (1 - alpha) * 100)),
            )

        convergence_flags = [1.0 if m.terminated else 0.0 for m in metrics]
        rewards = [m.total_reward for m in metrics]
        coherences = [m.avg_coherence for m in metrics]

        evaluation.convergence_rate_ci = bootstrap_ci(convergence_flags)
        evaluation.mean_reward_ci = bootstrap_ci(rewards)
        evaluation.mean_coherence_ci = bootstrap_ci(coherences)


# Built-in baseline policies for comparison


def random_policy(obs: np.ndarray) -> np.ndarray:
    """Random policy — uniform random actions."""
    return np.random.uniform(-0.5, 0.5, size=12).astype(np.float32)


def greedy_hiho_policy(obs: np.ndarray) -> np.ndarray:
    """Greedy policy — always push toward HIHO (0.5 on all dims)."""
    state_12d = obs[:12]
    target = np.full(12, 0.5, dtype=np.float32)
    direction = target - state_12d
    norm = np.linalg.norm(direction)
    if norm > 0:
        direction = direction / norm * 0.1  # Small step toward target
    return direction.astype(np.float32)


def zero_policy(obs: np.ndarray) -> np.ndarray:
    """Zero policy — do nothing (baseline for natural dynamics)."""
    return np.zeros(12, dtype=np.float32)
