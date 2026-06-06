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
from cohezion.compound.config import CompoundConfig as Config  # noqa: F401
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
from cohezion.compound.core.executor import (
    CompoundExecutor as CompoundExecutor,
)
from cohezion.compound.core.executor import (
    execute_simple as execute_simple,
)
from cohezion.compound.executor import CompoundExecutor as LegacyCompoundExecutor  # noqa: F401
from cohezion.compound.executor_factory import (  # noqa: F401
    ExecutorFactory as CompoundExecutorFactory,
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
    from cohezion.inference.triune_orchestrator import build_triune_orchestrator

    if lemonade_available():
        provider = build_triune_orchestrator()
        # Wire adaptive concurrency: under heavy model load, use sequential dispatch
        max_concurrent = get_recommended_concurrency()
        provider._max_concurrent = max_concurrent  # type: ignore[attr-defined]
    else:
        provider = None

    return CompoundExecutor(mcp_client, inference_provider=provider, **kwargs)  # type: ignore[arg-type]
