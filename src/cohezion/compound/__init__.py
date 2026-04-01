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
from cohezion.compound.core.executor import (
    CompoundExecutor as CompoundExecutor,
)
from cohezion.compound.core.executor import (
    execute_simple as execute_simple,
)
from cohezion.compound.executor import CompoundExecutor as LegacyCompoundExecutor  # noqa: F401
from cohezion.compound.executor import ExecutorFactory as CompoundExecutorFactory  # noqa: F401

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
