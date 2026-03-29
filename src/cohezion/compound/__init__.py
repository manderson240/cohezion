"""Cohezion Compound Engineering System."""

from __future__ import annotations


# Universal initialization
try:
    from .universal.init import (
        initialize_cohezion_environment as initialize_cohezion_environment,
    )
except Exception:
    pass

from cohezion.compound.analytics.engine import (
    ExecutionAnalyzer as ExecutionAnalyzer,
    SimpleAnalyzer as SimpleAnalyzer,
)
from cohezion.compound.analytics.metrics import MetricsCollector as MetricsCollector

# Legacy API (Selective Compatibility)
from cohezion.compound.batch_executor import (
    BatchableExecutor as BatchableExecutor,
    BatchExecutorFactory as BatchExecutorFactory,
)
from cohezion.compound.config import CompoundConfig as Config  # noqa: F401
from cohezion.compound.core.batch_processor import BatchProcessor as BatchProcessor
from cohezion.compound.core.executor import (
    CompoundExecutor as CompoundExecutor,
    execute_simple as execute_simple,
)
from cohezion.compound.executor import CompoundExecutor as LegacyCompoundExecutor  # noqa: F401
from cohezion.compound.executor import ExecutorFactory as CompoundExecutorFactory  # noqa: F401

# New Simplified API
from cohezion.compound.models import (
    AnalysisReport as AnalysisReport,
    ExecutionContext as ExecutionContext,
    ExecutionMetrics as ExecutionMetrics,
    ExecutionResult as ExecutionResult,
    ExecutionStatus as ExecutionStatus,
    IntentType as IntentType,
    Task as Task,
)
from cohezion.compound.persistence.vault import (
    SessionPersister as SessionPersister,
    VaultPersister as VaultPersister,
)
from cohezion.compound.skills.selector import SkillSelector as SkillSelector

# TDD and Adversarial Review System
from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem as AdversarialReviewSystem,
    PerspectiveState as PerspectiveState,
    ReviewFinding as ReviewFinding,
    ReviewPerspective as ReviewPerspective,
    ReviewSession as ReviewSession,
    get_adversarial_review_system as get_adversarial_review_system,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialCoordinator as TDDAdversarialCoordinator,
    TDDAdversarialState as TDDAdversarialState,
    get_tdd_adversarial_coordinator as get_tdd_adversarial_coordinator,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TDDIntegration as TDDIntegration,
    TDDState as TDDState,
    TestResult as TestResult,
    TestStatus as TestStatus,
    TestType as TestType,
    get_tdd_integration as get_tdd_integration,
)
