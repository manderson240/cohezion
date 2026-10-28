"""Cohezion Compound Engineering System."""

from __future__ import annotations

import importlib as _importlib
from typing import Any


# --- Lazy public names (PEP 562). See docs/audits/DYNAMIC_MODULARITY_AUDIT_2026-09-24.md.
# These used to be imported eagerly (many inside contextlib.suppress(Exception)), so importing
# any cohezion.compound.* submodule executed all of them and every package they reach. They now load on
# first access; a broken submodule raises a chained AttributeError where it is used.
_LAZY: dict[str, tuple[str, str]] = {
    "initialize_cohezion_environment": (
        "cohezion.compound.universal.init",
        "initialize_cohezion_environment",
    ),
    "ExecutionAnalyzer": ("cohezion.compound.analytics.engine", "ExecutionAnalyzer"),
    "SimpleAnalyzer": ("cohezion.compound.analytics.engine", "SimpleAnalyzer"),
    "MetricsCollector": ("cohezion.compound.analytics.metrics", "MetricsCollector"),
    "BatchableExecutor": ("cohezion.compound.batch_executor", "BatchableExecutor"),
    "BatchExecutorFactory": ("cohezion.compound.batch_executor", "BatchExecutorFactory"),
    "Config": ("cohezion.compound.config", "CompoundConfig"),
    "BatchProcessor": ("cohezion.compound.core.batch_processor", "BatchProcessor"),
    "check_quality": ("cohezion.compound.hiho_lm_gate", "check_quality"),
    "check_sycophancy": ("cohezion.compound.hiho_lm_gate", "check_sycophancy"),
    "ppl_score": ("cohezion.compound.hiho_lm_gate", "ppl_score"),
    "JourneyToTrainingBridge": ("cohezion.compound.journey_to_training", "JourneyToTrainingBridge"),
    "ValidationResult": ("cohezion.compound.journey_to_training", "ValidationResult"),
    "CompoundSessionManager": ("cohezion.compound.session_manager", "CompoundSessionManager"),
    "ThermalAutoresearchExecutor": (
        "cohezion.compound.thermal_autoresearch_executor",
        "ThermalAutoresearchExecutor",
    ),
    "DistillationEngine": ("cohezion.compound.distillation_engine", "DistillationEngine"),
    "AGIEvaluator": ("cohezion.compound.agi_reasoning", "AGIEvaluator"),
    "ReasoningModel": ("cohezion.compound.agi_reasoning", "ReasoningModel"),
    "FailureSignature": ("cohezion.compound.retrospection_summary", "FailureSignature"),
    "mine_failure_signatures": (
        "cohezion.compound.retrospection_summary",
        "mine_failure_signatures",
    ),
    "AIMOScaler": ("cohezion.compound.aimo_reasoning", "AIMOScaler"),
    "ProcessRewardModel": ("cohezion.compound.aimo_reasoning", "ProcessRewardModel"),
    "CLRQualityGate": ("cohezion.compound.clr_quality_gate", "CLRQualityGate"),
    "HealthObservabilityMixin": (
        "cohezion.compound.degradation_health",
        "HealthObservabilityMixin",
    ),
    "LoopDaemon": ("cohezion.compound.loop_daemon", "LoopDaemon"),
    "RubricMiddleware": ("cohezion.compound.rubric_middleware", "RubricMiddleware"),
    "RubricVerdict": ("cohezion.compound.rubric_middleware", "RubricVerdict"),
    "VModelCoverageReport": ("cohezion.compound.vmodel_harness", "VModelCoverageReport"),
    "VModelHarness": ("cohezion.compound.vmodel_harness", "VModelHarness"),
    "CompoundExecutor": ("cohezion.compound.core.executor", "CompoundExecutor"),
    "execute_simple": ("cohezion.compound.core.executor", "execute_simple"),
    "LegacyCompoundExecutor": ("cohezion.compound.executor", "CompoundExecutor"),
    "CompoundExecutorFactory": ("cohezion.compound.executor_factory", "ExecutorFactory"),
    "AnalysisReport": ("cohezion.compound.models", "AnalysisReport"),
    "ExecutionContext": ("cohezion.compound.models", "ExecutionContext"),
    "ExecutionMetrics": ("cohezion.compound.models", "ExecutionMetrics"),
    "ExecutionResult": ("cohezion.compound.models", "ExecutionResult"),
    "ExecutionStatus": ("cohezion.compound.models", "ExecutionStatus"),
    "IntentType": ("cohezion.compound.models", "IntentType"),
    "Task": ("cohezion.compound.models", "Task"),
    "SessionPersister": ("cohezion.compound.persistence.vault", "SessionPersister"),
    "VaultPersister": ("cohezion.compound.persistence.vault", "VaultPersister"),
    "SkillDiff": ("cohezion.compound.skill_evolution_diff", "SkillDiff"),
    "SkillEvolutionTracker": ("cohezion.compound.skill_evolution_diff", "SkillEvolutionTracker"),
    "SkillVersion": ("cohezion.compound.skill_evolution_diff", "SkillVersion"),
    "SkillHealthRecord": ("cohezion.compound.skill_health_tracker", "SkillHealthRecord"),
    "SkillHealthTracker": ("cohezion.compound.skill_health_tracker", "SkillHealthTracker"),
    "ImprovementHypothesis": (
        "cohezion.compound.skill_quality_orchestrator",
        "ImprovementHypothesis",
    ),
    "ImprovementResult": ("cohezion.compound.skill_quality_orchestrator", "ImprovementResult"),
    "SkillQualityOrchestrator": (
        "cohezion.compound.skill_quality_orchestrator",
        "SkillQualityOrchestrator",
    ),
    "DimensionScore": ("cohezion.compound.skill_quality_scorer", "DimensionScore"),
    "SkillQualityReport": ("cohezion.compound.skill_quality_scorer", "SkillQualityReport"),
    "SkillQualityScorer": ("cohezion.compound.skill_quality_scorer", "SkillQualityScorer"),
    "SkillSelector": ("cohezion.compound.skills.selector", "SkillSelector"),
    "AdversarialReviewSystem": (
        "cohezion.compound.tdd_adversarial.adversarial_review",
        "AdversarialReviewSystem",
    ),
    "PerspectiveState": (
        "cohezion.compound.tdd_adversarial.adversarial_review",
        "PerspectiveState",
    ),
    "ReviewFinding": ("cohezion.compound.tdd_adversarial.adversarial_review", "ReviewFinding"),
    "ReviewPerspective": (
        "cohezion.compound.tdd_adversarial.adversarial_review",
        "ReviewPerspective",
    ),
    "ReviewSession": ("cohezion.compound.tdd_adversarial.adversarial_review", "ReviewSession"),
    "get_adversarial_review_system": (
        "cohezion.compound.tdd_adversarial.adversarial_review",
        "get_adversarial_review_system",
    ),
    "TDDAdversarialCoordinator": (
        "cohezion.compound.tdd_adversarial.coordinator",
        "TDDAdversarialCoordinator",
    ),
    "TDDAdversarialState": ("cohezion.compound.tdd_adversarial.coordinator", "TDDAdversarialState"),
    "get_tdd_adversarial_coordinator": (
        "cohezion.compound.tdd_adversarial.coordinator",
        "get_tdd_adversarial_coordinator",
    ),
    "TDDIntegration": ("cohezion.compound.tdd_adversarial.tdd_integration", "TDDIntegration"),
    "TDDState": ("cohezion.compound.tdd_adversarial.tdd_integration", "TDDState"),
    "TestResult": ("cohezion.compound.tdd_adversarial.tdd_integration", "TestResult"),
    "TestStatus": ("cohezion.compound.tdd_adversarial.tdd_integration", "TestStatus"),
    "TestType": ("cohezion.compound.tdd_adversarial.tdd_integration", "TestType"),
    "get_tdd_integration": (
        "cohezion.compound.tdd_adversarial.tdd_integration",
        "get_tdd_integration",
    ),
    "BehaviorProperty": ("cohezion.compound.behavioral_eval", "BehaviorProperty"),
    "BehaviorTestResult": ("cohezion.compound.behavioral_eval", "BehaviorTestResult"),
    "CompoundEcoSymphony": ("cohezion.compound.eco_symphony", "CompoundEcoSymphony"),
    "EcoResilienceCompoundEngine": (
        "cohezion.compound.eco_symphony",
        "EcoResilienceCompoundEngine",
    ),
    "EvolutionTrainingConfig": (
        "cohezion.compound.evolution_training_bridge",
        "EvolutionTrainingConfig",
    ),
    "EvolutionTrainingExporter": (
        "cohezion.compound.evolution_training_bridge",
        "EvolutionTrainingExporter",
    ),
    "EvolutionTrainingSignalGenerator": (
        "cohezion.compound.evolution_training_bridge",
        "EvolutionTrainingSignalGenerator",
    ),
    "compute_temporal_correlation": (
        "cohezion.compound.experiment_correlator",
        "compute_temporal_correlation",
    ),
    "HarnessSynthesizer": ("cohezion.compound.harness", "HarnessSynthesizer"),
    "CompoundHealthReport": ("cohezion.compound.health", "CompoundHealthReport"),
    "SkillHistoryResponse": ("cohezion.compound.health", "SkillHistoryResponse"),
    "encode_step_sequence": ("cohezion.compound.holographic_projection", "encode_step_sequence"),
    "holographic_project": ("cohezion.compound.holographic_projection", "holographic_project"),
    "step_to_axiomatic": ("cohezion.compound.holographic_projection", "step_to_axiomatic"),
    "text_to_latent": ("cohezion.compound.holographic_projection", "text_to_latent"),
    "IntakeGreeting": ("cohezion.compound.intake_specialist", "IntakeGreeting"),
    "IntakeSpecialist": ("cohezion.compound.intake_specialist", "IntakeSpecialist"),
    "LongHorizonTask": ("cohezion.compound.long_horizon_task", "LongHorizonTask"),
    "TaskStepResult": ("cohezion.compound.long_horizon_task", "TaskStepResult"),
    "get_context_usage_percent": (
        "cohezion.compound.long_horizon_task",
        "get_context_usage_percent",
    ),
    "PlasmaAnomalyData": ("cohezion.compound.plasma_theosophy_synthesizer", "PlasmaAnomalyData"),
    "PlasmaTheosophySynthesizer": (
        "cohezion.compound.plasma_theosophy_synthesizer",
        "PlasmaTheosophySynthesizer",
    ),
    "PostExecutionOrchestrator": ("cohezion.compound.post_execution", "PostExecutionOrchestrator"),
    "ImprovementOpportunity": ("cohezion.compound.recursive_challenger", "ImprovementOpportunity"),
    "RecursiveChallenger": ("cohezion.compound.recursive_challenger", "RecursiveChallenger"),
    "get_test_count": ("cohezion.compound.recursive_challenger", "get_test_count"),
    "CycleMetrics": ("cohezion.compound.retrospection_summary", "CycleMetrics"),
    "RetrospectionSummary": ("cohezion.compound.retrospection_summary", "RetrospectionSummary"),
    "RetrospectionValidator": (
        "cohezion.compound.retrospection_validator",
        "RetrospectionValidator",
    ),
    "RoutingDecision": ("cohezion.compound.routing_feedback_loop", "RoutingDecision"),
    "RoutingDecisionType": ("cohezion.compound.routing_feedback_loop", "RoutingDecisionType"),
    "RoutingMetrics": ("cohezion.compound.routing_feedback_loop", "RoutingMetrics"),
    "AgentVote": ("cohezion.compound.skill_consensus_voter", "AgentVote"),
    "VotingStrategy": ("cohezion.compound.skill_consensus_voter", "VotingStrategy"),
    "RefinementMetrics": ("cohezion.compound.skill_refinement_validator", "RefinementMetrics"),
    "SkillRefinementValidator": (
        "cohezion.compound.skill_refinement_validator",
        "SkillRefinementValidator",
    ),
    "TapeEntry": ("cohezion.compound.tape_logger", "TapeEntry"),
    "TapeLogger": ("cohezion.compound.tape_logger", "TapeLogger"),
    "QueuedTask": ("cohezion.compound.task_queue", "QueuedTask"),
    "TaskPriority": ("cohezion.compound.task_queue", "TaskPriority"),
    "ThermalMetrics": ("cohezion.compound.thermal_predictor", "ThermalMetrics"),
    "UniverseBridge": ("cohezion.compound.universe_bridge", "UniverseBridge"),
    "SearchQuery": ("cohezion.compound.vault_search_executor", "SearchQuery"),
    "SearchResult": ("cohezion.compound.vault_search_executor", "SearchResult"),
    "PruningReport": ("cohezion.compound.vector_pruning", "PruningReport"),
    "SemanticVector": ("cohezion.compound.vector_pruning", "SemanticVector"),
    "GapReport": ("cohezion.compound.workflow_manager", "GapReport"),
    "OnboardingResult": ("cohezion.compound.workflow_manager", "OnboardingResult"),
    "WorkflowManager": ("cohezion.compound.workflow_manager", "WorkflowManager"),
    "OtelSpan": ("cohezion.compound.trace_exporter", "OtelSpan"),
    "make_executor": ("cohezion.compound.executor_factory", "make_executor"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        try:
            return _importlib.import_module(f"{__name__}.{name}")
        except ModuleNotFoundError as e:
            if e.name != f"{__name__}.{name}":
                raise
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    module, attr = target
    try:
        value = getattr(_importlib.import_module(module), attr)
    except ImportError as e:
        raise AttributeError(
            f"module {__name__!r} attribute {name!r} unavailable: {module} failed to import ({e})"
        ) from e
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))
