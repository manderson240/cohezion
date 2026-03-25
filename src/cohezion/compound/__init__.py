"""Cohezion Compound Engineering System."""

from __future__ import annotations


# Universal initialization
try:
    from .universal.init import initialize_cohezion_environment
except Exception:
    pass

import structlog

from cohezion.compound.analytics.engine import ExecutionAnalyzer, SimpleAnalyzer
from cohezion.compound.analytics.metrics import MetricsCollector

# Legacy API (Selective Compatibility)
from cohezion.compound.batch_executor import BatchableExecutor, BatchExecutorFactory
from cohezion.compound.config import CompoundConfig as Config
from cohezion.compound.core.batch_processor import BatchProcessor
from cohezion.compound.core.executor import CompoundExecutor, execute_simple
from cohezion.compound.executor import CompoundExecutor as LegacyCompoundExecutor
from cohezion.compound.executor import ExecutorFactory as CompoundExecutorFactory

# New Simplified API
from cohezion.compound.models import (
    AnalysisReport,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionStatus,
    IntentType,
    Task,
)
from cohezion.compound.persistence.vault import SessionPersister, VaultPersister
from cohezion.compound.skills.selector import SkillSelector

# TDD and Adversarial Review System
from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem,
    PerspectiveState,
    ReviewFinding,
    ReviewPerspective,
    ReviewSession,
    get_adversarial_review_system,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialCoordinator,
    TDDAdversarialState,
    get_tdd_adversarial_coordinator,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TDDIntegration,
    TDDState,
    TestResult,
    TestStatus,
    TestType,
    get_tdd_integration,
)
