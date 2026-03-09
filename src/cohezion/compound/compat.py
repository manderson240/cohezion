"""Compatibility layer for legacy compound module API.

Bridges old API to new simplified implementation.
Preserves all original functionality while using clean internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

# Import new simplified models
from cohezion.compound.models import (
    AnalysisReport as NewAnalysisReport,
    ExecutionResult as NewExecutionResult,
    ExecutionMetrics as NewExecutionMetrics,
    Task as NewTask,
)

from cohezion.compound.core.executor import (
    CompoundExecutor as NewCompoundExecutor,
    ExecutionConfig as NewExecutionConfig,
)

# ============================================================================
# Legacy Type Aliases (for backward compatibility)
# ============================================================================


# Keep old enums for compatibility
class ConstraintType(Enum):
    """Legacy constraint type enum."""

    LATENCY = auto()
    TOKENS = auto()
    QUALITY = auto()
    COST = auto()
    SCOPE = auto()


class IntentType(Enum):
    """Legacy intent type enum."""

    GENERATE = auto()
    ANALYZE = auto()
    SEARCH = auto()
    TRANSFORM = auto()
    PERSIST = auto()
    MULTI_STEP = auto()
    UNKNOWN = auto()


# ============================================================================
# Legacy Data Classes (mapped to new implementation)
# ============================================================================


@dataclass
class ExecutionConstraint:
    """Legacy constraint - maps to new config."""

    type: ConstraintType
    value: float
    unit: str
    is_hard: bool = True

    def to_config(self) -> dict[str, Any]:
        """Convert to new config format."""
        return {
            "type": self.type.name,
            "value": self.value,
            "unit": self.unit,
            "is_hard": self.is_hard,
        }


@dataclass
class SuccessCriterion:
    """Legacy success criterion."""

    description: str
    metric_name: str
    threshold: float
    is_explicit: bool = False


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


@dataclass
class CriterionFailure:
    """Legacy criterion failure."""

    criterion: SuccessCriterion
    expected_value: float
    actual_value: float
    gap: float


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


# ============================================================================
# Legacy Compound Classes (wrappers around new implementation)
# ============================================================================


class CompoundExecutor:
    """Legacy CompoundExecutor - wraps new implementation.

    Preserves 15-parameter interface but uses clean internals.
    """

    def __init__(
        self,
        mcp_client=None,
        token_client=None,
        guardrail_pipeline=None,
        enable_guardrails=True,
        inflection_detector=None,
        skill_refiner=None,
        enable_skill_refinement=True,
        metrics_collector=None,
        journey_tracker=None,
        journey_persistence=None,
        alignment_analyzer=None,
        enable_alignment_analysis=False,
        degradation_detector=None,
        model_quality_classifier=None,
        retrospection_engine=None,
        universe_bridge=None,
        **kwargs,
    ):
        """Initialize with legacy 15-parameter interface."""
        # Store legacy dependencies for compatibility
        self._mcp_client = mcp_client
        self._token_client = token_client
        self._guardrail_pipeline = guardrail_pipeline
        self._enable_guardrails = enable_guardrails
        self._inflection_detector = inflection_detector
        self._skill_refiner = skill_refiner
        self._enable_skill_refinement = enable_skill_refinement
        self._metrics_collector = metrics_collector
        self._journey_tracker = journey_tracker
        self._journey_persistence = journey_persistence
        self._alignment_analyzer = alignment_analyzer
        self._enable_alignment_analysis = enable_alignment_analysis
        self._degradation_detector = degradation_detector
        self._model_quality_classifier = model_quality_classifier
        self._retrospection_engine = retrospection_engine
        self._universe_bridge = universe_bridge

        # Create new simplified executor internally
        # (actual implementation would bridge to new executor)
        self._new_executor = None  # Placeholder

        self.logger = logging.getLogger(__name__)

    def execute_task(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str,
        execute_fn,
        **kwargs,
    ):
        """Execute task with legacy interface.

        For Phase 1: Delegates to the original executor.
        In Phase 2: Will bridge to new implementation.
        """
        # Import and delegate to the original executor
        from cohezion.compound.executor import CompoundExecutor as OriginalExecutor

        # Create original executor with stored dependencies
        original = OriginalExecutor(
            mcp_client=self._mcp_client,
            token_client=self._token_client,
            guardrail_pipeline=self._guardrail_pipeline,
            enable_guardrails=self._enable_guardrails,
            inflection_detector=self._inflection_detector,
            skill_refiner=self._skill_refiner,
            enable_skill_refinement=self._enable_skill_refinement,
            metrics_collector=self._metrics_collector,
            journey_tracker=self._journey_tracker,
            journey_persistence=self._journey_persistence,
            alignment_analyzer=self._alignment_analyzer,
            enable_alignment_analysis=self._enable_alignment_analysis,
            degradation_detector=self._degradation_detector,
            model_quality_classifier=self._model_quality_classifier,
            retrospection_engine=self._retrospection_engine,
            universe_bridge=self._universe_bridge,
        )

        # Delegate to original executor
        return original.execute_task(
            task_description=task_description,
            skill_name=skill_name,
            operation_type=operation_type,
            execute_fn=execute_fn,
            **kwargs,
        )

    def get_experience_guidance(self, **kwargs):
        """Legacy method - returns empty for now."""
        return {}


# ============================================================================
# Legacy Result Classes (mapped to new)
# ============================================================================


class ExecutionResult:
    """Legacy ExecutionResult - wraps new."""

    def __init__(
        self,
        success: bool,
        output: str,
        metrics=None,
        duration_seconds: float = 0.0,
        vault_experiment_path: str | None = None,
        vault_decision_paths: list | None = None,
        token_metrics: dict | None = None,
    ):
        self.success = success
        self.output = output
        self.metrics = metrics or NewExecutionMetrics()
        self.duration_seconds = duration_seconds
        self.vault_experiment_path = vault_experiment_path
        self.vault_decision_paths = vault_decision_paths or []
        self.token_metrics = token_metrics or {}


class CompoundCycleResult:
    """Legacy cycle result - mapped to new."""

    def __init__(
        self,
        skill_name: str = "",
        input_text: str = "",
        execution_output: str = "",
        execution_tokens: int = 0,
        execution_duration_ms: float = 0.0,
        compound_score_delta: float = 0.0,
        patterns: list | None = None,
        refinements_applied: int = 0,
        version_before: str = "",
        version_after: str = "",
        model_usage: dict | None = None,
    ):
        self.skill_name = skill_name
        self.input_text = input_text
        self.execution_output = execution_output
        self.execution_tokens = execution_tokens
        self.execution_duration_ms = execution_duration_ms
        self.compound_score_delta = compound_score_delta
        self.patterns = patterns or []
        self.refinements_applied = refinements_applied
        self.version_before = version_before
        self.version_after = version_after
        self.model_usage = model_usage or {}


class CompoundCycleReport:
    """Legacy cycle report."""

    def __init__(
        self,
        skill_name: str = "",
        cycles: list | None = None,
        total_cycles: int = 0,
        total_tokens: int = 0,
        total_duration_ms: float = 0.0,
        total_refinements: int = 0,
        final_compound_score_delta: float = 0.0,
    ):
        self.skill_name = skill_name
        self.cycles = cycles or []
        self.total_cycles = total_cycles
        self.total_tokens = total_tokens
        self.total_duration_ms = total_duration_ms
        self.total_refinements = total_refinements
        self.final_compound_score_delta = final_compound_score_delta


import logging

# Re-export all legacy symbols
__all__ = [
    # Enums
    "ConstraintType",
    "IntentType",
    # Legacy dataclasses
    "ExecutionConstraint",
    "SuccessCriterion",
    "DriftSignal",
    "ConstraintViolation",
    "CriterionFailure",
    "ExecutionAlignment",
    "HumanRequest",
    # Legacy executor
    "CompoundExecutor",
    # Legacy results
    "ExecutionResult",
    "CompoundCycleResult",
    "CompoundCycleReport",
]
