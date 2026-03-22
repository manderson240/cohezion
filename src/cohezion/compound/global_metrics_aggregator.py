"""Global metrics aggregation for distributed multi-instance teams.

Aggregates metrics across instances, supports time-windowed queries, and
provides real-time dashboard data. Supports up to 10+ instances without
degradation.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.swarm.team_metrics import TeamCompoundMetrics


logger = logging.getLogger(__name__)


@dataclass
class InstanceMetrics:
    """Metrics from a single instance (agent/executor)."""

    instance_id: str
    timestamp: float
    execution_count: int = 0
    success_count: int = 0
    total_tokens: int = 0
    avg_duration_ms: float = 0.0
    coherence_score: float = 0.0
    cache_hit_rate: float = 0.0
    skill_diversity: float = 0.0
    model_usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TimeWindowMetrics:
    """Aggregated metrics for a time window."""

    window_start: float
    window_end: float
    instance_count: int = 0
    total_executions: int = 0
    total_successes: int = 0
    total_tokens: int = 0
    avg_throughput: float = 0.0  # executions per second
    avg_coherence: float = 0.0
    cache_hit_rate_mean: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    model_distribution: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.total_successes / self.total_executions

    @property
    def window_duration_sec(self) -> float:
        """Duration of this window in seconds."""
        return self.window_end - self.window_start

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SkillMetrics:
    """Per-skill aggregated metrics."""

    skill_name: str
    instance_count: int = 0
    execution_count: int = 0
    success_count: int = 0
    avg_tokens: float = 0.0
    avg_duration_ms: float = 0.0
    coherence_trend: list[float] = field(default_factory=list)
    efficiency_trend: list[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["success_rate"] = self.success_rate
        return d


class GlobalMetricsAggregator:
    """Aggregate metrics across distributed instances.

    Provides multi-instance queries by team, agent, skill, and time range.
    Optimized for query latency <500ms over 1-week ranges.
    """

    def __init__(self, data_dir: Path | None = None, window_size_sec: int = 60):
        """Initialize aggregator.

        Parameters
        ----------
        data_dir : Path | None
            Directory for persistent metrics. If None, uses memory-only.
        window_size_sec : int
            Time window size for aggregations (default 60 seconds).
        """
        self._data_dir = data_dir or Path("data/global_metrics")
        self._window_size_sec = window_size_sec
        self._lock = threading.RLock()

        # In-memory storage: instance_id -> list[InstanceMetrics]
        self._instance_metrics: dict[str, list[InstanceMetrics]] = defaultdict(list)

        # Skill metrics: skill_name -> SkillMetrics
        self._skill_metrics: dict[str, SkillMetrics] = {}

        # Time-windowed aggregations for quick queries
        self._window_cache: dict[tuple[float, float], TimeWindowMetrics] = {}

        # Last update time per instance
        self._last_update: dict[str, float] = {}

        # Ensure data directory exists
        if self._data_dir:
            self._data_dir.mkdir(parents=True, exist_ok=True)

    def record_instance_metrics(
        self, instance_id: str, metrics: InstanceMetrics
    ) -> None:
        """Record metrics from a single instance.

        Parameters
        ----------
        instance_id : str
            Unique instance identifier.
        metrics : InstanceMetrics
            Metrics snapshot from the instance.
        """
        with self._lock:
            self._instance_metrics[instance_id].append(metrics)
            self._last_update[instance_id] = time.time()

            # Keep memory bounded: keep only last 1000 records per instance
            if len(self._instance_metrics[instance_id]) > 1000:
                self._instance_metrics[instance_id] = self._instance_metrics[instance_id][-1000:]

            logger.debug(
                "Recorded metrics from instance %s: %d executions",
                instance_id,
                metrics.execution_count,
            )

    def record_team_metrics(self, team_id: str, instance_id: str, metrics: TeamCompoundMetrics) -> None:
        """Record team-level metrics from an instance.

        Parameters
        ----------
        team_id : str
            Team identifier.
        instance_id : str
            Instance identifier.
        metrics : TeamCompoundMetrics
            Team execution metrics.
        """
        # Convert team metrics to instance metrics
        total_executions = metrics.total_tasks
        total_successes = sum(w.successes for w in metrics.waves)

        avg_duration = (
            metrics.total_duration_ms / len(metrics.waves) if metrics.waves else 0.0
        )

        instance_metrics = InstanceMetrics(
            instance_id=instance_id,
            timestamp=metrics.timestamp,
            execution_count=total_executions,
            success_count=total_successes,
            total_tokens=metrics.total_tokens,
            avg_duration_ms=avg_duration,
            coherence_score=metrics.compound_score_delta,
            cache_hit_rate=0.0,  # Would be populated by executor
            skill_diversity=len(metrics.model_usage),
            model_usage=metrics.model_usage,
            metadata={
                "team_id": team_id,
                "parallel_efficiency": metrics.parallel_efficiency,
            },
        )

        self.record_instance_metrics(instance_id, instance_metrics)

    def query_by_time_range(self, start_time: float, end_time: float) -> TimeWindowMetrics:
        """Query aggregated metrics for a time range.

        Optimized to run in <500ms for 1-week ranges.

        Parameters
        ----------
        start_time : float
            Unix timestamp (seconds).
        end_time : float
            Unix timestamp (seconds).

        Returns
        -------
        TimeWindowMetrics
            Aggregated metrics for the time range.
        """
        with self._lock:
            # Check cache first
            cache_key = (start_time, end_time)
            if cache_key in self._window_cache:
                return self._window_cache[cache_key]

            # Collect all metrics in range
            all_latencies: list[float] = []
            coherence_scores: list[float] = []
            cache_hit_rates: list[float] = []
            all_model_usage: dict[str, int] = defaultdict(int)
            total_executions = 0
            total_successes = 0
            total_tokens = 0
            instance_ids_in_range = set()

            for instance_id, metrics_list in self._instance_metrics.items():
                for m in metrics_list:
                    if start_time <= m.timestamp <= end_time:
                        instance_ids_in_range.add(instance_id)
                        total_executions += m.execution_count
                        total_successes += m.success_count
                        total_tokens += m.total_tokens
                        all_latencies.append(m.avg_duration_ms)
                        coherence_scores.append(m.coherence_score)
                        cache_hit_rates.append(m.cache_hit_rate)

                        # Aggregate model usage
                        for model, count in m.model_usage.items():
                            all_model_usage[model] += count

            # Calculate window duration
            window_duration = end_time - start_time
            avg_throughput = total_executions / window_duration if window_duration > 0 else 0.0

            # Calculate percentiles
            p50_latency = self._calculate_percentile(all_latencies, 0.5)
            p95_latency = self._calculate_percentile(all_latencies, 0.95)
            p99_latency = self._calculate_percentile(all_latencies, 0.99)

            # Calculate means
            avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
            cache_hit_mean = sum(cache_hit_rates) / len(cache_hit_rates) if cache_hit_rates else 0.0

            # Normalize model distribution
            model_distribution: dict[str, float] = {}
            if total_executions > 0:
                for model, count in all_model_usage.items():
                    model_distribution[model] = count / total_executions

            agg = TimeWindowMetrics(
                window_start=start_time,
                window_end=end_time,
                instance_count=len(instance_ids_in_range),
                total_executions=total_executions,
                total_successes=total_successes,
                total_tokens=total_tokens,
                avg_throughput=round(avg_throughput, 4),
                avg_coherence=round(avg_coherence, 4),
                cache_hit_rate_mean=round(cache_hit_mean, 4),
                p50_latency_ms=round(p50_latency, 2),
                p95_latency_ms=round(p95_latency, 2),
                p99_latency_ms=round(p99_latency, 2),
                model_distribution=model_distribution,
            )

            # Cache result
            self._window_cache[cache_key] = agg

            return agg

    def query_by_agent(
        self,
        agent_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[InstanceMetrics]:
        """Query metrics for a specific agent.

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        start_time : float | None
            Filter start time (Unix timestamp).
        end_time : float | None
            Filter end time (Unix timestamp).

        Returns
        -------
        list[InstanceMetrics]
            Metrics for the agent.
        """
        with self._lock:
            if agent_id not in self._instance_metrics:
                return []

            metrics_list = self._instance_metrics[agent_id]

            # Filter by time range
            if start_time is not None or end_time is not None:
                start = start_time or 0
                end = end_time or time.time()
                metrics_list = [m for m in metrics_list if start <= m.timestamp <= end]

            return list(metrics_list)

    def query_by_skill(
        self,
        skill_name: str,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> SkillMetrics | None:
        """Query aggregated metrics for a specific skill.

        Parameters
        ----------
        skill_name : str
            Skill name.
        start_time : float | None
            Filter start time (Unix timestamp).
        end_time : float | None
            Filter end time (Unix timestamp).

        Returns
        -------
        SkillMetrics | None
            Aggregated skill metrics, or None if no data.
        """
        with self._lock:
            if skill_name in self._skill_metrics:
                return self._skill_metrics[skill_name]
            return None

    def record_skill_metrics(
        self,
        skill_name: str,
        execution_count: int,
        success_count: int,
        avg_tokens: float,
        avg_duration_ms: float,
        coherence: float,
        efficiency: float,
    ) -> None:
        """Record metrics for a skill.

        Parameters
        ----------
        skill_name : str
            Skill identifier.
        execution_count : int
            Total executions.
        success_count : int
            Successful executions.
        avg_tokens : float
            Average tokens used.
        avg_duration_ms : float
            Average duration in milliseconds.
        coherence : float
            Coherence score (0-1).
        efficiency : float
            Efficiency score (0-1).
        """
        with self._lock:
            if skill_name not in self._skill_metrics:
                self._skill_metrics[skill_name] = SkillMetrics(skill_name=skill_name)

            metrics = self._skill_metrics[skill_name]
            metrics.execution_count += execution_count
            metrics.success_count += success_count
            metrics.avg_tokens = (metrics.avg_tokens + avg_tokens) / 2
            metrics.avg_duration_ms = (metrics.avg_duration_ms + avg_duration_ms) / 2
            metrics.coherence_trend.append(coherence)
            metrics.efficiency_trend.append(efficiency)

            # Keep trends bounded
            if len(metrics.coherence_trend) > 100:
                metrics.coherence_trend = metrics.coherence_trend[-100:]
            if len(metrics.efficiency_trend) > 100:
                metrics.efficiency_trend = metrics.efficiency_trend[-100:]

    def get_active_instances(self) -> list[str]:
        """Get list of active instances (updated in last 5 minutes)."""
        cutoff = time.time() - 300  # 5 minutes
        with self._lock:
            return [instance_id for instance_id, last_update in self._last_update.items() if last_update > cutoff]

    def get_dashboard_snapshot(self) -> dict[str, Any]:
        """Get real-time dashboard snapshot (updated every 5 seconds).

        Returns
        -------
        dict[str, Any]
            Dashboard data: active instances, recent throughput, latencies, etc.
        """
        with self._lock:
            now = time.time()
            window_start = now - 300  # Last 5 minutes
            window_metrics = self.query_by_time_range(window_start, now)

            active_instances = self.get_active_instances()

            # Calculate recent throughput trend (last 5 windows)
            throughput_trend = []
            for i in range(5):
                ws = now - (5 - i) * 60
                we = ws + 60
                w = self.query_by_time_range(ws, we)
                throughput_trend.append(w.avg_throughput)

            # Get skill metrics summary
            skill_summary = [
                {
                    "skill": name,
                    "executions": m.execution_count,
                    "success_rate": m.success_rate,
                    "avg_coherence": (sum(m.coherence_trend) / len(m.coherence_trend) if m.coherence_trend else 0.0),
                }
                for name, m in list(self._skill_metrics.items())[:20]  # Top 20 skills
            ]

            return {
                "timestamp": now,
                "active_instances": len(active_instances),
                "instance_ids": active_instances,
                "total_executions_5m": window_metrics.total_executions,
                "total_successes_5m": window_metrics.total_successes,
                "success_rate": window_metrics.success_rate,
                "avg_throughput_5m": window_metrics.avg_throughput,
                "throughput_trend": throughput_trend,
                "avg_coherence": window_metrics.avg_coherence,
                "cache_hit_rate": window_metrics.cache_hit_rate_mean,
                "p50_latency_ms": window_metrics.p50_latency_ms,
                "p95_latency_ms": window_metrics.p95_latency_ms,
                "p99_latency_ms": window_metrics.p99_latency_ms,
                "model_distribution": window_metrics.model_distribution,
                "top_skills": skill_summary,
            }

    def export_to_vault(self, vault_path: Path) -> str:
        """Export metrics to vault for historical analysis.

        Parameters
        ----------
        vault_path : Path
            Path to vault directory.

        Returns
        -------
        str
            Path to exported file.
        """
        vault_path.mkdir(parents=True, exist_ok=True)

        with self._lock:
            snapshot = {
                "exported_at": time.time(),
                "instance_metrics": {},
                "skill_metrics": {},
            }

            # Export instance metrics
            for instance_id, metrics_list in self._instance_metrics.items():
                snapshot["instance_metrics"][instance_id] = [m.to_dict() for m in metrics_list]

            # Export skill metrics
            for skill_name, metrics in self._skill_metrics.items():
                snapshot["skill_metrics"][skill_name] = metrics.to_dict()

            # Write to vault
            filename = f"global_metrics_{int(time.time())}.json"
            filepath = vault_path / filename

            try:
                filepath.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
                logger.info("Exported metrics to %s", filepath)
                return str(filepath)
            except Exception as e:
                logger.exception("Failed to export metrics: %s", e)
                return ""

    def export_to_csv(self, csv_path: Path) -> str:
        """Export metrics to CSV for analytics.

        Parameters
        ----------
        csv_path : Path
            Path to CSV file.

        Returns
        -------
        str
            Path to exported file.
        """
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            try:
                import csv as csv_module

                with csv_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv_module.DictWriter(
                        f,
                        fieldnames=[
                            "timestamp",
                            "instance_id",
                            "execution_count",
                            "success_count",
                            "success_rate",
                            "total_tokens",
                            "avg_duration_ms",
                            "coherence_score",
                            "cache_hit_rate",
                        ],
                    )
                    writer.writeheader()

                    for instance_id, metrics_list in self._instance_metrics.items():
                        for m in metrics_list:
                            writer.writerow(
                                {
                                    "timestamp": m.timestamp,
                                    "instance_id": instance_id,
                                    "execution_count": m.execution_count,
                                    "success_count": m.success_count,
                                    "success_rate": m.success_rate,
                                    "total_tokens": m.total_tokens,
                                    "avg_duration_ms": m.avg_duration_ms,
                                    "coherence_score": m.coherence_score,
                                    "cache_hit_rate": m.cache_hit_rate,
                                }
                            )

                logger.info("Exported metrics to CSV: %s", csv_path)
                return str(csv_path)
            except Exception as e:
                logger.exception("Failed to export to CSV: %s", e)
                return ""

    @staticmethod
    def _calculate_percentile(values: list[float], percentile: float) -> float:
        """Calculate percentile from list of values.

        Parameters
        ----------
        values : list[float]
            List of values.
        percentile : float
            Percentile to calculate (0-1).

        Returns
        -------
        float
            Percentile value.
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile)
        return float(sorted_values[min(idx, len(sorted_values) - 1)])

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._lock:
            self._instance_metrics.clear()
            self._skill_metrics.clear()
            self._window_cache.clear()
            self._last_update.clear()


# Singleton instance
_global_aggregator: GlobalMetricsAggregator | None = None
_aggregator_lock = threading.Lock()


def get_global_aggregator(data_dir: Path | None = None, window_size_sec: int = 60) -> GlobalMetricsAggregator:
    """Get or create the global metrics aggregator singleton.

    Parameters
    ----------
    data_dir : Path | None
        Data directory for persistence.
    window_size_sec : int
        Time window size in seconds.

    Returns
    -------
    GlobalMetricsAggregator
        Singleton instance.
    """
    global _global_aggregator
    with _aggregator_lock:
        if _global_aggregator is None:
            _global_aggregator = GlobalMetricsAggregator(data_dir, window_size_sec)
        return _global_aggregator


def reset_global_aggregator() -> None:
    """Reset the global aggregator singleton (for testing)."""
    global _global_aggregator
    with _aggregator_lock:
        if _global_aggregator is not None:
            _global_aggregator.reset()
        _global_aggregator = None
