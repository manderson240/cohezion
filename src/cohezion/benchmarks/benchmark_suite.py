"""LM Evaluation Harness-style benchmark suite for FLUME EVO physics."""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics


class Policy(Protocol):
    def get_action(self, state: np.ndarray) -> tuple[np.ndarray, float, float]: ...


@dataclass
class TaskResult:
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
    name: str = ""
    difficulty: str = "medium"
    archetype: str = "HIHO_BASIN"
    max_steps: int = 200

    @abstractmethod
    def is_success(self, env: Any, evo: Any) -> bool: ...

    def before_episode(self, env: Any) -> None: ...  # noqa: B027

    def after_episode(self, env: Any, evo: Any) -> dict[str, Any]:
        return {}


class HIHOBasinEasy(BenchmarkTask):
    name = "cohezion/hiho_basin_easy"
    difficulty = "easy"
    archetype = "HIHO_BASIN"

    def is_success(self, env: Any, evo: Any) -> bool:
        from cohezion.rl.environment import FlumeNavEnv

        if isinstance(env, FlumeNavEnv) and hasattr(env, "_state") and env._state is not None:
            hiho_dist = abs(float(np.mean(env._state)) - 0.5)
        else:
            hiho_dist = abs(evo.doer_state[0] - 0.5) if hasattr(evo, "doer_state") else 0.1
        return float(getattr(evo, "coherence_amplitude", 0.0)) > 0.7 and hiho_dist < 0.1


class HIHOBasinMedium(HIHOBasinEasy):
    name = "cohezion/hiho_basin_medium"
    difficulty = "medium"

    def is_success(self, env: Any, evo: Any) -> bool:
        from cohezion.rl.environment import FlumeNavEnv

        if isinstance(env, FlumeNavEnv) and hasattr(env, "_state") and env._state is not None:
            hiho_dist = abs(float(np.mean(env._state)) - 0.5)
        else:
            hiho_dist = abs(evo.doer_state[0] - 0.5) if hasattr(evo, "doer_state") else 0.05
        return float(getattr(evo, "coherence_amplitude", 0.0)) > 0.8 and hiho_dist < 0.05


class HIHOBasinHard(HIHOBasinEasy):
    name = "cohezion/hiho_basin_hard"
    difficulty = "hard"

    def is_success(self, env: Any, evo: Any) -> bool:
        from cohezion.rl.environment import FlumeNavEnv

        if isinstance(env, FlumeNavEnv) and hasattr(env, "_state") and env._state is not None:
            hiho_dist = abs(float(np.mean(env._state)) - 0.5)
        else:
            hiho_dist = abs(evo.doer_state[0] - 0.5) if hasattr(evo, "doer_state") else 0.02
        return float(getattr(evo, "coherence_amplitude", 0.0)) > 0.9 and hiho_dist < 0.02


class TRIUNEBalanceEasy(BenchmarkTask):
    name = "cohezion/triune_balance_easy"
    difficulty = "easy"
    archetype = "TRIUNE_BALANCE"

    def is_success(self, env: Any, evo: Any) -> bool:
        dm = float(np.mean(evo.doer_state))
        tm = float(np.mean(evo.thinker_state))
        km = float(np.mean(evo.knower_state))
        return all(abs(v - 0.5) < 0.15 for v in [dm, tm, km])


class TRIUNEBalanceMedium(TRIUNEBalanceEasy):
    name = "cohezion/triune_balance_medium"
    difficulty = "medium"

    def is_success(self, env: Any, evo: Any) -> bool:
        dm = float(np.mean(evo.doer_state))
        tm = float(np.mean(evo.thinker_state))
        km = float(np.mean(evo.knower_state))
        return all(abs(v - 0.5) < 0.08 for v in [dm, tm, km])


class TRIUNEBalanceHard(TRIUNEBalanceEasy):
    name = "cohezion/triune_balance_hard"
    difficulty = "hard"

    def is_success(self, env: Any, evo: Any) -> bool:
        dm = float(np.mean(evo.doer_state))
        tm = float(np.mean(evo.thinker_state))
        km = float(np.mean(evo.knower_state))
        return all(abs(v - 0.5) < 0.03 for v in [dm, tm, km])


class ExoticChargeEasy(BenchmarkTask):
    name = "cohezion/exotic_charge_easy"
    difficulty = "easy"
    archetype = "EXOTIC_CHARGE"

    def is_success(self, env: Any, evo: Any) -> bool:
        return float(getattr(evo, "exotic_charge_density", 0.0)) > 0.8


class ExoticChargeMedium(ExoticChargeEasy):
    name = "cohezion/exotic_charge_medium"
    difficulty = "medium"

    def is_success(self, env: Any, evo: Any) -> bool:
        return float(getattr(evo, "exotic_charge_density", 0.0)) > 0.9


class ExoticChargeHard(ExoticChargeEasy):
    name = "cohezion/exotic_charge_hard"
    difficulty = "hard"

    def is_success(self, env: Any, evo: Any) -> bool:
        return float(getattr(evo, "exotic_charge_density", 0.0)) > 0.95


class KordylewskiOrbitEasy(BenchmarkTask):
    name = "cohezion/kordylewski_orbit_easy"
    difficulty = "easy"
    archetype = "KORDYLEWSKI_ORBIT"

    def is_success(self, env: Any, evo: Any) -> bool:
        from cohezion.rl.environment import FlumeNavEnv

        if isinstance(env, FlumeNavEnv) and hasattr(env, "_state") and env._state is not None:
            dist = float(np.linalg.norm(env._state - 0.5))
        else:
            dist = 5.0
        return dist < 0.3


class KordylewskiOrbitMedium(KordylewskiOrbitEasy):
    name = "cohezion/kordylewski_orbit_medium"
    difficulty = "medium"

    def is_success(self, env: Any, evo: Any) -> bool:
        from cohezion.rl.environment import FlumeNavEnv

        if isinstance(env, FlumeNavEnv) and hasattr(env, "_state") and env._state is not None:
            dist = float(np.linalg.norm(env._state - 0.5))
        else:
            dist = 5.0
        return dist < 0.15


class KordylewskiOrbitHard(KordylewskiOrbitEasy):
    name = "cohezion/kordylewski_orbit_hard"
    difficulty = "hard"

    def is_success(self, env: Any, evo: Any) -> bool:
        from cohezion.rl.environment import FlumeNavEnv

        if isinstance(env, FlumeNavEnv) and hasattr(env, "_state") and env._state is not None:
            dist = float(np.linalg.norm(env._state - 0.5))
        else:
            dist = 5.0
        return dist < 0.08


class InterruptionRecoveryEasy(BenchmarkTask):
    name = "cohezion/interruption_recovery_easy"
    difficulty = "easy"
    archetype = "INTERRUPTION_RECOVERY"

    def is_success(self, env: Any, evo: Any) -> bool:
        return float(getattr(evo, "coherence_amplitude", 0.0)) > 0.6


class InterruptionRecoveryMedium(InterruptionRecoveryEasy):
    name = "cohezion/interruption_recovery_medium"
    difficulty = "medium"

    def is_success(self, env: Any, evo: Any) -> bool:
        return float(getattr(evo, "coherence_amplitude", 0.0)) > 0.75


class InterruptionRecoveryHard(InterruptionRecoveryEasy):
    name = "cohezion/interruption_recovery_hard"
    difficulty = "hard"

    def is_success(self, env: Any, evo: Any) -> bool:
        return float(getattr(evo, "coherence_amplitude", 0.0)) > 0.85


class BenchmarkSuite:
    _tasks: dict[str, type[BenchmarkTask]]

    def __init__(self) -> None:
        self._tasks: dict[str, type] = {}
        self._metrics = EVOPhysicsMetrics()
        self._register_default_tasks()

    def _register_default_tasks(self) -> None:
        for cls in [
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
        ]:
            self._tasks[cls.name] = cls  # type: ignore[type-abstract]

    def register_task(self, name: str, cls: type) -> None:
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
            task_start = time.monotonic()
            for ep in range(num_episodes):
                episode_id = str(uuid.uuid4())[:8]
                ep_start = time.monotonic()
                state, _ = env.reset(seed=int(rng.integers(0, 2**31)) if seed is not None else None)
                task_instance.before_episode(env)
                evo = self._create_evo(task_instance)
                episode_reward = 0.0
                coherences: list[float] = []
                step = 0
                done = False
                while not done and step < task_instance.max_steps:
                    action, _, _ = policy.get_action(state)
                    action_clipped = np.clip(action, -1.0, 1.0)
                    next_state, reward, terminated, truncated, info = env.step(action_clipped)
                    done = terminated or truncated
                    evo.update_physics(
                        coherence=info.get("coherence", 0.5),
                        step=step,
                        doer_state=state,
                        thinker_state=None,
                        knower_state=None,
                    )
                    coherences.append(float(getattr(evo, "coherence_amplitude", 0.5)))
                    episode_reward += float(reward)
                    state = next_state
                    step += 1
                success = task_instance.is_success(env, evo)
                biography = evo.trajectory
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
                        n: {
                            "mean": r.mean,
                            "std": r.std,
                            "ci_lower": r.ci_lower,
                            "ci_upper": r.ci_upper,
                            "p_value": r.p_value,
                            "effect_size": r.effect_size,
                        }
                        for n, r in metrics.items()
                    },
                    biography=biography,
                )
                task_results.append(task_result)
                if verbose:
                    status = "SUCCESS" if success else "FAIL"
                    print(
                        f"  Episode {ep + 1}/{num_episodes} [{status}]: "
                        f"reward={episode_reward:.2f} coh={mean_coh:.3f} steps={step} "
                        f"time={duration:.2f}s"
                    )
            env.close()
            total_duration = time.monotonic() - task_start
            rewards = [r.episode_reward for r in task_results]
            coherences_all = [r.mean_coherence for r in task_results]
            successes = [r.success for r in task_results]
            steps_all = [float(r.steps) for r in task_results]
            agg_metrics = self._aggregate_metrics([r.biography for r in task_results])
            benchmark_result = BenchmarkResult(
                task_name=task_name,
                num_episodes=num_episodes,
                mean_reward=float(np.mean(rewards)),
                std_reward=float(np.std(rewards, ddof=1)) if len(rewards) > 1 else 0.0,
                mean_coherence=float(np.mean(coherences_all)),
                success_rate=float(np.sum(successes) / len(successes)),
                mean_steps=float(np.mean(steps_all)),
                total_duration_seconds=total_duration,
                per_episode=[r.to_dict() for r in task_results],
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

    def _create_evo(self, task: BenchmarkTask) -> Any:
        from cohezion.rl.evo import EthericVariantOscillator

        evo = EthericVariantOscillator()
        evo.kordylewski_cloud_id = "L4" if np.random.rand() < 0.5 else "L5"
        return evo

    def _aggregate_metrics(self, biographies: list[list[dict[str, Any]]]) -> dict[str, Any]:
        if not biographies:
            return {}
        all_metrics: dict[str, list[float]] = {}
        for bio in biographies:
            for step in bio:
                for key in ["coherence", "exotic_charge_density"]:
                    if key in step:
                        if key not in all_metrics:
                            all_metrics[key] = []
                        all_metrics[key].append(float(step[key]))
        aggregated: dict[str, Any] = {}
        for key, values in all_metrics.items():
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
        lines = ["\n" + "=" * 80, "FLUME EVO PHYSICS BENCHMARK RESULTS", "=" * 80]
        for task_name, result in results.items():
            lines.extend(
                [
                    f"\nTask: {task_name}",
                    f"  Episodes:        {result.num_episodes}",
                    f"  Success Rate:    {result.success_rate:.1%}",
                    f"  Mean Reward:     {result.mean_reward:>8.3f} ± {result.std_reward:.3f}",
                    f"  Mean Coherence:  {result.mean_coherence:>8.4f}",
                    f"  Mean Steps:      {result.mean_steps:>8.1f}",
                    f"  Total Time:      {result.total_duration_seconds:>8.2f}s",
                ]
            )
        overall_success = float(np.mean([r.success_rate for r in results.values()]))
        overall_reward = float(np.mean([r.mean_reward for r in results.values()]))
        lines.extend(
            [
                "\n" + "-" * 80,
                f"OVERALL SUCCESS RATE: {overall_success:.1%}",
                f"OVERALL MEAN REWARD:  {overall_reward:.3f}",
                "=" * 80 + "\n",
            ]
        )
        return "\n".join(lines)
