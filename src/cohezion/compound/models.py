"""Unified data models for compound engineering.

Consolidated from scattered dataclasses across the module.
All core execution concepts in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any


class ExecutionStatus(Enum):
    """Unified execution status."""

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()


class IntentType(Enum):
    """Classification of human intent/request type."""

    GENERATE = auto()
    ANALYZE = auto()
    SEARCH = auto()
    TRANSFORM = auto()
    PERSIST = auto()
    MULTI_STEP = auto()
    UNKNOWN = auto()


@dataclass
class ExecutionMetrics:
    """Consolidated metrics from 4 separate classes."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0
    coherence: float = 0.0
    quality_score: float | None = None
    cache_hit_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "duration_seconds": self.duration_seconds,
            "coherence": self.coherence,
            "quality_score": self.quality_score,
            "cache_hit_rate": self.cache_hit_rate,
        }


@dataclass
class ExecutionResult:
    """Unified execution result."""

    success: bool
    output: str
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    vault_path: str | None = None
    checkpoint_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    @property
    def failed(self) -> bool:
        return not self.success

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "metrics": self.metrics.to_dict(),
            "vault_path": self.vault_path,
        }


@dataclass
class Task:
    """Unified task definition."""

    id: str
    description: str
    skill_name: str
    operation_type: str
    context: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    timeout_seconds: float = 120.0
    priority: int = 5
    intent: IntentType = IntentType.UNKNOWN

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class ExecutionContext:
    """Execution context passed through pipeline."""

    session_id: str
    task: Task
    attempt_number: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    previous_results: list[ExecutionResult] = field(default_factory=list)
    checkpoint_data: dict[str, Any] = field(default_factory=dict)

    def with_retry(self) -> ExecutionContext:
        """Create context for retry attempt."""
        return ExecutionContext(
            session_id=self.session_id,
            task=self.task,
            attempt_number=self.attempt_number + 1,
            start_time=self.start_time,
            previous_results=self.previous_results,
            checkpoint_data=self.checkpoint_data,
        )


@dataclass
class AnalysisReport:
    """Unified analysis report."""

    anomalies_detected: bool = False
    degradation_detected: bool = False
    quality_issue: bool = False
    suggested_action: str | None = None
    retry_recommended: bool = False
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)

    def has_issues(self) -> bool:
        return self.anomalies_detected or self.degradation_detected or self.quality_issue


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    max_batch_size: int = 10
    optimal_batch_size: int = 5
    max_wait_seconds: float = 30.0
    max_concurrent: int = 4

    def should_batch(self, queue_size: int) -> bool:
        return queue_size >= self.optimal_batch_size


# Type aliases
TaskId = str
SessionId = str
VaultPath = str
