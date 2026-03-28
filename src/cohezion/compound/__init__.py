"""Compound engineering system for iterative AI refinement.

Integrates skill execution, knowledge persistence (vault), and experience-guided loops.
"""

from __future__ import annotations

from cohezion.compound.analytics.engine import (
    AnalysisConfig,
    ExecutionAnalyzer,
    SimpleAnalyzer,
)
from cohezion.compound.analytics.metrics import (
    MetricsCollector,
    MetricsSnapshot,
    SimpleMetrics,
)
from cohezion.compound.batch_executor import (
    BatchableExecutor,
    BatchExecutorFactory,
)
from cohezion.compound.compat import (
    CompoundCycleReport,
    CompoundCycleResult,
    CompoundExecutor,
    ExecutionResult,
)
from cohezion.compound.core.batch_processor import (
    BatchProcessor,
    BatchResult,
    SimpleBatch,
)
from cohezion.compound.core.executor import (
    ExecutionConfig,
    execute_simple,
)
from cohezion.compound.exp_persistence.journey import JourneyPersistence
from cohezion.compound.exp_persistence.vault import (
    ExecutionContext,
    VaultLogger,
)
from cohezion.compound.feedback_loop import (
    CompoundFeedbackLoop,
    CompoundFeedbackLoopFactory,
    FeedbackLoopResult,
    RetryAttempt,
    RetryStrategy,
)
from cohezion.compound.global_metrics_aggregator import (
    GlobalMetricsAggregator,
    InstanceMetrics,
    SkillMetrics,
    TimeWindowMetrics,
    get_global_aggregator,
    reset_global_aggregator,
)
from cohezion.compound.hardware_monitor import (
    HardwareMetrics,
    HardwareMonitor,
    get_hardware_monitor,
)
from cohezion.compound.inflection_detector import (
    InflectionDetector,
    InflectionDetectorFactory,
    Severity,
)
from cohezion.compound.intake_specialist import (
    IntakeGreeting,
    IntakeSpecialist,
)
from cohezion.compound.intent_classifier import IntentClassifier
from cohezion.compound.journey_tracker import (
    Journey,
    JourneyTracker,
    JourneyTrackerFactory,
    OperationType,
    TrajectoryPoint,
)
from cohezion.compound.metrics import (
    CompoundMetricsCollector,
    get_collector,
    reset_collector,
)
from cohezion.compound.metrics_persistence import MetricsPersistence
from cohezion.compound.model_quality_classifier import (
    ActionRecommendation,
    ExecutionRecord,
    FailureMode,
    ModelQualityClassifier,
    QualityForecast,
    QualityPredictor,
    RecommendedAction,
)
from cohezion.compound.models import (
    AnalysisReport,
    BatchConfig,
    CompoundCycleReport,
    CompoundCycleResult,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionStatus,
    Task,
)
from cohezion.compound.persistence.vault import (
    PersistenceConfig,
    SessionPersister,
    SimplePersistence,
    VaultPersister,
)
from cohezion.compound.prompt_optimizer import PromptOptimizer
from cohezion.compound.request_alignment_analyzer import (
    ConstraintType,
    ConstraintViolation,
    CriterionFailure,
    DriftSignal,
    ExecutionAlignment,
    ExecutionConstraint,
    HumanRequest,
    IntentType,
    SuccessCriterion,
)
from cohezion.compound.skills.selector import (
    SimpleSkills,
    SkillMatch,
    SkillRefiner,
    SkillSelector,
)


try:
    from cohezion.compound.executor import ExecutorFactory
except ImportError:
    ExecutorFactory = None  # type: ignore[assignment]

try:
    from cohezion.compound.core.executor import CompoundExecutor as NewCompoundExecutor
except ImportError:
    NewCompoundExecutor = None  # type: ignore[assignment]

__version__ = "2.0.0"


def get_version() -> str:
    return __version__


__all__ = [
    "AnalysisConfig",
    "AnalysisReport",
    "BatchConfig",
    "BatchProcessor",
    "BatchResult",
    "CompoundCycleReport",
    "CompoundCycleResult",
    "CompoundExecutor",
    "CompoundMetricsCollector",
    "ConstraintType",
    "ConstraintViolation",
    "CriterionFailure",
    "DriftSignal",
    "ExecutionAlignment",
    "ExecutionAnalyzer",
    "ExecutionConfig",
    "ExecutionConstraint",
    "ExecutionContext",
    "ExecutionMetrics",
    "ExecutionRecord",
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutorFactory",
    "FeedbackLoopResult",
    "GlobalMetricsAggregator",
    "HardwareMetrics",
    "HardwareMonitor",
    "HumanRequest",
    "InflectionDetector",
    "InflectionDetectorFactory",
    "IntentClassifier",
    "IntentType",
    "Journey",
    "JourneyPersistence",
    "JourneyTracker",
    "JourneyTrackerFactory",
    "MetricsCollector",
    "MetricsSnapshot",
    "ModelQualityClassifier",
    "NewCompoundExecutor",
    "OperationType",
    "PromptOptimizer",
    "QualityForecast",
    "RecommendedAction",
    "RetryAttempt",
    "RetryStrategy",
    "Severity",
    "SimpleAnalyzer",
    "SimpleBatch",
    "SimpleMetrics",
    "SimplePersistence",
    "SimpleSkills",
    "SkillMatch",
    "SkillRefiner",
    "SkillSelector",
    "SuccessCriterion",
    "Task",
    "TimeWindowMetrics",
    "TrajectoryPoint",
    "VaultLogger",
    "VaultPersister",
    "__version__",
    "execute_simple",
    "get_collector",
    "get_global_aggregator",
    "get_hardware_monitor",
    "get_version",
    "reset_collector",
    "reset_global_aggregator",
]
