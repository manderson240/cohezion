"""Cohezion Compound Engineering System."""

from __future__ import annotations

import contextlib


# Universal initialization
with contextlib.suppress(Exception):
    from .universal.init import (
        initialize_cohezion_environment as initialize_cohezion_environment,
    )

from cohezion.compound.analytics.engine import (
    ExecutionAnalyzer as ExecutionAnalyzer,
)
from cohezion.compound.analytics.engine import (
    SimpleAnalyzer as SimpleAnalyzer,
)
from cohezion.compound.analytics.metrics import MetricsCollector as MetricsCollector

# Legacy API (Selective Compatibility)
from cohezion.compound.batch_executor import (
    BatchableExecutor as BatchableExecutor,
)
from cohezion.compound.batch_executor import (
    BatchExecutorFactory as BatchExecutorFactory,
)
from cohezion.compound.config import CompoundConfig as Config  # noqa: F401  # pyright: ignore[reportUnusedImport]
from cohezion.compound.core.batch_processor import BatchProcessor as BatchProcessor


# Wiring-sweep 2026-06-06: hiho_lm_gate was an import-graph orphan (no production importer).
# Re-exported here so its HIHO-LM quality gate is part of compound's public surface and
# reachable by static analysis. Guarded — a future LM-import fragility must not take down
# the whole package. (Deeper integration of this model-based gate INTO anti_sycophancy /
# AUTODQA is a BEHAVIOR change — flagged for human decision in WIRING_SWEEP_LEDGER.md.)
with contextlib.suppress(Exception):
    from cohezion.compound.hiho_lm_gate import (
        check_quality as check_quality,
    )
    from cohezion.compound.hiho_lm_gate import (
        check_sycophancy as check_sycophancy,
    )
    from cohezion.compound.hiho_lm_gate import (
        ppl_score as ppl_score,
    )

# Wiring-sweep 2026-06-06: journey_to_training was a genuine import-graph orphan. Re-exported
# so the journey→training bridge is part of compound's public surface + statically reachable.
with contextlib.suppress(Exception):
    from cohezion.compound.journey_to_training import (
        JourneyToTrainingBridge as JourneyToTrainingBridge,
    )
    from cohezion.compound.journey_to_training import (
        ValidationResult as ValidationResult,
    )

# Wiring-sweep 2026-06-06: optimized_session_manager was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.optimized_session_manager import (
        CompoundSessionManager as CompoundSessionManager,
    )
    from cohezion.compound.optimized_session_manager import (
        OptimizedSessionRuntime as OptimizedSessionRuntime,
    )

# Wiring-sweep 2026-06-06: thermal_autoresearch_executor was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.thermal_autoresearch_executor import (
        ThermalAutoresearchExecutor as ThermalAutoresearchExecutor,
    )

# Wiring-sweep 2026-06-06: distillation_engine was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.distillation_engine import (
        DistillationEngine as DistillationEngine,
    )

# Wiring-sweep 2026-06-06: dynamic_compound_system was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.dynamic_compound_system import (
        DynamicCompoundSystem as DynamicCompoundSystem,
    )
    from cohezion.compound.dynamic_compound_system import (
        DynamicExecutionResult as DynamicExecutionResult,
    )

# Wiring-sweep 2026-06-06: dynamic_system_integration was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.dynamic_system_integration import (
        DynamicSystemCoordinator as DynamicSystemCoordinator,
    )

# Wiring-sweep 2026-06-06: consortium_instigator was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.consortium_instigator import (
        ConsortiumInstigator as ConsortiumInstigator,
    )

# Wiring-sweep 2026-06-06: agi_reasoning was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.agi_reasoning import (
        AGIEvaluator as AGIEvaluator,
    )
    from cohezion.compound.agi_reasoning import (
        ReasoningModel as ReasoningModel,
    )

# Self-Harness Weakness Mining (arXiv 2606.09498 §3.1): mine_failure_signatures
# was defined but never exported — zero callers, zero static analysis reachability.
# Re-exported here so the FailureSignature pipeline is part of compound's public
# surface and reachable by executor, skill_refiner, and downstream consumers.
with contextlib.suppress(Exception):
    from cohezion.compound.retrospection_summary import (
        FailureSignature as FailureSignature,
    )
with contextlib.suppress(Exception):
    from cohezion.compound.retrospection_summary import (
        mine_failure_signatures as mine_failure_signatures,
    )

# Wiring-sweep 2026-06-06: aimo_reasoning was a genuine import-graph orphan. Re-export its
# DISTINCTIVE classes only — `ReasoningModel` collides with agi_reasoning's (surface-name
# duplicate flagged for human review in WIRING_SWEEP_LEDGER.md), so it is NOT re-exported here.
with contextlib.suppress(Exception):
    from cohezion.compound.aimo_reasoning import (
        AIMOScaler as AIMOScaler,
    )
    from cohezion.compound.aimo_reasoning import (
        ProcessRewardModel as ProcessRewardModel,
    )
# Wiring-sweep 2026-06-22: clr_quality_gate was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.clr_quality_gate import (
        CLRQualityGate as CLRQualityGate,
    )

# Wiring-sweep 2026-06-22: degradation_health was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.degradation_health import (
        HealthObservabilityMixin as HealthObservabilityMixin,
    )

# Wiring-sweep 2026-06-22: loop_daemon was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.loop_daemon import (
        LoopDaemon as LoopDaemon,
    )

# Wiring-sweep 2026-06-22: rubric_middleware was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.rubric_middleware import (
        RubricMiddleware as RubricMiddleware,
    )
    from cohezion.compound.rubric_middleware import (
        RubricVerdict as RubricVerdict,
    )

# Wiring-sweep 2026-06-22: vmodel_harness was a genuine import-graph orphan (V-Model CI gate).
with contextlib.suppress(Exception):
    from cohezion.compound.vmodel_harness import (
        VModelCoverageReport as VModelCoverageReport,
    )
    from cohezion.compound.vmodel_harness import (
        VModelHarness as VModelHarness,
    )

from cohezion.compound.core.executor import (
    CompoundExecutor as CompoundExecutor,
)
from cohezion.compound.core.executor import (
    execute_simple as execute_simple,
)
from cohezion.compound.executor import CompoundExecutor as LegacyCompoundExecutor  # noqa: F401  # pyright: ignore[reportUnusedImport]
from cohezion.compound.executor_factory import (  # noqa: F401
    ExecutorFactory as CompoundExecutorFactory,  # pyright: ignore[reportUnusedImport]
)

# New Simplified API
from cohezion.compound.models import (
    AnalysisReport as AnalysisReport,
)
from cohezion.compound.models import (
    ExecutionContext as ExecutionContext,
)
from cohezion.compound.models import (
    ExecutionMetrics as ExecutionMetrics,
)
from cohezion.compound.models import (
    ExecutionResult as ExecutionResult,
)
from cohezion.compound.models import (
    ExecutionStatus as ExecutionStatus,
)
from cohezion.compound.models import (
    IntentType as IntentType,
)
from cohezion.compound.models import (
    Task as Task,
)
from cohezion.compound.persistence.vault import (
    SessionPersister as SessionPersister,
)
from cohezion.compound.persistence.vault import (
    VaultPersister as VaultPersister,
)

# Self-improving skill quality ecosystem
from cohezion.compound.skill_evolution_diff import (
    SkillDiff as SkillDiff,
)
from cohezion.compound.skill_evolution_diff import (
    SkillEvolutionTracker as SkillEvolutionTracker,
)
from cohezion.compound.skill_evolution_diff import (
    SkillVersion as SkillVersion,
)
from cohezion.compound.skill_health_tracker import (
    SkillHealthRecord as SkillHealthRecord,
)
from cohezion.compound.skill_health_tracker import (
    SkillHealthTracker as SkillHealthTracker,
)
from cohezion.compound.skill_quality_orchestrator import (
    ImprovementHypothesis as ImprovementHypothesis,
)
from cohezion.compound.skill_quality_orchestrator import (
    ImprovementResult as ImprovementResult,
)
from cohezion.compound.skill_quality_orchestrator import (
    SkillQualityOrchestrator as SkillQualityOrchestrator,
)
from cohezion.compound.skill_quality_scorer import (
    DimensionScore as DimensionScore,
)
from cohezion.compound.skill_quality_scorer import (
    SkillQualityReport as SkillQualityReport,
)
from cohezion.compound.skill_quality_scorer import (
    SkillQualityScorer as SkillQualityScorer,
)
from cohezion.compound.skills.selector import SkillSelector as SkillSelector

# TDD and Adversarial Review System
from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem as AdversarialReviewSystem,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    PerspectiveState as PerspectiveState,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewFinding as ReviewFinding,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewPerspective as ReviewPerspective,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewSession as ReviewSession,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    get_adversarial_review_system as get_adversarial_review_system,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialCoordinator as TDDAdversarialCoordinator,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialState as TDDAdversarialState,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    get_tdd_adversarial_coordinator as get_tdd_adversarial_coordinator,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TDDIntegration as TDDIntegration,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TDDState as TDDState,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TestResult as TestResult,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TestStatus as TestStatus,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TestType as TestType,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    get_tdd_integration as get_tdd_integration,
)

# Wiring-sweep 2026-06-22: behavioral_eval was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.behavioral_eval import (
        BehaviorProperty as BehaviorProperty,
    )
    from cohezion.compound.behavioral_eval import (
        BehaviorTestResult as BehaviorTestResult,
    )

# Wiring-sweep 2026-06-22: eco_symphony was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.eco_symphony import (
        CompoundEcoSymphony as CompoundEcoSymphony,
    )
    from cohezion.compound.eco_symphony import (
        EcoResilienceCompoundEngine as EcoResilienceCompoundEngine,
    )

# Wiring-sweep 2026-06-22: evolution_training_bridge was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.evolution_training_bridge import (
        EvolutionTrainingConfig as EvolutionTrainingConfig,
    )
    from cohezion.compound.evolution_training_bridge import (
        EvolutionTrainingExporter as EvolutionTrainingExporter,
    )
    from cohezion.compound.evolution_training_bridge import (
        EvolutionTrainingSignalGenerator as EvolutionTrainingSignalGenerator,
    )

# Wiring-sweep 2026-06-22: experiment_correlator was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.experiment_correlator import (
        compute_temporal_correlation as compute_temporal_correlation,
    )

# Wiring-sweep 2026-06-22: harness was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.harness import (
        HarnessSynthesizer as HarnessSynthesizer,
    )

# Wiring-sweep 2026-06-22: health was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.health import (
        CompoundHealthReport as CompoundHealthReport,
    )
    from cohezion.compound.health import (
        SkillHistoryResponse as SkillHistoryResponse,
    )

# Wiring-sweep 2026-06-22: holographic_projection was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.holographic_projection import (
        encode_step_sequence as encode_step_sequence,
    )
    from cohezion.compound.holographic_projection import (
        holographic_project as holographic_project,
    )
    from cohezion.compound.holographic_projection import (
        step_to_axiomatic as step_to_axiomatic,
    )
    from cohezion.compound.holographic_projection import (
        text_to_latent as text_to_latent,
    )

# Wiring-sweep 2026-06-22: intake_specialist was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.intake_specialist import (
        IntakeGreeting as IntakeGreeting,
    )
    from cohezion.compound.intake_specialist import (
        IntakeSpecialist as IntakeSpecialist,
    )

# Wiring-sweep 2026-06-22: long_horizon_task was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.long_horizon_task import (
        LongHorizonTask as LongHorizonTask,
    )
    from cohezion.compound.long_horizon_task import (
        TaskStepResult as TaskStepResult,
    )
    from cohezion.compound.long_horizon_task import (
        get_context_usage_percent as get_context_usage_percent,
    )

# Wiring-sweep 2026-06-22: plasma_theosophy_synthesizer was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.plasma_theosophy_synthesizer import (
        PlasmaAnomalyData as PlasmaAnomalyData,
    )
    from cohezion.compound.plasma_theosophy_synthesizer import (
        PlasmaTheosophySynthesizer as PlasmaTheosophySynthesizer,
    )

# Wiring-sweep 2026-06-22: post_execution was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.post_execution import (
        PostExecutionOrchestrator as PostExecutionOrchestrator,
    )

# Wiring-sweep 2026-06-22: recursive_challenger was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.recursive_challenger import (
        ImprovementOpportunity as ImprovementOpportunity,
    )
    from cohezion.compound.recursive_challenger import (
        RecursiveChallenger as RecursiveChallenger,
    )
    from cohezion.compound.recursive_challenger import (
        get_test_count as get_test_count,
    )

# Wiring-sweep 2026-06-22: retrospection_summary was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.retrospection_summary import (
        CycleMetrics as CycleMetrics,
    )
    from cohezion.compound.retrospection_summary import (
        RetrospectionSummary as RetrospectionSummary,
    )

# Wiring-sweep 2026-06-22: retrospection_validator was a genuine import-graph orphan.
# ValidationResult skipped — name collision with journey_to_training.ValidationResult (already wired).
with contextlib.suppress(Exception):
    from cohezion.compound.retrospection_validator import (
        RetrospectionValidator as RetrospectionValidator,
    )

# Wiring-sweep 2026-06-22: routing_feedback_loop was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.routing_feedback_loop import (
        RoutingDecision as RoutingDecision,
    )
    from cohezion.compound.routing_feedback_loop import (
        RoutingDecisionType as RoutingDecisionType,
    )
    from cohezion.compound.routing_feedback_loop import (
        RoutingMetrics as RoutingMetrics,
    )

# Wiring-sweep 2026-06-22: skill_consensus_voter was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.skill_consensus_voter import (
        AgentVote as AgentVote,
    )
    from cohezion.compound.skill_consensus_voter import (
        VotingStrategy as VotingStrategy,
    )

# Wiring-sweep 2026-06-22: skill_refinement_validator was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.skill_refinement_validator import (
        RefinementMetrics as RefinementMetrics,
    )
    from cohezion.compound.skill_refinement_validator import (
        SkillRefinementValidator as SkillRefinementValidator,
    )

# Wiring-sweep 2026-06-22: tape_logger was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.tape_logger import (
        TapeEntry as TapeEntry,
    )
    from cohezion.compound.tape_logger import (
        TapeLogger as TapeLogger,
    )

# Wiring-sweep 2026-06-22: task_queue was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.task_queue import (
        QueuedTask as QueuedTask,
    )
    from cohezion.compound.task_queue import (
        TaskPriority as TaskPriority,
    )

# Wiring-sweep 2026-06-22: thermal_predictor was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.thermal_predictor import (
        ThermalMetrics as ThermalMetrics,
    )

# Wiring-sweep 2026-06-22: universe_bridge was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.universe_bridge import (
        UniverseBridge as UniverseBridge,
    )

# Wiring-sweep 2026-06-22: vault_search_executor was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.vault_search_executor import (
        SearchQuery as SearchQuery,
    )
    from cohezion.compound.vault_search_executor import (
        SearchResult as SearchResult,
    )

# Wiring-sweep 2026-06-22: vector_pruning was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.vector_pruning import (
        PruningReport as PruningReport,
    )
    from cohezion.compound.vector_pruning import (
        SemanticVector as SemanticVector,
    )

# Wiring-sweep 2026-06-22: workflow_manager was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.compound.workflow_manager import (
        GapReport as GapReport,
    )
    from cohezion.compound.workflow_manager import (
        OnboardingResult as OnboardingResult,
    )
    from cohezion.compound.workflow_manager import (
        WorkflowManager as WorkflowManager,
    )


# Wiring-sweep 2026-06-22: loop_daemon, trace_exporter, vmodel_harness orphans.
with contextlib.suppress(Exception):
    from cohezion.compound.loop_daemon import LoopDaemon as LoopDaemon

with contextlib.suppress(Exception):
    from cohezion.compound.trace_exporter import OtelSpan as OtelSpan

with contextlib.suppress(Exception):
    from cohezion.compound.vmodel_harness import VModelHarness as VModelHarness


def make_executor(mcp_client: object, **kwargs: object) -> CompoundExecutor:
    """Factory that wires local AMD silicon (Triune) inference by default.

    Checks Lemonade liveness before building the TieredOrchestrator — no
    model weights are loaded in Python; only HTTP endpoints are probed.
    Falls back to inference_provider=None (caller must supply execute_fn)
    when Lemonade is offline.

    Also sets recommended max_concurrent on the orchestrator based on live
    model load count (exp_NNNN1: heavy load → sequential, light load → concurrent).
    """
    from cohezion.compound.executor import CompoundExecutor  # avoid circular at module level
    from cohezion.compound.local_inference import get_recommended_concurrency, lemonade_available
    from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

    if lemonade_available():
        exec_provider = build_triune_omni_orchestrator()
        # Wire adaptive concurrency: under heavy model load, use sequential dispatch
        max_concurrent = get_recommended_concurrency()
        exec_provider._max_concurrent = max_concurrent  # type: ignore[attr-defined]
    else:
        exec_provider = None

    # W1 + JG2: JepaGate auto-injection. build_live_jepa_gate wires a LEMONADE-backed world model
    # (GAIA SDK, :13305) + k-step lookahead when local inference is reachable; else fail-open.
    if "jepa_gate" not in kwargs:
        try:
            from cohezion.compound.lemonade_world_model import build_live_jepa_gate  # type: ignore[import]

            kwargs["jepa_gate"] = build_live_jepa_gate()  # type: ignore[assignment]
        except Exception:
            try:
                from cohezion.compound.jepa_gate import JepaGate  # type: ignore[import]

                kwargs["jepa_gate"] = JepaGate(world_model=None)  # type: ignore[assignment]
            except Exception:
                pass

    # M1: the FAPO R3 regression gate's run_fn is wired in SkillRefinerFactory.create (the canonical
    # creation point — the executor builds its SkillRefiner lazily, so it isn't available here).
    return CompoundExecutor(mcp_client, inference_provider=exec_provider, **kwargs)  # type: ignore[arg-type]
