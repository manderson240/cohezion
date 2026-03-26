"""Evaluation pipeline for FLUME journey benchmarks.

Provides two main abstractions:
1. RalphLoop — FOR iteration with DONE incantation + escalation protocol.
   Named after the archetypal autonomous agent, Ralph. Implements the
   incantation pattern: FOR (iteration) → DONE (convergence check) →
   ESCALATE (strategy change). Each escalation level applies a different
   search/strategy mutation to break out of local minima.

2. EvalPipeline — orchestrates multi-episode evaluation with FlumeNavEnv,
   PPOTrainer, and EthericVariantOscillator, producing CapabilityScorecard
   reports at the end.

Convergence incantation (DONE protocol):
    Level 0: mean_coherence > 0.8 AND std_coherence < 0.05
    Level 1: + success_rate > 0.9
    Level 2: + all 6 EVO physics metrics significant (p < 0.05)
    Level 3: + longitudinal improvement across last 10 runs

Escalation protocol:
    Level 0: No change (baseline exploration)
    Level 1: Perturb learning rate × 2.0
    Level 2: Perturb learning rate × 0.5
    Level 3: Reset optimizer state (full restart)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np


class EpisodeStatus(Enum):
    """Status of an individual episode within the pipeline."""

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    CONVERGED = auto()
    DIVERGED = auto()
    INTERRUPTED = auto()


class ConvergenceLevel(Enum):
    """DONE protocol convergence levels for RalphLoop."""

    NONE = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


@dataclass(frozen=True)
class PipelineProgress:
    """Immutable snapshot of pipeline progress at a given moment.

    Attributes:
        episode: Current episode number (1-indexed).
        total_episodes: Total episodes to run.
        status: Status of the current episode.
        convergence_level: Current DONE convergence level.
        mean_coherence: Running mean coherence across completed episodes.
        std_coherence: Running std of coherence across completed episodes.
        success_rate: Running success rate (fraction of successful episodes).
        escalation_level: Current escalation level (0-3).
        total_reward: Running mean total reward.
        message: Human-readable status message.
    """

    episode: int
    total_episodes: int
    status: EpisodeStatus
    convergence_level: ConvergenceLevel
    mean_coherence: float
    std_coherence: float
    success_rate: float
    escalation_level: int
    total_reward: float
    message: str


@dataclass
class RalphLoopConfig:
    """Configuration for RalphLoop.

    Attributes:
        max_episodes: Maximum episodes before forced termination.
        convergence_levels: Number of convergence levels to track.
        patience: Episodes to wait before escalating at each level.
        min_episodes: Minimum episodes before convergence check.
        hiho_target: Target HIHO coherence value.
        coherence_threshold: Coherence threshold for Level 1 convergence.
        coherence_std_threshold: Coherence std threshold for Level 1 convergence.
        success_threshold: Success rate threshold for Level 2 convergence.
        p_value_threshold: P-value threshold for Level 3 convergence.
    """

    max_episodes: int = 1000
    convergence_levels: int = 3
    patience: int = 20
    min_episodes: int = 10
    hiho_target: float = 0.5
    coherence_threshold: float = 0.8
    coherence_std_threshold: float = 0.05
    success_threshold: float = 0.9
    p_value_threshold: float = 0.05


class RalphLoop:
    """FOR iteration with DONE incantation + escalation for autonomous benchmarking.

    Named after the archetypal autonomous agent, Ralph. Implements the
    incantation pattern: FOR (iteration) → DONE (convergence check) →
    ESCALATE (strategy mutation). The DONE incantation checks four levels
    of convergence, each more stringent.

    The escalation protocol applies strategy mutations at each level:
    - Level 0: Baseline exploration (no mutation)
    - Level 1: Perturb learning rate × 2.0
    - Level 2: Perturb learning rate × 0.5
    - Level 3: Reset optimizer state (full restart)

    Example:
        config = RalphLoopConfig(max_episodes=500, patience=20)
        loop = RalphLoop(config)

        episode_data = []
        for progress in loop.run():
            episode_data.append(progress)
            if progress.status == EpisodeStatus.CONVERGED:
                print("Converged!")
                break
    """

    def __init__(self, config: RalphLoopConfig | None = None) -> None:
        self.config = config or RalphLoopConfig()
        self._episode_data: list[dict[str, Any]] = []
        self._convergence_history: list[ConvergenceLevel] = []
        self._escalation_level: int = 0
        self._patience_counter: int = 0

    def run(
        self,
        episode_fn: callable,
    ) -> Any:
        """Run the RalphLoop FOR-DONE-ESCLALATE iteration.

        This is a generator that yields PipelineProgress at each episode.
        Callers pass an episode_fn that executes one episode and returns
        a dict with episode data.

        Args:
            episode_fn: Callable that executes one episode and returns a dict
                with keys: reward, coherence, success, steps, policy_loss, etc.

        Yields:
            PipelineProgress objects at each episode.
        """
        for episode in range(1, self.config.max_episodes + 1):
            episode_result = episode_fn(episode=episode, escalation_level=self._escalation_level)

            self._episode_data.append(episode_result)
            status = self._compute_status(episode_result)

            progress = self._compute_progress(episode, status)
            yield progress

            if status == EpisodeStatus.CONVERGED:
                return

            if status == EpisodeStatus.DIVERGED:
                return

            self._update_escalation(status)

    def _compute_status(self, episode_result: dict[str, Any]) -> EpisodeStatus:
        """Compute episode status based on convergence levels."""
        n = len(self._episode_data)

        if n < self.config.min_episodes:
            return EpisodeStatus.RUNNING

        recent = self._episode_data[-min(n, 20) :]
        coherences = [e.get("coherence", 0.0) for e in recent]
        successes = [e.get("success", False) for e in recent]

        mean_coh = float(np.mean(coherences))
        std_coh = float(np.std(coherences, ddof=1)) if len(coherences) > 1 else 1.0
        success_rate = float(np.mean(successes)) if successes else 0.0

        level = self._check_convergence_level(mean_coh, std_coh, success_rate)

        if level.value >= ConvergenceLevel.LEVEL_3.value:
            return EpisodeStatus.CONVERGED
        if level.value == ConvergenceLevel.NONE.value and std_coh > 0.3:
            return EpisodeStatus.DIVERGED

        return EpisodeStatus.RUNNING

    def _check_convergence_level(self, mean_coh: float, std_coh: float, success_rate: float) -> ConvergenceLevel:
        """Check which convergence level has been reached."""
        if mean_coh > self.config.coherence_threshold and std_coh < self.config.coherence_std_threshold:
            if success_rate > self.config.success_threshold:
                if self._check_longitudinal_significance():
                    return ConvergenceLevel.LEVEL_3
                return ConvergenceLevel.LEVEL_2
            return ConvergenceLevel.LEVEL_1
        return ConvergenceLevel.NONE

    def _check_longitudinal_significance(self) -> bool:
        """Check Level 3: significance across last 10 runs (p < threshold)."""
        if len(self._episode_data) < 20:
            return False

        recent_10 = self._episode_data[-10:]
        prev_10 = self._episode_data[-20:-10]

        recent_coherences = [e.get("coherence", 0.0) for e in recent_10]
        prev_coherences = [e.get("coherence", 0.0) for e in prev_10]

        from cohezion.benchmarks.agentic_metrics import _mann_whitney_u

        comparison = _mann_whitney_u(
            np.array(recent_coherences),
            np.array(prev_coherences),
        )
        return bool(comparison.p_value < self.config.p_value_threshold)

    def _update_escalation(self, status: EpisodeStatus) -> None:
        """Update escalation level based on patience counter."""
        if status == EpisodeStatus.RUNNING:
            self._patience_counter = 0
            return

        self._patience_counter += 1

        if self._patience_counter >= self.config.patience:
            self._escalation_level = min(self._escalation_level + 1, 3)
            self._patience_counter = 0

    def _compute_progress(self, episode: int, status: EpisodeStatus) -> PipelineProgress:
        """Compute PipelineProgress from current state."""
        n = len(self._episode_data)
        self._episode_data[-min(n, 20) :]

        coherences = [e.get("coherence", 0.0) for e in self._episode_data]
        successes = [e.get("success", False) for e in self._episode_data]
        rewards = [e.get("reward", 0.0) for e in self._episode_data]

        mean_coh = float(np.mean(coherences)) if coherences else 0.0
        std_coh = float(np.std(coherences, ddof=1)) if len(coherences) > 1 else 0.0
        success_rate = float(np.mean(successes)) if successes else 0.0
        mean_reward = float(np.mean(rewards)) if rewards else 0.0

        convergence = self._check_convergence_level(mean_coh, std_coh, success_rate)

        messages = {
            EpisodeStatus.PENDING: "Pending",
            EpisodeStatus.RUNNING: f"Running (escalation={self._escalation_level})",
            EpisodeStatus.SUCCESS: "Success",
            EpisodeStatus.FAILURE: "Failure",
            EpisodeStatus.CONVERGED: f"CONVERGED (level {convergence.value})",
            EpisodeStatus.DIVERGED: "DIVERGED",
            EpisodeStatus.INTERRUPTED: "Interrupted",
        }

        return PipelineProgress(
            episode=episode,
            total_episodes=self.config.max_episodes,
            status=status,
            convergence_level=convergence,
            mean_coherence=mean_coh,
            std_coherence=std_coh,
            success_rate=success_rate,
            escalation_level=self._escalation_level,
            total_reward=mean_reward,
            message=messages.get(status, "Unknown"),
        )


@dataclass
class EvalPipeline:
    """Multi-episode evaluation pipeline for FLUME EVO physics benchmarks.

    Orchestrates:
    1. RalphLoop FOR-DONE-ESCLALATE iteration
    2. FlumeNavEnv environment management
    3. PPOTrainer policy execution
    4. EthericVariantOscillator biography tracking
    5. EVOPhysicsMetrics computation
    6. CapabilityScorecard generation

    Example:
        pipeline = EvalPipeline(
            trainer=PPOTrainer(config),
            task_generator=TaskGenerator(),
        )
        scorecard = pipeline.run(n_episodes=100, output_path="results/")
    """

    task_generator: Any = field(default_factory=lambda: None)
    max_steps: int = 200
    verbose: bool = True

    def __post_init__(self) -> None:
        if self.task_generator is None:
            from cohezion.rl.task_generator import TaskGenerator

            self.task_generator = TaskGenerator()

    def run(
        self,
        policy: Any,
        n_episodes: int = 100,
        output_path: str | None = None,
        seed: int | None = None,
        task_spec: Any | None = None,
    ) -> Any:
        """Run the evaluation pipeline.

        Args:
            policy: Policy with get_action(state) -> (action, log_prob, value).
            n_episodes: Number of episodes to run.
            output_path: Optional path to write results.
            seed: Random seed for reproducibility.
            task_spec: Optional TaskSpec to use for all episodes.

        Returns:
            CapabilityScorecard with full evaluation results.
        """
        import gymnasium as gym

        from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics
        from cohezion.rl.evo import EthericVariantOscillator

        rng = np.random.default_rng(seed)
        env = gym.make("cohezion/FlumeNav-v0", max_steps=self.max_steps)
        EVOPhysicsMetrics()

        episode_results: list[dict[str, Any]] = []
        all_biographies: list[list[dict[str, Any]]] = []

        if task_spec is not None:
            task_generator = None
        else:
            task_generator = self.task_generator

        loop_config = RalphLoopConfig(max_episodes=n_episodes)
        loop = RalphLoop(loop_config)

        def episode_fn(episode: int, escalation_level: int) -> dict[str, Any]:
            nonlocal env

            task_name = "default"
            if task_spec is not None:
                spec = task_spec
            elif task_generator is not None:
                spec = task_generator.sample(difficulty="medium", archetype="HIHO_BASIN")
                task_name = f"{spec.archetype}/{spec.difficulty}"

            state, _ = env.reset(
                seed=int(rng.integers(0, 2**31)) if seed is not None else None,
            )

            evo = EthericVariantOscillator(
                journey_id=f"eval_ep{episode}",
            )

            episode_reward = 0.0
            coherences: list[float] = []
            steps = 0
            done = False

            while not done and steps < self.max_steps:
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
                steps += 1

            bio_data = evo.export_biography()
            if isinstance(bio_data, dict):
                biography = bio_data.get("biography", [])
            else:
                biography = bio_data or []
            success = info.get("task_success", bool(evo.coherence > 0.7))
            mean_coh = float(np.mean(coherences)) if coherences else 0.0

            result = {
                "episode": episode,
                "task_name": task_name,
                "reward": episode_reward,
                "coherence": mean_coh,
                "final_coherence": float(coherences[-1]) if coherences else 0.0,
                "success": success,
                "steps": steps,
                "biography": biography,
                "escalation_level": escalation_level,
            }
            return result

        for progress in loop.run(episode_fn):
            if self.verbose:
                pct = progress.episode / progress.total_episodes * 100
                print(
                    f"[{progress.episode:4d}/{progress.total_episodes} "
                    f"({pct:5.1f}%)] "
                    f"coh={progress.mean_coherence:.4f}±{progress.std_coherence:.4f} "
                    f"succ={progress.success_rate:.2f} "
                    f"esc={progress.escalation_level} "
                    f"— {progress.message}"
                )

            if progress.status == EpisodeStatus.CONVERGED:
                if self.verbose:
                    print("Convergence reached!")
                break
            if progress.status == EpisodeStatus.DIVERGED:
                if self.verbose:
                    print("Divergence detected!")
                break

        env.close()

        episode_results = loop._episode_data
        all_biographies = [e["biography"] for e in episode_results]

        if output_path is not None:
            import json
            from pathlib import Path

            out_dir = Path(output_path)
            out_dir.mkdir(parents=True, exist_ok=True)
            results_file = out_dir / "eval_results.json"
            with open(results_file, "w") as f:
                json.dump([{k: v for k, v in e.items() if k != "biography"} for e in episode_results], f, indent=2)

        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()

        episode_summaries = [
            {
                "episode": e["episode"],
                "task_name": e["task_name"],
                "reward": e["reward"],
                "coherence": e["coherence"],
                "final_coherence": e["final_coherence"],
                "success": e["success"],
                "steps": e["steps"],
            }
            for e in episode_results
        ]

        scorecard.record_run(
            run_id=f"run_{int(time.time())}",
            episodes=episode_summaries,
            biographies=all_biographies,
        )

        return scorecard
