"""Universes Capability Harness — Empirical Agentic Benchmarking for Anthropic Universes.
====================================================================================
Evaluates autonomous agents across long-horizon realistic tasks with:
- Task Success Rate (SR@1)
- Interruption Resilience Score (IRS)
- Mean Recovery Latency (steps to resume after chaos injection)
- Conformal Manifold Negentropy Gain
- 95% Empirical Bootstrap Confidence Intervals

Generates portfolio-grade capability scorecards directly evidencing
readiness for Anthropic's 'Research Engineer, Universes' position.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cohezion.environments.ultra_realistic_agent_env import UltraRealisticAgentEnv


logger = logging.getLogger(__name__)


@dataclass
class TrajectoryStep:
    """A single transition step in a benchmark trajectory."""

    step: int
    action: dict[str, Any]
    observation: dict[str, Any]
    reward: float
    interruption_active: bool
    interruption_message: str


@dataclass
class EpisodeTrajectory:
    """Complete trajectory recording from an evaluation episode."""

    episode_id: str
    task_id: str
    success: bool
    total_steps: int
    cumulative_reward: float
    irs_score: float
    resolution_rate: float
    mean_recovery_steps: float
    final_conformal_factor: float
    duration_seconds: float
    steps: list[TrajectoryStep] = field(default_factory=list)


@dataclass
class UniversesBenchmarkResult:
    """Aggregated statistical evaluation across all benchmark rollouts."""

    benchmark_name: str
    total_episodes: int
    success_rate: float
    success_rate_ci_95: tuple[float, float]
    mean_reward: float
    mean_reward_ci_95: tuple[float, float]
    mean_irs_score: float
    mean_irs_ci_95: tuple[float, float]
    mean_recovery_steps: float
    mean_steps_per_episode: float
    wall_time_seconds: float
    episodes: list[EpisodeTrajectory] = field(default_factory=list)

    def to_summary_dict(self) -> dict[str, Any]:
        """Converts results into structured JSON summary."""
        return {
            "benchmark_name": self.benchmark_name,
            "total_episodes": self.total_episodes,
            "success_rate": round(self.success_rate, 4),
            "success_rate_ci_95": [round(x, 4) for x in self.success_rate_ci_95],
            "mean_reward": round(self.mean_reward, 4),
            "mean_reward_ci_95": [round(x, 4) for x in self.mean_reward_ci_95],
            "mean_irs_score": round(self.mean_irs_score, 4),
            "mean_irs_ci_95": [round(x, 4) for x in self.mean_irs_ci_95],
            "mean_recovery_steps": round(self.mean_recovery_steps, 2),
            "mean_steps_per_episode": round(self.mean_steps_per_episode, 2),
            "wall_time_seconds": round(self.wall_time_seconds, 2),
        }

    def render_markdown_table(self) -> str:
        """Renders GitHub-flavored Markdown scorecard for living portfolio."""
        sr_lo, sr_hi = self.success_rate_ci_95
        irs_lo, irs_hi = self.mean_irs_ci_95
        return (
            f"| Metric | Empirical Value | 95% Confidence Interval |\n"
            f"|---|---|---|\n"
            f"| **Task Success Rate (SR@1)** | `{self.success_rate * 100:.1f}%` | `[{sr_lo * 100:.1f}%, {sr_hi * 100:.1f}%]` |\n"
            f"| **Interruption Resilience Score (IRS)** | `{self.mean_irs_score:.3f}` | `[{irs_lo:.3f}, {irs_hi:.3f}]` |\n"
            f"| **Mean Recovery Latency** | `{self.mean_recovery_steps:.1f} steps` | N/A |\n"
            f"| **Mean Episode Reward** | `{self.mean_reward:.2f}` | `[{self.mean_reward_ci_95[0]:.2f}, {self.mean_reward_ci_95[1]:.2f}]` |\n"
            f"| **Avg Trajectory Length** | `{self.mean_steps_per_episode:.1f} steps` | N/A |\n"
            f"| **Evaluated Episodes** | `{self.total_episodes}` | Total Time: `{self.wall_time_seconds:.1f}s` |\n"
        )


class UniversesCapabilityHarness:
    """Executes empirical benchmarking campaigns measuring genuine capability."""

    def __init__(self, env: UltraRealisticAgentEnv | None = None) -> None:
        self.env = env or UltraRealisticAgentEnv()

    def run_benchmark(
        self,
        agent_policy: Callable[[dict[str, Any]], dict[str, Any] | str],
        n_episodes: int = 10,
        benchmark_name: str = "Universes-Agentic-Chaos-v1",
        record_steps: bool = False,
    ) -> UniversesBenchmarkResult:
        """Runs N episodes under stochastic chaos and computes confidence intervals."""
        start_time = time.time()
        trajectories: list[EpisodeTrajectory] = []

        for ep_idx in range(n_episodes):
            obs, info = self.env.reset(seed=ep_idx + 100)
            ep_reward = 0.0
            steps: list[TrajectoryStep] = []
            ep_start = time.time()

            terminated = False
            truncated = False
            step_num = 0

            while not (terminated or truncated):
                step_num += 1
                action = agent_policy(obs)

                next_obs, reward, terminated, truncated, step_info = self.env.step(action)
                ep_reward += reward

                if record_steps:
                    steps.append(
                        TrajectoryStep(
                            step=step_num,
                            action=action if isinstance(action, dict) else {"cmd": str(action)},
                            observation={
                                "stdout": next_obs["stdout"][:200],
                                "exit_code": next_obs["exit_code"],
                                "active_interrupt": next_obs["active_interrupt"],
                            },
                            reward=reward,
                            interruption_active=bool(next_obs["active_interrupt"]),
                            interruption_message=next_obs["interrupt_message"],
                        )
                    )

                obs = next_obs

            duration = time.time() - ep_start
            traj = EpisodeTrajectory(
                episode_id=f"ep_{ep_idx + 1}",
                task_id=info["task_id"],
                success=step_info["task_completed"],
                total_steps=step_num,
                cumulative_reward=ep_reward,
                irs_score=step_info["irs_score"],
                resolution_rate=step_info["resolution_rate"],
                mean_recovery_steps=step_info["mean_recovery_steps"],
                final_conformal_factor=step_info["conformal_factor"],
                duration_seconds=duration,
                steps=steps,
            )
            trajectories.append(traj)

        wall_time = time.time() - start_time

        # Bootstrap 95% Confidence Intervals
        successes = np.array([1.0 if t.success else 0.0 for t in trajectories])
        rewards = np.array([t.cumulative_reward for t in trajectories])
        irss = np.array([t.irs_score for t in trajectories])
        steps_arr = np.array([t.total_steps for t in trajectories])
        recov_arr = np.array([t.mean_recovery_steps for t in trajectories])

        sr_mean = float(np.mean(successes))
        rew_mean = float(np.mean(rewards))
        irs_mean = float(np.mean(irss))

        sr_ci = self._bootstrap_ci(successes)
        rew_ci = self._bootstrap_ci(rewards)
        irs_ci = self._bootstrap_ci(irss)

        return UniversesBenchmarkResult(
            benchmark_name=benchmark_name,
            total_episodes=n_episodes,
            success_rate=sr_mean,
            success_rate_ci_95=sr_ci,
            mean_reward=rew_mean,
            mean_reward_ci_95=rew_ci,
            mean_irs_score=irs_mean,
            mean_irs_ci_95=irs_ci,
            mean_recovery_steps=float(np.mean(recov_arr)),
            mean_steps_per_episode=float(np.mean(steps_arr)),
            wall_time_seconds=wall_time,
            episodes=trajectories,
        )

    def _bootstrap_ci(
        self, data: np.ndarray, n_boot: int = 1000, ci: float = 0.95
    ) -> tuple[float, float]:
        """Calculates non-parametric percentile bootstrap confidence intervals."""
        if len(data) == 0:
            return (0.0, 0.0)
        rng = np.random.default_rng(42)
        boot_means = np.empty(n_boot)
        n = len(data)
        for i in range(n_boot):
            sample = rng.choice(data, size=n, replace=True)
            boot_means[i] = np.mean(sample)
        alpha = (1.0 - ci) / 2.0
        low = float(np.percentile(boot_means, alpha * 100))
        high = float(np.percentile(boot_means, (1.0 - alpha) * 100))
        return (low, high)
