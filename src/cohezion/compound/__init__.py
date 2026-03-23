"""Cohezion Compound Engineering System."""

from __future__ import annotations

# Universal initialization
try:
    from .universal.init import initialize_cohezion_environment
except Exception:
    pass

import structlog

# New Simplified API
from cohezion.compound.models import (
    Task,
    ExecutionResult,
    ExecutionContext,
    ExecutionMetrics,
    AnalysisReport,
    ExecutionStatus,
    IntentType
)
from cohezion.compound.core.executor import CompoundExecutor, execute_simple
from cohezion.compound.core.batch_processor import BatchProcessor
from cohezion.compound.analytics.engine import ExecutionAnalyzer, SimpleAnalyzer
from cohezion.compound.analytics.metrics import MetricsCollector
from cohezion.compound.skills.selector import SkillSelector
from cohezion.compound.persistence.vault import VaultPersister, SessionPersister

# Legacy API (Selective Compatibility)
from cohezion.compound.batch_executor import BatchableExecutor, BatchExecutorFactory
from cohezion.compound.config import CompoundConfig as Config
from cohezion.compound.executor import CompoundExecutor as LegacyCompoundExecutor, ExecutorFactory as CompoundExecutorFactory

# TDD and Adversarial Review System
from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem,
    ReviewPerspective,
    ReviewFinding,
    PerspectiveState,
    ReviewSession,
    get_adversarial_review_system
)

from cohezion.compound.tdd_adversarial.tdd_integration import (
    TDDIntegration,
    TestStatus,
    TestType,
    TestResult,
    TDDState,
    get_tdd_integration
)

from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialCoordinator,
    TDDAdversarialState,
    get_tdd_adversarial_coordinator
)
