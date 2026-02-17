"""Pydantic models for compound feedback cycle data."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class ExecutionReportLike(Protocol):
    """Protocol satisfied by both ExecutionReport and proxy objects.

    Allows the feedback loop to accept real ExecutionReports from the
    orchestrator or lightweight proxy objects without circular imports.
    """

    @property
    def plan_name(self) -> str: ...

    @property
    def task_results(self) -> list[Any]: ...

    @property
    def total_tokens(self) -> int: ...

    @property
    def total_duration_ms(self) -> float: ...


class CompoundCycleResult(BaseModel):
    """Result of a single compound feedback cycle."""

    skill_name: str
    input_text: str
    execution_output: str = ""
    execution_tokens: int = 0
    execution_duration_ms: float = 0.0
    compound_score_delta: float = 0.0
    patterns: list[str] = []
    refinements_applied: int = 0
    version_before: str = ""
    version_after: str = ""
    model_usage: dict[str, int] = {}


class CompoundCycleReport(BaseModel):
    """Report across multiple compound cycles."""

    skill_name: str
    cycles: list[CompoundCycleResult] = []
    total_cycles: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    total_refinements: int = 0
    final_compound_score_delta: float = 0.0


# ============================================================================
# Request Alignment Models (Phase 5A.6: Intent-aware execution monitoring)
# ============================================================================


class IntentType(Enum):
    """Classification of human intent/request type."""

    GENERATE = "generate"  # Create new content
    ANALYZE = "analyze"  # Review, evaluate, assess
    SEARCH = "search"  # Find, locate, discover
    TRANSFORM = "transform"  # Convert, reformat, extract
    PERSIST = "persist"  # Store, save, record
    MULTI_STEP = "multi_step"  # Sequential operations
    UNKNOWN = "unknown"  # Unclassifiable


class ConstraintType(Enum):
    """Types of execution constraints."""

    LATENCY = "latency"  # Time limit (ms/sec/min)
    TOKENS = "tokens"  # Token budget
    QUALITY = "quality"  # Quality threshold
    COST = "cost"  # Cost limit
    SCOPE = "scope"  # Scope restriction


@dataclass
class ExecutionConstraint:
    """A single constraint on execution.

    Attributes:
        type: ConstraintType (LATENCY, TOKENS, etc.)
        value: Numeric constraint value
        unit: Unit of measurement (ms, tokens, etc.)
        is_hard: True if must be enforced, False if soft preference
    """

    type: ConstraintType
    value: float
    unit: str
    is_hard: bool = True

    def __repr__(self) -> str:
        """String representation."""
        return f"Constraint({self.type.value}: {self.value}{self.unit}, hard={self.is_hard})"


@dataclass
class SuccessCriterion:
    """A single success criterion for the task.

    Attributes:
        description: Human-readable criterion description
        metric_name: Metrics dict key to check (e.g., "coherence")
        threshold: Expected value/score threshold
        is_explicit: True if user explicitly stated it
    """

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
    """Signal indicating execution divergence from request.

    Attributes:
        signal_type: Type of drift (execution_failed, coherence_drop, etc.)
        severity: 0.0-1.0 severity score
        description: Human-readable description
        metadata: Additional context dict
    """

    signal_type: str
    severity: float
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        """String representation."""
        return f"Drift({self.signal_type}: severity={self.severity:.2f})"


@dataclass
class ConstraintViolation:
    """Record of a constraint being violated.

    Attributes:
        constraint: The ExecutionConstraint that was violated
        requested_value: Value that was requested
        actual_value: Actual value achieved
        severity: 0.0-1.0 severity of violation
    """

    constraint: ExecutionConstraint
    requested_value: float
    actual_value: float
    severity: float

    def __repr__(self) -> str:
        """String representation."""
        return f"Violation({self.constraint.type.value}: requested={self.requested_value}, actual={self.actual_value})"


@dataclass
class CriterionFailure:
    """Record of a success criterion not being met.

    Attributes:
        criterion: The SuccessCriterion that failed
        expected_value: Expected metric value
        actual_value: Actual metric value
        gap: How far below threshold
    """

    criterion: SuccessCriterion
    expected_value: float
    actual_value: float
    gap: float

    def __repr__(self) -> str:
        """String representation."""
        return f"Failure({self.criterion.metric_name}: expected={self.expected_value}, actual={self.actual_value})"


@dataclass
class ExecutionAlignment:
    """Complete alignment analysis between request and execution result.

    Attributes:
        intent_match_score: 0.0-1.0 how well operation matched intent
        constraint_satisfaction: 0.0-1.0 how well constraints were met
        criteria_satisfaction: 0.0-1.0 how well success criteria were met
        misalignment_score: 0.0-1.0 overall misalignment (0=perfect, 1=total mismatch)
        violations: List of ConstraintViolations
        failures: List of CriterionFailures
        drift_signals: List of DriftSignals detected
        issues: List of human-readable issue descriptions
        recommendations: List of recommended actions
        should_retry: Whether re-execution is recommended
    """

    intent_match_score: float
    constraint_satisfaction: float
    criteria_satisfaction: float
    misalignment_score: float
    violations: list[ConstraintViolation] = field(default_factory=list)
    failures: list[CriterionFailure] = field(default_factory=list)
    drift_signals: list[DriftSignal] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    should_retry: bool = False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Alignment(misalignment={self.misalignment_score:.2f}, "
            f"intent={self.intent_match_score:.2f}, "
            f"constraints={self.constraint_satisfaction:.2f}, "
            f"criteria={self.criteria_satisfaction:.2f})"
        )
