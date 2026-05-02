"""Compound engineering system for iterative AI refinement.

Integrates skill execution, knowledge persistence (vault), and experience-guided loops.
Phase 1: Compatibility layer with simplified internals
"""

# ============================================================================
# Compatibility Layer (Phase 1) - Preserves old API
# ============================================================================

# ============================================================================
# New Simplified Analytics (Phase 1)
# ============================================================================
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
from cohezion.compound.compat import (
    CompoundCycleReport,
    CompoundCycleResult,
    CompoundExecutor,
    ExecutionResult,
    ExecutorFactory,
)
from cohezion.compound.compat import (
    ExecutionResult as LegacyExecutionResult,
)
from cohezion.compound.core.batch_processor import (
    BatchProcessor,
    BatchResult,
    SimpleBatch,
)
from cohezion.compound.core.executor import (
    CompoundExecutor as NewCompoundExecutor,
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

# ============================================================================
# New Simplified Core (Phase 1) - Clean implementations
# ============================================================================
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

# ============================================================================
# New Simplified Persistence (Phase 1)
# ============================================================================
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

# ============================================================================
# New Simplified Skills (Phase 1)
# ============================================================================
from cohezion.compound.skills.selector import (
    SimpleSkills,
    SkillMatch,
    SkillRefiner,
    SkillSelector,
)


# ============================================================================
# New Simplified Analytics (Phase 1)
# ============================================================================



# ============================================================================
# New Simplified Skills (Phase 1)
# ============================================================================


# ============================================================================
# New Simplified Persistence (Phase 1)
# ============================================================================



# ============================================================================
# Version Info
# ============================================================================

__version__ = "2.0.0-simplified"


def get_version() -> str:
    """Get compound module version."""
    return __version__


# ============================================================================
# Exports
# ============================================================================

# ============================================================================
# Version Info
# ============================================================================

__version__ = "2.0.0-simplified"


def get_version() -> str:
    """Get compound module version."""
    return __version__


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # New analytics
    "AnalysisConfig",
    # New models
    "AnalysisReport",
    "BatchConfig",
    "BatchProcessor",
    "BatchResult",
    # Compatibility layer (old API)
    "CompoundCycleReport",
    "CompoundCycleResult",
    "CompoundExecutor",
    "ConstraintType",
    "ConstraintViolation",
    "CriterionFailure",
    "DriftSignal",
    "EvolutionDirective",
    "EvolutionRoundResult",
    "EvolutionTrainingConfig",
    "EvolutionTrainingExporter",
    "EvolutionTrainingPipeline",
    "EvolutionTrainingSignalGenerator",
    "EvolutionTrajectory",
    "ExecutionAlignment",
    "ExecutionAnalyzer",
    "ExecutionConfig",
    "ExecutionConstraint",
    "ExecutionContext",
    "ExecutionMetrics",
    "ExecutionResult",
    "ExecutionStatus",
    "HumanRequest",
    "IntentType",
    "LegacyExecutionResult",
    "MetricsCollector",
    "MetricsSnapshot",
    # New core
    "NewCompoundExecutor",
    # New persistence
    "PersistenceConfig",
    "SessionPersister",
    "SimpleAnalyzer",
    "SimpleBatch",
    "SimpleMetrics",
    "SimplePersistence",
    "SimpleSkills",
    # New skills
    "SkillMatch",
    "SkillRefiner",
    "SkillSelector",
    "SuccessCriterion",
    "Task",
    "VaultPersister",
    # Version
    "__version__",
    "execute_simple",
    "get_version",
]
