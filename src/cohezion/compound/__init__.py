"""Compound engineering system for iterative AI refinement.

Integrates skill execution, knowledge persistence (vault), and experience-guided loops.
"""

from cohezion.compound.batch_sizer import (
    BatchExecutionMetrics,
    BatchSizePredictor,
    get_batch_size_predictor,
)
from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader
from cohezion.compound.degradation_detector import (
    AlertSeverity,
    DegradationAlert,
    DegradationDetector,
    MetricBaseline,
)
from cohezion.compound.executor import (
    CompoundExecutor,
    ExecutionResult,
    ExecutorFactory,
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
from cohezion.compound.exp_persistence.journey import JourneyPersistence
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
from cohezion.compound.models import CompoundCycleReport, CompoundCycleResult
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
    RequestAlignmentAnalyzer,
    RequestAlignmentAnalyzerFactory,
    SuccessCriterion,
)
from cohezion.compound.request_cache import RequestCache
from cohezion.compound.skill_consensus_voter import (
    AgentVote,
    ConsensusResult,
    SkillConsensusVoter,
    VotingStrategy,
)
from cohezion.compound.skill_selector import (
    SkillScore,
    SkillSelector,
)
from cohezion.compound.task_queue import (
    QueuedTask,
    TaskPriority,
    TaskQueue,
)
from cohezion.compound.team_executor import (
    AgentTask,
    AgentTaskResult,
    TeamExecutionResult,
    TeamExecutor,
    TeamExecutorFactory,
)
from cohezion.compound.thermodynamic_metrics import (
    PhaseTransition,
    ThermodynamicMetrics,
    ThermodynamicState,
)
from cohezion.compound.topological_persistence import (
    PersistenceDiagram,
    PersistencePair,
    TopologicalPersistence,
    trajectory_persistence_summary,
)
from cohezion.compound.thermal_history_persistence import (
    ThermalTimeSeriesCollector,
    get_thermal_time_series_collector,
    load_jsonl_history,
)
from cohezion.compound.thermal_predictor import (
    ThermalMetrics,
    ThermalTrendAnalyzer,
    get_thermal_trend_analyzer,
)
from cohezion.compound.thermal_trend_predictor import (
    ThermalTimeSeries,
    ThermalTrendPredictor,
    get_thermal_trend_predictor,
)
from cohezion.compound.exp_persistence.vault import (
    ExecutionContext,
    VaultLogger,
)
from cohezion.compound.vault_search_executor import (
    SearchQuery,
    SearchResult,
    VaultSearchExecutor,
    create_vault_search_executor,
)


__all__ = [
    "ActionRecommendation",
    "AgentTask",
    "AgentTaskResult",
    "AgentVote",
    "AlertSeverity",
    "BatchExecutionMetrics",
    "BatchSizePredictor",
    "CachePersistence",
    "CompoundCycleReport",
    "CompoundCycleResult",
    "CompoundExecutor",
    "CompoundFeedbackLoop",
    "CompoundFeedbackLoopFactory",
    "CompoundMetricsCollector",
    "ConsensusResult",
    "ConstraintType",
    "ConstraintViolation",
    "CriterionFailure",
    "DegradationAlert",
    "DegradationDetector",
    "DriftSignal",
    "ExecutionAlignment",
    "ExecutionConstraint",
    "ExecutionContext",
    "ExecutionRecord",
    "ExecutionResult",
    "ExecutorFactory",
    "FailureMode",
    "FeedbackLoopResult",
    "GlobalMetricsAggregator",
    "HardwareMetrics",
    "HardwareMonitor",
    "HumanRequest",
    "InflectionDetector",
    "InflectionDetectorFactory",
    "InstanceMetrics",
    "IntakeGreeting",
    "IntakeSpecialist",
    "IntentClassifier",
    "IntentType",
    "Journey",
    "JourneyPersistence",
    "JourneyTracker",
    "JourneyTrackerFactory",
    "MetricBaseline",
    "MetricsPersistence",
    "ModelQualityClassifier",
    "OperationType",
    "PromptOptimizer",
    "QualityForecast",
    "QualityPredictor",
    "QueuedTask",
    "RecommendedAction",
    "RequestAlignmentAnalyzer",
    "RequestAlignmentAnalyzerFactory",
    "RequestCache",
    "RetryAttempt",
    "RetryStrategy",
    "Severity",
    "SkillConsensusVoter",
    "SkillMetrics",
    "SkillScore",
    "SkillSelector",
    "SuccessCriterion",
    "VotingStrategy",
    "TaskPriority",
    "TaskQueue",
    "TeamExecutionResult",
    "TeamExecutor",
    "TeamExecutorFactory",
    "ThermalMetrics",
    "ThermalTimeSeries",
    "ThermalTimeSeriesCollector",
    "ThermalTrendAnalyzer",
    "ThermalTrendPredictor",
    "TimeWindowMetrics",
    "TrajectoryPoint",
    "VaultLogger",
    "VaultSearchExecutor",
    "SearchQuery",
    "SearchResult",
    "WarmCacheLoader",
    "create_vault_search_executor",
    "PhaseTransition",
    "PersistenceDiagram",
    "PersistencePair",
    "ThermodynamicMetrics",
    "ThermodynamicState",
    "TopologicalPersistence",
    "trajectory_persistence_summary",
    "get_batch_size_predictor",
    "get_collector",
    "get_global_aggregator",
    "get_hardware_monitor",
    "get_thermal_time_series_collector",
    "get_thermal_trend_analyzer",
    "get_thermal_trend_predictor",
    "load_jsonl_history",
    "reset_collector",
    "reset_global_aggregator",
]
