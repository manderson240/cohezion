"""Team-level metrics aggregation for compound team execution."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field


class WaveMetrics(BaseModel):
    """Metrics for a single execution wave."""

    wave_index: int = 0
    task_count: int = 0
    duration_ms: float = 0.0
    tokens: int = 0
    model_usage: dict[str, int] = {}
    successes: int = 0
    failures: int = 0


class TeamCompoundMetrics(BaseModel):
    """Aggregated metrics for a team compound execution run."""

    plan_name: str = ""
    waves: list[WaveMetrics] = []
    total_tasks: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_usage: dict[str, int] = {}
    parallel_efficiency: float = 0.0
    compound_score_delta: float = 0.0
    success_rate: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class TeamMetricsAggregator:
    """Collect and aggregate metrics across execution waves.

    Records per-wave timing, token usage, and model distribution, then
    computes parallel efficiency as the ratio of sequential work time to
    actual wall-clock time.
    """

    def __init__(self, plan_name: str = "") -> None:
        self._plan_name = plan_name
        self._waves: list[WaveMetrics] = []
        self._model_usage: dict[str, int] = {}
        self._total_tokens = 0
        self._total_tasks = 0
        self._successes = 0
        self._failures = 0

    def record_wave(
        self,
        wave_index: int,
        task_results: list[dict[str, Any]],
        duration_ms: float,
    ) -> WaveMetrics:
        """Record metrics for a completed wave.

        Parameters
        ----------
        wave_index : int
            Zero-based wave index.
        task_results : list[dict[str, Any]]
            Per-task results with keys: tokens, model, status.
        duration_ms : float
            Wall-clock time for this wave.

        Returns
        -------
        WaveMetrics
            Metrics for this wave.
        """
        wave_tokens = sum(r.get("tokens", 0) for r in task_results)
        wave_models: dict[str, int] = {}
        successes = 0
        failures = 0

        for r in task_results:
            model = r.get("model", "unknown")
            if model:
                wave_models[model] = wave_models.get(model, 0) + 1
                self._model_usage[model] = self._model_usage.get(model, 0) + 1
            if r.get("status") == "completed":
                successes += 1
            else:
                failures += 1

        self._total_tokens += wave_tokens
        self._total_tasks += len(task_results)
        self._successes += successes
        self._failures += failures

        wave = WaveMetrics(
            wave_index=wave_index,
            task_count=len(task_results),
            duration_ms=round(duration_ms, 2),
            tokens=wave_tokens,
            model_usage=wave_models,
            successes=successes,
            failures=failures,
        )
        self._waves.append(wave)
        return wave

    def finalize(
        self,
        total_duration_ms: float,
        compound_score_delta: float = 0.0,
    ) -> TeamCompoundMetrics:
        """Compute final aggregated metrics.

        Parameters
        ----------
        total_duration_ms : float
            Total wall-clock time for the entire execution.
        compound_score_delta : float
            Aggregate compound score change.

        Returns
        -------
        TeamCompoundMetrics
            Full metrics report.
        """
        # Parallel efficiency: sum of wave durations / total duration
        # > 1.0 means we saved time via parallelism
        sum_wave_durations = sum(w.duration_ms for w in self._waves)
        efficiency = sum_wave_durations / total_duration_ms if total_duration_ms > 0 else 1.0

        success_rate = self._successes / self._total_tasks if self._total_tasks > 0 else 0.0

        return TeamCompoundMetrics(
            plan_name=self._plan_name,
            waves=self._waves,
            total_tasks=self._total_tasks,
            total_tokens=self._total_tokens,
            total_duration_ms=round(total_duration_ms, 2),
            model_usage=dict(self._model_usage),
            parallel_efficiency=round(efficiency, 4),
            compound_score_delta=compound_score_delta,
            success_rate=round(success_rate, 4),
        )
