"""Unified metrics collection across all subsystems.

Aggregates metrics from:
- Guardrail pipeline (blocks, latency)
- Semantic cache (hit rates by tier)
- Token efficiency (token usage, model routing)
- Session management (checkpoints, resumptions)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class InferenceMetrics:
    """Comprehensive metrics for an inference operation.

    Tracks:
        - Guardrail operations (checks, blocks, sanitizations)
        - Cache performance (hits by tier, misses)
        - Execution (tokens, duration, model usage)
        - Session management (checkpoints, resumptions)
        - Resources (memory, concurrency waits)
    """

    # Guardrails
    guardrail_checks: int = 0
    guardrail_blocks: int = 0
    guardrail_sanitizations: int = 0
    guardrail_latency_ms: float = 0.0

    # Cache
    cache_l1_hits: int = 0
    cache_l2_hits: int = 0
    cache_l3_hits: int = 0
    cache_misses: int = 0

    # Execution
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_usage: dict[str, int] = field(default_factory=dict)

    # Session
    checkpoints_created: int = 0
    session_resumptions: int = 0

    # Resources
    peak_memory_gb: float = 0.0
    concurrency_waits: int = 0

    # Cost tracking (new in cost optimization initiative)
    total_cost_usd: float = 0.0
    cost_breakdown: dict[str, float] = field(default_factory=dict)
    budget_utilization_pct: float = 0.0

    @property
    def total_cache_hit_rate(self) -> float:
        """Combined L1+L2+L3 hit rate."""
        total_cache_ops = self.cache_l1_hits + self.cache_l2_hits + self.cache_l3_hits + self.cache_misses
        if total_cache_ops == 0:
            return 0.0
        return (self.cache_l1_hits + self.cache_l2_hits + self.cache_l3_hits) / total_cache_ops * 100

    @property
    def l1_cache_hit_rate(self) -> float:
        """L1 cache hit rate percentage."""
        total_cache_ops = self.cache_l1_hits + self.cache_l2_hits + self.cache_l3_hits + self.cache_misses
        if total_cache_ops == 0:
            return 0.0
        return self.cache_l1_hits / total_cache_ops * 100

    @property
    def l2_cache_hit_rate(self) -> float:
        """L2 cache hit rate percentage."""
        total_cache_ops = self.cache_l1_hits + self.cache_l2_hits + self.cache_l3_hits + self.cache_misses
        if total_cache_ops == 0:
            return 0.0
        return self.cache_l2_hits / total_cache_ops * 100

    @property
    def guardrail_block_rate(self) -> float:
        """Percentage of requests blocked by guardrails."""
        total_guardrail_ops = self.guardrail_checks + self.guardrail_blocks + self.guardrail_sanitizations
        if total_guardrail_ops == 0:
            return 0.0
        return self.guardrail_blocks / total_guardrail_ops * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "guardrail_checks": self.guardrail_checks,
            "guardrail_blocks": self.guardrail_blocks,
            "guardrail_sanitizations": self.guardrail_sanitizations,
            "guardrail_latency_ms": self.guardrail_latency_ms,
            "cache_l1_hits": self.cache_l1_hits,
            "cache_l2_hits": self.cache_l2_hits,
            "cache_l3_hits": self.cache_l3_hits,
            "cache_misses": self.cache_misses,
            "total_cache_hit_rate": self.total_cache_hit_rate,
            "l1_cache_hit_rate": self.l1_cache_hit_rate,
            "l2_cache_hit_rate": self.l2_cache_hit_rate,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "model_usage": self.model_usage,
            "checkpoints_created": self.checkpoints_created,
            "session_resumptions": self.session_resumptions,
            "peak_memory_gb": self.peak_memory_gb,
            "concurrency_waits": self.concurrency_waits,
            "guardrail_block_rate": self.guardrail_block_rate,
            "total_cost_usd": self.total_cost_usd,
            "cost_breakdown": self.cost_breakdown,
            "budget_utilization_pct": self.budget_utilization_pct,
        }


class UnifiedMetricsCollector:
    """Collect and aggregate metrics from all subsystems.

    Provides:
        - Per-operation metrics
        - Aggregate statistics
        - Trend analysis
        - Health checks
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.current_metrics = InferenceMetrics()
        self.history: list[InferenceMetrics] = []
        self.start_time = time.time()

    def record_guardrail_action(self, action: str, latency_ms: float = 0.0) -> None:
        """Record guardrail action.

        Args:
            action: "allow", "block", or "sanitize"
            latency_ms: Latency in milliseconds
        """
        self.current_metrics.guardrail_checks += 1
        if action == "block":
            self.current_metrics.guardrail_blocks += 1
        elif action == "sanitize":
            self.current_metrics.guardrail_sanitizations += 1
        self.current_metrics.guardrail_latency_ms += latency_ms

    def record_cache_hit(self, tier: int) -> None:
        """Record cache hit.

        Args:
            tier: Cache tier (1, 2, or 3)
        """
        if tier == 1:
            self.current_metrics.cache_l1_hits += 1
        elif tier == 2:
            self.current_metrics.cache_l2_hits += 1
        elif tier == 3:
            self.current_metrics.cache_l3_hits += 1

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.current_metrics.cache_misses += 1

    def record_execution(self, tokens: int, duration_ms: float, model: str = "unknown") -> None:
        """Record execution metrics.

        Args:
            tokens: Number of tokens used
            duration_ms: Execution duration in milliseconds
            model: Model name
        """
        self.current_metrics.total_tokens += tokens
        self.current_metrics.total_duration_ms += duration_ms
        self.current_metrics.model_usage[model] = self.current_metrics.model_usage.get(model, 0) + tokens

    def record_checkpoint(self) -> None:
        """Record checkpoint creation."""
        self.current_metrics.checkpoints_created += 1

    def record_resumption(self) -> None:
        """Record session resumption."""
        self.current_metrics.session_resumptions += 1

    def record_memory_peak(self, memory_gb: float) -> None:
        """Record peak memory usage.

        Args:
            memory_gb: Memory in gigabytes
        """
        self.current_metrics.peak_memory_gb = max(self.current_metrics.peak_memory_gb, memory_gb)

    def record_concurrency_wait(self) -> None:
        """Record concurrency wait event."""
        self.current_metrics.concurrency_waits += 1

    def get_current_metrics(self) -> InferenceMetrics:
        """Get current metrics snapshot."""
        return InferenceMetrics(
            guardrail_checks=self.current_metrics.guardrail_checks,
            guardrail_blocks=self.current_metrics.guardrail_blocks,
            guardrail_sanitizations=self.current_metrics.guardrail_sanitizations,
            guardrail_latency_ms=self.current_metrics.guardrail_latency_ms,
            cache_l1_hits=self.current_metrics.cache_l1_hits,
            cache_l2_hits=self.current_metrics.cache_l2_hits,
            cache_l3_hits=self.current_metrics.cache_l3_hits,
            cache_misses=self.current_metrics.cache_misses,
            total_tokens=self.current_metrics.total_tokens,
            total_duration_ms=self.current_metrics.total_duration_ms,
            model_usage=dict(self.current_metrics.model_usage),
            checkpoints_created=self.current_metrics.checkpoints_created,
            session_resumptions=self.current_metrics.session_resumptions,
            peak_memory_gb=self.current_metrics.peak_memory_gb,
            concurrency_waits=self.current_metrics.concurrency_waits,
        )

    def reset_current_metrics(self) -> None:
        """Reset current metrics and save to history."""
        self.history.append(self.current_metrics)
        self.current_metrics = InferenceMetrics()

    def get_aggregate_metrics(self) -> dict[str, Any]:
        """Get aggregate statistics across all recorded operations."""
        all_metrics = [self.current_metrics, *self.history]

        total_tokens = sum(m.total_tokens for m in all_metrics)
        total_duration_ms = sum(m.total_duration_ms for m in all_metrics)
        total_operations = len(all_metrics)

        return {
            "total_operations": total_operations,
            "aggregate_tokens": total_tokens,
            "aggregate_duration_ms": total_duration_ms,
            "avg_tokens_per_operation": (total_tokens / total_operations if total_operations > 0 else 0),
            "avg_duration_ms": (total_duration_ms / total_operations if total_operations > 0 else 0),
            "total_guardrail_blocks": sum(m.guardrail_blocks for m in all_metrics),
            "total_cache_hits": sum(m.cache_l1_hits + m.cache_l2_hits + m.cache_l3_hits for m in all_metrics),
            "total_cache_misses": sum(m.cache_misses for m in all_metrics),
            "aggregate_cache_hit_rate": (
                sum(m.cache_l1_hits + m.cache_l2_hits + m.cache_l3_hits for m in all_metrics)
                / (sum(m.cache_l1_hits + m.cache_l2_hits + m.cache_l3_hits + m.cache_misses for m in all_metrics) or 1)
                * 100
            ),
            "uptime_seconds": time.time() - self.start_time,
        }


# Global metrics collector instance
_global_metrics_collector = UnifiedMetricsCollector()


def get_metrics_collector() -> UnifiedMetricsCollector:
    """Get global metrics collector instance."""
    return _global_metrics_collector
