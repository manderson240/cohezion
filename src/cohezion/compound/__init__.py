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

# ============================================================================
# New Simplified Core (Phase 1) - Clean implementations
# ============================================================================
from cohezion.compound.models import (
    AnalysisReport,
    BatchConfig,
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
    # Compatibility layer (old API)
    "CompoundCycleReport",
    "CompoundCycleResult",
    "CompoundExecutor",
    "ConstraintType",
    "ConstraintViolation",
    "CriterionFailure",
    "DriftSignal",
    "ExecutionAlignment",
    "ExecutionConstraint",
    "HumanRequest",
    "IntentType",
    "SuccessCriterion",
    "LegacyExecutionResult",
    # New models
    "AnalysisReport",
    "BatchConfig",
    "ExecutionContext",
    "ExecutionMetrics",
    "ExecutionResult",
    "ExecutionStatus",
    "Task",
    # New core
    "NewCompoundExecutor",
    "ExecutionConfig",
    "execute_simple",
    "BatchProcessor",
    "BatchResult",
    "SimpleBatch",
    # New analytics
    "AnalysisConfig",
    "ExecutionAnalyzer",
    "SimpleAnalyzer",
    "MetricsCollector",
    "MetricsSnapshot",
    "SimpleMetrics",
    # New skills
    "SkillMatch",
    "SkillSelector",
    "SkillRefiner",
    "SimpleSkills",
    # New persistence
    "PersistenceConfig",
    "SessionPersister",
    "SimplePersistence",
    "VaultPersister",
    # Version
    "__version__",
    "get_version",
]
