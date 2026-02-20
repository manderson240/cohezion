"""Observability and metrics for real environment performance.

Tracks execution metrics, resource usage, and performance characteristics
of real environment tasks for debugging and optimization.
"""

from __future__ import annotations

import json
import logging
import resource
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil


logger = logging.getLogger(__name__)


@dataclass
class EnvironmentMetrics:
    """Metrics for a single environment execution."""

    environment_type: str
    task_id: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # Step metrics
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0

    # Timing
    total_duration_ms: float = 0.0
    avg_step_latency_ms: float = 0.0
    max_step_latency_ms: float = 0.0

    # Resource usage
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0

    # Task-specific metrics
    task_completion_rate: float = 0.0
    final_reward: float = 0.0
    phi_score: float = 0.5

    def record_step(self, latency_ms: float, success: bool) -> None:
        """Record metrics for a single step."""
        self.total_steps += 1
        if success:
            self.successful_steps += 1
        else:
            self.failed_steps += 1

        self.total_duration_ms += latency_ms
        self.avg_step_latency_ms = self.total_duration_ms / self.total_steps
        self.max_step_latency_ms = max(self.max_step_latency_ms, latency_ms)

        # Update resource usage
        process = psutil.Process()
        memory_info = process.memory_info()
        self.peak_memory_mb = max(self.peak_memory_mb, memory_info.rss / 1024 / 1024)
        self.peak_cpu_percent = max(self.peak_cpu_percent, process.cpu_percent())

    def finalize(self, success: bool, reward: float, phi_score: float) -> None:
        """Finalize metrics at end of task."""
        self.end_time = time.time()
        self.task_completion_rate = 1.0 if success else 0.0
        self.final_reward = reward
        self.phi_score = phi_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_type": self.environment_type,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": (self.end_time or time.time()) - self.start_time,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "success_rate": self.successful_steps / max(self.total_steps, 1),
            "total_duration_ms": self.total_duration_ms,
            "avg_step_latency_ms": self.avg_step_latency_ms,
            "max_step_latency_ms": self.max_step_latency_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "task_completion_rate": self.task_completion_rate,
            "final_reward": self.final_reward,
            "phi_score": self.phi_score,
        }


class RealEnvironmentMetricsCollector:
    """Collects and aggregates metrics across environment executions.

    Example:
        ```python
        collector = RealEnvironmentMetricsCollector()

        # Track environment execution
        metrics = collector.begin_tracking("shell", "task_123")

        # ... execute steps ...
        for step in steps:
            collector.record_step(metrics, latency_ms=100, success=True)

        collector.finalize(metrics, success=True, reward=0.8, phi_score=0.72)

        # Get aggregated stats
        stats = collector.get_aggregate_stats()
        print(f"Average success rate: {stats['avg_success_rate']:.2%}")
        ```
    """

    def __init__(self, output_dir: str = "data/real_envs/metrics"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._active_metrics: dict[str, EnvironmentMetrics] = {}
        self._completed_metrics: list[EnvironmentMetrics] = []

    def begin_tracking(self, environment_type: str, task_id: str) -> EnvironmentMetrics:
        """Begin tracking metrics for an environment execution."""
        metrics = EnvironmentMetrics(
            environment_type=environment_type,
            task_id=task_id,
        )
        self._active_metrics[task_id] = metrics
        logger.debug(f"Started tracking metrics for {task_id}")
        return metrics

    def record_step(
        self, metrics: EnvironmentMetrics, latency_ms: float, success: bool
    ) -> None:
        """Record a step's metrics."""
        metrics.record_step(latency_ms, success)

    def finalize(
        self,
        metrics: EnvironmentMetrics,
        success: bool,
        reward: float,
        phi_score: float,
    ) -> None:
        """Finalize and save metrics."""
        metrics.finalize(success, reward, phi_score)

        if metrics.task_id in self._active_metrics:
            del self._active_metrics[metrics.task_id]

        self._completed_metrics.append(metrics)

        # Save to disk
        self._save_metrics(metrics)

        logger.info(
            f"Metrics finalized for {metrics.task_id}: "
            f"success={success}, reward={reward:.2f}, phi={phi_score:.2f}"
        )

    def _save_metrics(self, metrics: EnvironmentMetrics) -> Path:
        """Save metrics to disk."""
        filename = (
            f"{metrics.environment_type}_{metrics.task_id}_{int(time.time())}.json"
        )
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2, default=str)

        return filepath

    def get_aggregate_stats(self, n_recent: int = 100) -> dict[str, Any]:
        """Get aggregate statistics across recent executions."""
        recent = self._completed_metrics[-n_recent:] if self._completed_metrics else []

        if not recent:
            return {"error": "No metrics collected yet"}

        # Compute aggregates
        total_tasks = len(recent)
        successful_tasks = sum(1 for m in recent if m.task_completion_rate > 0)

        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / total_tasks,
            "avg_steps_per_task": sum(m.total_steps for m in recent) / total_tasks,
            "avg_step_latency_ms": sum(m.avg_step_latency_ms for m in recent)
            / total_tasks,
            "avg_reward": sum(m.final_reward for m in recent) / total_tasks,
            "avg_phi_score": sum(m.phi_score for m in recent) / total_tasks,
            "peak_memory_mb": max(m.peak_memory_mb for m in recent),
            "by_environment": self._aggregate_by_environment(recent),
        }

    def _aggregate_by_environment(
        self,
        metrics: list[EnvironmentMetrics],
    ) -> dict[str, dict[str, Any]]:
        """Aggregate metrics grouped by environment type."""
        by_env: dict[str, list[EnvironmentMetrics]] = {}

        for m in metrics:
            if m.environment_type not in by_env:
                by_env[m.environment_type] = []
            by_env[m.environment_type].append(m)

        return {
            env_type: {
                "count": len(env_metrics),
                "success_rate": sum(
                    1 for m in env_metrics if m.task_completion_rate > 0
                )
                / len(env_metrics),
                "avg_reward": sum(m.final_reward for m in env_metrics)
                / len(env_metrics),
                "avg_phi_score": sum(m.phi_score for m in env_metrics)
                / len(env_metrics),
            }
            for env_type, env_metrics in by_env.items()
        }

    def export_report(self, filepath: str | None = None) -> Path:
        """Export a comprehensive metrics report."""
        stats = self.get_aggregate_stats()

        report = {
            "timestamp": time.time(),
            "aggregate_stats": stats,
            "recent_tasks": [m.to_dict() for m in self._completed_metrics[-20:]],
        }

        filepath = filepath or str(self.output_dir / f"report_{int(time.time())}.json")
        path = Path(filepath)

        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Exported metrics report to {path}")
        return path
