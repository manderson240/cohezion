"""Evaluation pipeline for FLUME journey benchmarks.

RalphLoop: FOR-DONE-ESCALATE iteration pattern.
EvalPipeline: multi-episode orchestration with FlumeNavEnv + EthericVariantOscillator."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

import numpy as np


class EpisodeStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    CONVERGED = auto()
    DIVERGED = auto()
    INTERRUPTED = auto()


class ConvergenceLevel(Enum):
    NONE = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


@dataclass(frozen=True)
class PipelineProgress:
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
    max_episodes: int = 1000
    patience: int = 20
    min_episodes: int = 10
    coherence_threshold: float = 0.8
    coherence_std_threshold: float = 0.05
    success_threshold: float = 0.9
    p_value_threshold: float = 0.05


class RalphLoop:
    def __init__(self, config: RalphLoopConfig | None = None) -> None:
        self.config = config or RalphLoopConfig()
        self._episode_data: list[dict[str, Any]] = []
        self._escalation_level: int = 0
        self._patience_counter: int = 0

    def run(self, episode_fn: Callable) -> Any:
        for episode in range(1, self.config.max_episodes + 1):
            episode_result = episode_fn(episode=episode, escalation_level=self._escalation_level)
            self._episode_data.append(episode_result)
            status = self._compute_status(episode_result)
            progress = self._compute_progress(episode, status)
            yield progress
            if status in (EpisodeStatus.CONVERGED, EpisodeStatus.DIVERGED):
                return
            self._update_escalation(status)

    def _compute_status(self, episode_result: dict[str, Any]) -> EpisodeStatus:
        n = len(self._episode_data)
        if n < self.config.min_episodes:
            return EpisodeStatus.RUNNING
        recent = self._episode_data[-min(n, 20) :]
        coherences = [e.get("coherence", 0.0) for e in recent]
        successes = [e.get("success", False) for e in recent]
        mean_coh = float(np.mean(coherences)) if coherences else 0.0
        std_coh = float(np.std(coherences, ddof=1)) if len(coherences) > 1 else 1.0
        success_rate = float(np.mean(successes)) if successes else 0.0
        level = self._check_convergence(mean_coh, std_coh, success_rate)
        if level == ConvergenceLevel.LEVEL_3:
            return EpisodeStatus.CONVERGED
        if level == ConvergenceLevel.NONE and std_coh > 0.3:
            return EpisodeStatus.DIVERGED
        return EpisodeStatus.RUNNING

    def _check_convergence(
        self, mean_coh: float, std_coh: float, success_rate: float
    ) -> ConvergenceLevel:
        if (
            mean_coh > self.config.coherence_threshold
            and std_coh < self.config.coherence_std_threshold
        ):
            if success_rate > self.config.success_threshold:
                if self._check_longitudinal():
                    return ConvergenceLevel.LEVEL_3
                return ConvergenceLevel.LEVEL_2
            return ConvergenceLevel.LEVEL_1
        return ConvergenceLevel.NONE

    def _check_longitudinal(self) -> bool:
        if len(self._episode_data) < 20:
            return False
        recent = [e.get("coherence", 0.5) for e in self._episode_data[-10:]]
        prev = [e.get("coherence", 0.5) for e in self._episode_data[-20:-10]]
        from cohezion.benchmarks.agentic_metrics import _mann_whitney_u

        comp = _mann_whitney_u(np.array(recent), np.array(prev))
        return bool(comp.p_value < self.config.p_value_threshold)

    def _update_escalation(self, status: EpisodeStatus) -> None:
        if status == EpisodeStatus.RUNNING:
            self._patience_counter = 0
            return
        self._patience_counter += 1
        if self._patience_counter >= self.config.patience:
            self._escalation_level = min(self._escalation_level + 1, 3)
            self._patience_counter = 0

    def _compute_progress(self, episode: int, status: EpisodeStatus) -> PipelineProgress:
        coherences = [e.get("coherence", 0.0) for e in self._episode_data]
        successes = [e.get("success", False) for e in self._episode_data]
        rewards = [e.get("reward", 0.0) for e in self._episode_data]
        mean_coh = float(np.mean(coherences)) if coherences else 0.0
        std_coh = float(np.std(coherences, ddof=1)) if len(coherences) > 1 else 0.0
        success_rate = float(np.mean(successes)) if successes else 0.0
        mean_reward = float(np.mean(rewards)) if rewards else 0.0
        level = self._check_convergence(mean_coh, std_coh, success_rate)
        messages = {
            EpisodeStatus.RUNNING: f"Running (escalation={self._escalation_level})",
            EpisodeStatus.CONVERGED: f"CONVERGED (level {level.value})",
            EpisodeStatus.DIVERGED: "DIVERGED",
        }
        return PipelineProgress(
            episode=episode,
            total_episodes=self.config.max_episodes,
            status=status,
            convergence_level=level,
            mean_coherence=mean_coh,
            std_coherence=std_coh,
            success_rate=success_rate,
            escalation_level=self._escalation_level,
            total_reward=mean_reward,
            message=messages.get(status, str(status)),
        )


@dataclass
class EvalPipeline:
    max_steps: int = 200
    verbose: bool = True

    def run(
        self,
        policy: Any,
        n_episodes: int = 100,
        output_path: str | None = None,
        seed: int | None = None,
    ) -> Any:
        import gymnasium as gym

        from cohezion.rl.evo import EthericVariantOscillator

        rng = np.random.default_rng(seed)
        env = gym.make("cohezion/FlumeNav-v0")
        loop = RalphLoop(RalphLoopConfig(max_episodes=n_episodes))

        def episode_fn(episode: int, escalation_level: int) -> dict[str, Any]:
            state, _ = env.reset(seed=int(rng.integers(0, 2**31)) if seed is not None else None)
            evo = EthericVariantOscillator(journey_id=f"eval_ep{episode}")
            episode_reward = 0.0
            coherences: list[float] = []
            steps = 0
            done = False
            while not done and steps < self.max_steps:
                action, _, _ = policy.get_action(state)
                action_clipped = np.clip(action, -1.0, 1.0)
                next_state, reward, terminated, truncated, info = env.step(action_clipped)
                done = terminated or truncated
                evo.update_physics(
                    coherence=info.get("coherence", 0.5),
                    step=steps,
                    doer_state=state,
                    thinker_state=None,
                    knower_state=None,
                )
                coherences.append(float(evo.coherence_amplitude))
                episode_reward += float(reward)
                state = next_state
                steps += 1
            bio_data = evo.to_exotic_vacuum_biography()
            if isinstance(bio_data, dict):
                biography = bio_data.get("biography", [])
            else:
                biography = bio_data or []
            mean_coh = float(np.mean(coherences)) if coherences else 0.0
            return {
                "episode": episode,
                "reward": episode_reward,
                "coherence": mean_coh,
                "success": bool(evo.coherence_amplitude > 0.7),
                "steps": steps,
                "biography": biography,
                "escalation_level": escalation_level,
            }

        episode_results: list[PipelineProgress] = []
        for progress in loop.run(episode_fn):
            if self.verbose:
                pct = progress.episode / progress.total_episodes * 100
                print(
                    f"[{progress.episode:4d}/{progress.total_episodes} ({pct:5.1f}%)] "
                    f"coh={progress.mean_coherence:.4f}±{progress.std_coherence:.4f} "
                    f"succ={progress.success_rate:.2f} esc={progress.escalation_level} "
                    f"— {progress.message}"
                )
            episode_results.append(progress)
            if progress.status == EpisodeStatus.CONVERGED:
                if self.verbose:
                    print("Convergence reached!")
                break
            if progress.status == EpisodeStatus.DIVERGED:
                if self.verbose:
                    print("Divergence detected!")
                break

        env.close()

        if output_path is not None:
            from pathlib import Path

            out_dir = Path(output_path)
            out_dir.mkdir(parents=True, exist_ok=True)
            results_file = out_dir / "eval_results.json"
            with open(results_file, "w") as f:
                json.dump(
                    [dict(e.__dict__) for e in episode_results],
                    f,
                    default=str,
                    indent=2,
                )

        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            run_id=f"run_{int(time.time())}",
            episodes=[
                {
                    "episode": p.episode,
                    "reward": p.total_reward,
                    "coherence": p.mean_coherence,
                    "final_coherence": p.mean_coherence,
                    "success": p.success_rate > 0.5,
                    "steps": 0,
                }
                for p in episode_results
            ],
            biographies=[{} for _ in episode_results],
        )
        return scorecard
