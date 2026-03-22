"""Unified data models for compound engineering.

Consolidated from scattered dataclasses across the module.
All core execution concepts in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
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


# ============================================================================
# Legacy Compatibility Models (for backward compatibility)
# These preserve old API while new code uses simplified models above
# ============================================================================


@dataclass
class ThermodynamicState:
    """Thermodynamic state (legacy compatibility)."""

    entropy: float = 0.0
    energy: float = 0.0
    free_energy: float = 0.0
    temperature: float = 0.0
    entropy_production_rate: float = 0.0
    susceptibility: float = 0.0
    heat_capacity: float = 0.0
    order_parameter: float = 0.0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ConstraintType(Enum):
    """Legacy constraint type enum."""

    LATENCY = auto()
    TOKENS = auto()
    QUALITY = auto()
    COST = auto()
    SCOPE = auto()


@dataclass
class ExecutionConstraint:
    """Legacy constraint - maps to new config."""

    type: ConstraintType
    value: float
    unit: str
    is_hard: bool = True

    def __repr__(self) -> str:
        """String representation."""
        return f"Constraint({self.type.value}: {self.value}{self.unit}, hard={self.is_hard})"


@dataclass
class SuccessCriterion:
    """Legacy success criterion."""

    description: str
    metric_name: str
    threshold: float
    is_explicit: bool = False

    def __repr__(self) -> str:
        """String representation."""
        return f"Criterion({self.description}: {self.metric_name}>={self.threshold}, explicit={self.is_explicit})"


@dataclass
class HumanRequest:
    """Structured representation of human request.

    Attributes:
        raw_text: Original request text
        intent: Inferred IntentType
        intent_confidence: 0.0-1.0 confidence in intent classification
        constraints: List of ExecutionConstraints
        criteria: List of SuccessCriteria
        scope_includes: Task scope items that must be included
        scope_excludes: Task scope items to exclude
    """

    raw_text: str
    intent: IntentType = IntentType.UNKNOWN
    intent_confidence: float = 0.0
    constraints: list[ExecutionConstraint] = field(default_factory=list)
    criteria: list[SuccessCriterion] = field(default_factory=list)
    scope_includes: list[str] = field(default_factory=list)
    scope_excludes: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Request(intent={self.intent.value}, "
            f"confidence={self.intent_confidence:.2f}, "
            f"{len(self.constraints)} constraints, {len(self.criteria)} criteria)"
        )


@dataclass
class DriftSignal:
    """Legacy drift signal - now part of AnalysisReport."""

    signal_type: str
    severity: float
    description: str
    metadata: dict[str, Any] | None = None


@dataclass
class ConstraintViolation:
    """Legacy constraint violation."""

    constraint: ExecutionConstraint
    requested_value: float
    actual_value: float
    severity: float

    def __repr__(self) -> str:
        """String representation."""
        return f"Violation({self.constraint.type.value}: requested={self.requested_value}, actual={self.actual_value})"


@dataclass
class CriterionFailure:
    """Legacy criterion failure."""

    criterion: SuccessCriterion
    expected_value: float
    actual_value: float
    gap: float

    def __repr__(self) -> str:
        """String representation."""
        return f"Failure({self.criterion.metric_name}: expected={self.expected_value}, actual={self.actual_value})"


@dataclass
class ExecutionAlignment:
    """Legacy execution alignment - now AnalysisReport."""

    intent_match_score: float
    constraint_satisfaction: float
    criteria_satisfaction: float
    misalignment_score: float
    violations: list[ConstraintViolation] | None = None
    failures: list[CriterionFailure] | None = None
    drift_signals: list[DriftSignal] | None = None
    issues: list[str] | None = None
    recommendations: list[str] | None = None
    should_retry: bool = False


@dataclass
class HumanRequest:
    """Legacy human request."""

    raw_text: str
    intent: IntentType = IntentType.UNKNOWN
    intent_confidence: float = 0.0
    constraints: list[ExecutionConstraint] | None = None
    criteria: list[SuccessCriterion] | None = None
    scope_includes: list[str] | None = None
    scope_excludes: list[str] | None = None


@dataclass
class SessionCheckpoint:
    """Checkpoint for session recovery."""

    session_id: str
    timestamp: datetime
    task: Task
    results: list[ExecutionResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": str(self.timestamp),
            "task_id": self.task.id if hasattr(self.task, "id") else str(self.task),
            "results_count": len(self.results),
            "metadata": self.metadata,
        }


@dataclass
class CompoundCycleResult:
    """Legacy cycle result - mapped to new."""

    skill_name: str = ""
    input_text: str = ""
    execution_output: str = ""
    execution_tokens: int = 0
    execution_duration_ms: float = 0.0
    compound_score_delta: float = 0.0
    patterns: list[str] | None = None
    refinements_applied: int = 0
    version_before: str = ""
    version_after: str = ""
    model_usage: dict[str, int] | None = None


@dataclass
class CompoundCycleReport:
    """Legacy cycle report."""

    skill_name: str = ""
    cycles: list[CompoundCycleResult] | None = None
    total_cycles: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    total_refinements: int = 0
    final_compound_score_delta: float = 0.0
