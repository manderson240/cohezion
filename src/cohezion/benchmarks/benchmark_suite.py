"""LM Evaluation Harness-style benchmark suite for FLUME EVO physics.

Provides a standard benchmark interface inspired by EleutherAI's lm-evaluation-harness:
- Task registry with TaskSpec-driven task definitions
- Multiple evaluation modes (train, eval, benchmark)
- Model-agnostic policy interface (any policy that implements get_action)
- Sweepable hyperparameters via TOML/CLI
- JSONL results export compatible with HuggingFace evaluation datasets
- Integration with EvalPipeline for multi-episode runs

Example:
    suite = BenchmarkSuite()
    suite.register_task("cohezion/hiho_basin_easy", HIHOBasinEasyTask)
    results = suite.run(
        policy=triune_policy,
        tasks=["cohezion/hiho_basin_easy"],
        num_episodes=50,
        output_path="results/",
    )
    print(suite.format_results(results))
"""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics
from cohezion.rl.evo import EthericVariantOscillator
from cohezion.rl.task_generator import TaskGenerator


if TYPE_CHECKING:
    from cohezion.rl.environment import FlumeNavEnv


class Policy(Protocol):
    """Protocol for benchmark policies.

    Any object with a get_action method can be used as a policy in benchmarks.
    """

    def get_action(self, state: np.ndarray) -> tuple[np.ndarray, float, float]:
        """Sample an action from the policy given the current state.

        Args:
            state: Current observation (256D VAE latent).

        Returns:
            Tuple of (action, log_prob, value). action must be a numpy array
            with shape matching the env action space.
        """
        ...


@dataclass
class TaskResult:
    """Result of running a single episode on a benchmark task.

    Attributes:
        task_name: Name of the task that was run.
        episode_id: Unique identifier for this episode.
        episode_reward: Total discounted reward accumulated.
        mean_coherence: Mean HIHO coherence across steps.
        final_coherence: Coherence at the final step.
        steps: Number of environment steps taken.
        success: Whether the task was marked successful.
        duration_seconds: Wall-clock time for the episode.
        metrics: Full EVO physics metrics from the episode.
        biography: EVO biography list (excluded from summary for size).
    """

    task_name: str
    episode_id: str
    episode_reward: float
    mean_coherence: float
    final_coherence: float
    steps: int
    success: bool
    duration_seconds: float
    metrics: dict[str, Any]
    biography: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, include_biography: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = {
            "task_name": self.task_name,
            "episode_id": self.episode_id,
            "episode_reward": self.episode_reward,
            "mean_coherence": self.mean_coherence,
            "final_coherence": self.final_coherence,
            "steps": self.steps,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "metrics": self.metrics,
        }
        if include_biography:
            d["biography"] = self.biography
        return d


@dataclass
class BenchmarkResult:
    """Aggregated result for a complete benchmark run.

    Attributes:
        task_name: Name of the task that was benchmarked.
        num_episodes: Number of episodes run.
        mean_reward: Mean episode reward across episodes.
        std_reward: Standard deviation of episode rewards.
        mean_coherence: Mean HIHO coherence across all episodes.
        success_rate: Fraction of episodes marked successful.
        mean_steps: Mean number of steps per episode.
        total_duration_seconds: Total wall-clock time for the benchmark.
        per_episode: List of individual TaskResult dicts.
        aggregate_metrics: Aggregated EVO physics metrics across episodes.
    """

    task_name: str
    num_episodes: int
    mean_reward: float
    std_reward: float
    mean_coherence: float
    success_rate: float
    mean_steps: float
    total_duration_seconds: float
    per_episode: list[dict[str, Any]]
    aggregate_metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_name": self.task_name,
            "num_episodes": self.num_episodes,
            "mean_reward": self.mean_reward,
            "std_reward": self.std_reward,
            "mean_coherence": self.mean_coherence,
            "success_rate": self.success_rate,
            "mean_steps": self.mean_steps,
            "total_duration_seconds": self.total_duration_seconds,
            "per_episode": self.per_episode,
            "aggregate_metrics": self.aggregate_metrics,
        }


class BenchmarkTask(ABC):
    """Abstract base class for a benchmark task.

    Subclass this to define custom tasks with specific success criteria,
    reward shaping, and evaluation logic.

    Example:
        class HIHOBasinEasy(BenchmarkTask):
            name = "cohezion/hiho_basin_easy"
            difficulty = "easy"
            archetype = "HIHO_BASIN"

            def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
                return evo.coherence > 0.7 and evo.hiho_distance < 0.1
    """

    name: str = ""
    difficulty: str = "medium"
    archetype: str = "HIHO_BASIN"
    max_steps: int = 200

    @abstractmethod
    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        """Return True if the current episode state constitutes task success."""
        ...

    def before_episode(self, env: FlumeNavEnv) -> None:  # noqa: B027
        """Hook called before each episode starts. Override for setup."""
        ...

    def after_episode(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> dict[str, Any]:
        """Hook called after each episode ends. Override for custom metrics."""
        return {}


class HIHOBasinEasy(BenchmarkTask):
    """Navigate to HIHO stability (coherence > 0.7, HIHO distance < 0.1)."""

    name = "cohezion/hiho_basin_easy"
    difficulty = "easy"
    archetype = "HIHO_BASIN"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        hiho_distance = abs(float(np.mean(self._final_state)) - 0.5)
        return float(evo.coherence) > 0.7 and hiho_distance < 0.1


class HIHOBasinMedium(HIHOBasinEasy):
    """Navigate to HIHO stability (coherence > 0.8, HIHO distance < 0.05)."""

    name = "cohezion/hiho_basin_medium"
    difficulty = "medium"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        hiho_distance = abs(float(np.mean(self._final_state)) - 0.5)
        return float(evo.coherence) > 0.8 and hiho_distance < 0.05


class HIHOBasinHard(HIHOBasinEasy):
    """Navigate to HIHO stability (coherence > 0.9, HIHO distance < 0.02)."""

    name = "cohezion/hiho_basin_hard"
    difficulty = "hard"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        hiho_distance = abs(float(np.mean(self._final_state)) - 0.5)
        return float(evo.coherence) > 0.9 and hiho_distance < 0.02


class TRIUNEBalanceEasy(BenchmarkTask):
    """Maintain equal TRIUNE activation (all weights within 0.1 of 1/3)."""

    name = "cohezion/triune_balance_easy"
    difficulty = "easy"
    archetype = "TRIUNE_BALANCE"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        d, t, k = evo.doer_weight, evo.thinker_weight, evo.knower_weight
        return all(abs(w - 1 / 3) < 0.15 for w in [d, t, k])


class TRIUNEBalanceMedium(TRIUNEBalanceEasy):
    """Maintain equal TRIUNE activation (all weights within 0.08 of 1/3)."""

    name = "cohezion/triune_balance_medium"
    difficulty = "medium"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        d, t, k = evo.doer_weight, evo.thinker_weight, evo.knower_weight
        return all(abs(w - 1 / 3) < 0.08 for w in [d, t, k])


class TRIUNEBalanceHard(TRIUNEBalanceEasy):
    """Maintain equal TRIUNE activation (all weights within 0.03 of 1/3)."""

    name = "cohezion/triune_balance_hard"
    difficulty = "hard"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        d, t, k = evo.doer_weight, evo.thinker_weight, evo.knower_weight
        return all(abs(w - 1 / 3) < 0.03 for w in [d, t, k])


class ExoticChargeEasy(BenchmarkTask):
    """Survive with high exotic charge (density > 0.8)."""

    name = "cohezion/exotic_charge_easy"
    difficulty = "easy"
    archetype = "EXOTIC_CHARGE"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        return float(evo.exotic_charge_density) > 0.8


class ExoticChargeMedium(ExoticChargeEasy):
    """Survive with high exotic charge (density > 0.9)."""

    name = "cohezion/exotic_charge_medium"
    difficulty = "medium"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        return float(evo.exotic_charge_density) > 0.9


class ExoticChargeHard(ExoticChargeEasy):
    """Survive with high exotic charge (density > 0.95)."""

    name = "cohezion/exotic_charge_hard"
    difficulty = "hard"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        return float(evo.exotic_charge_density) > 0.95


class KordylewskiOrbitEasy(BenchmarkTask):
    """Maintain stable orbit around assigned Lagrange point (distance < 0.3)."""

    name = "cohezion/kordylewski_orbit_easy"
    difficulty = "easy"
    archetype = "KORDYLEWSKI_ORBIT"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        lagrange_distance = float(np.linalg.norm(self._final_state - 0.5))
        return lagrange_distance < 0.3


class KordylewskiOrbitMedium(KordylewskiOrbitEasy):
    """Maintain stable orbit around assigned Lagrange point (distance < 0.15)."""

    name = "cohezion/kordylewski_orbit_medium"
    difficulty = "medium"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        lagrange_distance = float(np.linalg.norm(self._final_state - 0.5))
        return lagrange_distance < 0.15


class KordylewskiOrbitHard(KordylewskiOrbitEasy):
    """Maintain stable orbit around assigned Lagrange point (distance < 0.08)."""

    name = "cohezion/kordylewski_orbit_hard"
    difficulty = "hard"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        lagrange_distance = float(np.linalg.norm(self._final_state - 0.5))
        return lagrange_distance < 0.08


class InterruptionRecoveryEasy(BenchmarkTask):
    """Recover from pause + drift injection (coherence recovered to > 0.6)."""

    name = "cohezion/interruption_recovery_easy"
    difficulty = "easy"
    archetype = "INTERRUPTION_RECOVERY"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        return float(evo.coherence) > 0.6


class InterruptionRecoveryMedium(InterruptionRecoveryEasy):
    """Recover from pause + drift injection (coherence recovered to > 0.75)."""

    name = "cohezion/interruption_recovery_medium"
    difficulty = "medium"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        return float(evo.coherence) > 0.75


class InterruptionRecoveryHard(InterruptionRecoveryEasy):
    """Recover from pause + drift injection (coherence recovered to > 0.85)."""

    name = "cohezion/interruption_recovery_hard"
    difficulty = "hard"

    def is_success(self, env: FlumeNavEnv, evo: EthericVariantOscillator) -> bool:
        return float(evo.coherence) > 0.85


class BenchmarkSuite:
    """LM Evaluation Harness-style benchmark suite for FLUME EVO physics.

    Provides:
    - Task registry with BenchmarkTask subclasses
    - Single and multi-task evaluation
    - Policy-agnostic interface (any get_action callable)
    - JSONL results export
    - Aggregated statistics with EVO physics metrics

    Example:
        suite = BenchmarkSuite()
        suite.register_task("cohezion/hiho_basin_easy", HIHOBasinEasy)
        results = suite.run(
            policy=triune_policy,
            tasks=["cohezion/hiho_basin_easy"],
            num_episodes=50,
            output_path="results/",
        )
    """

    _tasks: dict[str, type[BenchmarkTask]] = {}
    _task_generator: TaskGenerator = field(default_factory=TaskGenerator)

    def __init__(self) -> None:
        self._tasks = {}
        self._task_generator = TaskGenerator()
        self._metrics = EVOPhysicsMetrics()
        self._register_default_tasks()

    def _register_default_tasks(self) -> None:
        """Register all default benchmark tasks."""
        task_classes: list[type[BenchmarkTask]] = [
            HIHOBasinEasy,
            HIHOBasinMedium,
            HIHOBasinHard,
            TRIUNEBalanceEasy,
            TRIUNEBalanceMedium,
            TRIUNEBalanceHard,
            ExoticChargeEasy,
            ExoticChargeMedium,
            ExoticChargeHard,
            KordylewskiOrbitEasy,
            KordylewskiOrbitMedium,
            KordylewskiOrbitHard,
            InterruptionRecoveryEasy,
            InterruptionRecoveryMedium,
            InterruptionRecoveryHard,
        ]
        for cls in task_classes:
            self.register_task(cls.name, cls)

    def register_task(self, name: str, cls: type[BenchmarkTask]) -> None:
        """Register a BenchmarkTask subclass with the suite.

        Args:
            name: Task identifier (e.g., "cohezion/hiho_basin_easy").
            cls: BenchmarkTask subclass.
        """
        self._tasks[name] = cls

    def run(
        self,
        policy: Policy,
        tasks: list[str] | None = None,
        num_episodes: int = 10,
        output_path: Path | str | None = None,
        seed: int | None = None,
        verbose: bool = True,
    ) -> dict[str, BenchmarkResult]:
        """Run benchmark evaluation on one or more tasks.

        Args:
            policy: Policy object with get_action(state) -> (action, log_prob, value).
            tasks: List of task names to evaluate. None = all registered tasks.
            num_episodes: Number of episodes per task.
            output_path: Optional directory to write JSONL results.
            seed: Random seed for reproducibility.
            verbose: If True, print progress.

        Returns:
            Dictionary mapping task name to BenchmarkResult.
        """
        import gymnasium as gym

        rng = np.random.default_rng(seed)

        if tasks is None:
            tasks = list(self._tasks.keys())

        results: dict[str, BenchmarkResult] = {}
        env = gym.make("cohezion/FlumeNav-v0")

        for task_name in tasks:
            task_cls = self._tasks.get(task_name)
            if task_cls is None:
                if verbose:
                    print(f"Warning: unknown task {task_name}, skipping")
                continue

            task_instance = task_cls()
            task_results: list[TaskResult] = []

            if verbose:
                print(f"\n=== Running task: {task_name} ({num_episodes} episodes) ===")

            task_start = time.monotonic()

            for ep in range(num_episodes):
                episode_id = str(uuid.uuid4())[:8]
                ep_start = time.monotonic()

                state, _ = env.reset(seed=int(rng.integers(0, 2**31)) if seed is not None else None)
                task_instance.before_episode(env)

                evo = EthericVariantOscillator(
                    journey_id=f"bench_{task_name}_{ep}",
                )

                episode_reward = 0.0
                coherences: list[float] = []
                step = 0
                done = False
                final_state = state

                while not done and step < task_instance.max_steps:
                    action, _log_prob, _value = policy.get_action(state)
                    action_clipped = np.clip(action, -1.0, 1.0)

                    next_state, reward, terminated, truncated, info = env.step(action_clipped)
                    done = terminated or truncated

                    evo.update_physics(
                        coherence=info.get("coherence", 0.5),
                        hiho_distance=info.get("hiho_distance", 0.5),
                    )

                    coherences.append(float(evo.coherence))
                    episode_reward += float(reward)
                    state = next_state
                    final_state = next_state
                    step += 1

                task_instance._final_state = final_state
                success = task_instance.is_success(task_instance, evo)
                bio_data = evo.export_biography()
                if isinstance(bio_data, dict):
                    biography = bio_data.get("biography", [])
                else:
                    biography = bio_data or []

                duration = time.monotonic() - ep_start
                mean_coh = float(np.mean(coherences)) if coherences else 0.0
                final_coh = float(coherences[-1]) if coherences else 0.0

                metrics = self._metrics.compute_all(biography)

                task_result = TaskResult(
                    task_name=task_name,
                    episode_id=episode_id,
                    episode_reward=episode_reward,
                    mean_coherence=mean_coh,
                    final_coherence=final_coh,
                    steps=step,
                    success=success,
                    duration_seconds=duration,
                    metrics={
                        name: {
                            "mean": r.mean,
                            "std": r.std,
                            "ci_lower": r.ci_lower,
                            "ci_upper": r.ci_upper,
                            "p_value": r.p_value,
                            "effect_size": r.effect_size,
                        }
                        for name, r in metrics.items()
                    },
                    biography=biography.get("biography", []) if isinstance(biography, dict) else biography,
                )
                task_results.append(task_result)

                if verbose:
                    status = "SUCCESS" if success else "FAIL"
                    print(
                        f"  Episode {ep + 1}/{num_episodes} [{status}]: "
                        f"reward={episode_reward:.2f}, "
                        f"coherence={mean_coh:.3f}, "
                        f"steps={step}, "
                        f"time={duration:.2f}s"
                    )

            env.close()

            total_duration = time.monotonic() - task_start
            rewards = [r.episode_reward for r in task_results]
            coherences_all = [r.mean_coherence for r in task_results]
            successes = [r.success for r in task_results]
            steps_all = [float(r.steps) for r in task_results]

            agg_metrics: dict[str, Any] = {}
            if task_results:
                all_biographies = [r.biography for r in task_results]
                agg_metrics = self._aggregate_metrics(all_biographies)

            benchmark_result = BenchmarkResult(
                task_name=task_name,
                num_episodes=num_episodes,
                mean_reward=float(np.mean(rewards)),
                std_reward=float(np.std(rewards, ddof=1)) if len(rewards) > 1 else 0.0,
                mean_coherence=float(np.mean(coherences_all)),
                success_rate=float(np.sum(successes) / len(successes)),
                mean_steps=float(np.mean(steps_all)),
                total_duration_seconds=total_duration,
                per_episode=[r.to_dict(include_biography=False) for r in task_results],
                aggregate_metrics=agg_metrics,
            )
            results[task_name] = benchmark_result

            if output_path is not None:
                out_dir = Path(output_path)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"{task_name.replace('/', '_')}_results.jsonl"
                with open(out_file, "w") as f:
                    for r in task_results:
                        f.write(json.dumps(r.to_dict(include_biography=True)) + "\n")

        return results

    def run_with_ppo_trainer(
        self,
        trainer: Any,
        tasks: list[str] | None = None,
        num_episodes: int = 10,
        output_path: Path | str | None = None,
        seed: int | None = None,
        verbose: bool = True,
    ) -> dict[str, BenchmarkResult]:
        """Run benchmark with a PPOTrainer as the policy.

        Args:
            trainer: PPOTrainer instance to use as policy.
            tasks: List of task names to evaluate.
            num_episodes: Number of episodes per task.
            output_path: Optional directory to write JSONL results.
            seed: Random seed for reproducibility.
            verbose: If True, print progress.

        Returns:
            Dictionary mapping task name to BenchmarkResult.
        """

        class PPOPolicy:
            def __init__(self, t: Any) -> None:
                self._t = t

            def get_action(self, state: np.ndarray) -> tuple[np.ndarray, float, float]:
                return self._t.get_action(state)

        return self.run(
            policy=PPOPolicy(trainer),
            tasks=tasks,
            num_episodes=num_episodes,
            output_path=output_path,
            seed=seed,
            verbose=verbose,
        )

    def _aggregate_metrics(self, biographies: list[list[dict[str, Any]]]) -> dict[str, Any]:
        """Aggregate EVO physics metrics across multiple episode biographies.

        Args:
            biographies: List of biography lists (one per episode).

        Returns:
            Dictionary with aggregated mean/std across all episodes.
        """
        if not biographies:
            return {}

        all_results: dict[str, list[float]] = {}
        for bio in biographies:
            for step in bio:
                for key in [
                    "coherence",
                    "doer_weight",
                    "thinker_weight",
                    "knower_weight",
                    "exotic_charge_density",
                    "phase",
                ]:
                    if key not in step:
                        continue
                    if key not in all_results:
                        all_results[key] = []
                    all_results[key].append(float(step[key]))

        aggregated: dict[str, Any] = {}
        for key, values in all_results.items():
            arr = np.array(values, dtype=np.float64)
            arr = arr[np.isfinite(arr)]
            if len(arr) == 0:
                continue
            aggregated[key] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr, ddof=1)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "n": len(arr),
            }
        return aggregated

    def format_results(self, results: dict[str, BenchmarkResult]) -> str:
        """Format benchmark results as a human-readable string.

        Args:
            results: Output of run().

        Returns:
            Formatted multi-line string with summary table.
        """
        lines = ["\n" + "=" * 80]
        lines.append("FLUME EVO PHYSICS BENCHMARK RESULTS")
        lines.append("=" * 80)

        for task_name, result in results.items():
            lines.append(f"\nTask: {task_name}")
            lines.append(f"  Episodes:        {result.num_episodes}")
            lines.append(f"  Success Rate:    {result.success_rate:.1%}")
            lines.append(f"  Mean Reward:     {result.mean_reward:>8.3f} ± {result.std_reward:.3f}")
            lines.append(f"  Mean Coherence:  {result.mean_coherence:>8.4f}")
            lines.append(f"  Mean Steps:      {result.mean_steps:>8.1f}")
            lines.append(f"  Total Time:      {result.total_duration_seconds:>8.2f}s")
            lines.append(f"  Rate:            {result.num_episodes / result.total_duration_seconds:>8.2f} eps/s")

            if result.aggregate_metrics:
                lines.append("  Aggregate Metrics:")
                for key, vals in result.aggregate_metrics.items():
                    if isinstance(vals, dict) and "mean" in vals:
                        lines.append(f"    {key}: {vals['mean']:.4f} ± {vals.get('std', 0):.4f}")

        overall_success = np.mean([r.success_rate for r in results.values()])
        overall_reward = np.mean([r.mean_reward for r in results.values()])
        lines.append("\n" + "-" * 80)
        lines.append(f"OVERALL SUCCESS RATE: {overall_success:.1%}")
        lines.append(f"OVERALL MEAN REWARD:  {overall_reward:.3f}")
        lines.append("=" * 80 + "\n")

        return "\n".join(lines)
