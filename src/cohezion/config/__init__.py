"""
ASCENDED COHEZION - Configuration Module

Includes:
- Unified system configuration
- Configuration orchestration (CLAUDE.md/GEMINI.md sync)
"""

from cohezion.config.config_archival import ConfigArchiver, SizeEnforcer
from cohezion.config.config_events import ConfigEvent
from cohezion.config.config_monitoring import (
    ConfigMonitor,
    VaultSubscriptionClientProxy,
)
from cohezion.config.config_state import (
    ChangeSet,
    ConfigConflict,
    ConfigSchema,
    ConfigState,
    FileMetadata,
    ValidationReport,
)
from cohezion.config.config_sync_engine import ConfigSyncEngine
from cohezion.config.config_sync_logger import ConfigSyncLogger, SyncLogEntry
from cohezion.config.config_templates import (
    ConfigTemplateEngine,
    TemplateContext,
    TemplateType,
)
from cohezion.config.config_validation import ConfigValidator, ReconciliationValidator
from cohezion.config.configuration_orchestrator import (
    ConfigurationOrchestrator,
    get_config_orchestrator,
    reset_config_orchestrator,
)
from cohezion.config.conflict_policy import (
    ConflictPolicy,
    ConflictResolutionPolicy,
    ConflictResolutionStrategy,
)
from cohezion.config.git_utils import GitUtils
from cohezion.config.unified import (
    CloudGraderConfig,
    EmailConfig,
    SystemConfig,
    UniverseTrackConfig,
    get_config,
    reload_config,
)


__all__ = [
    # System config (existing)
    "SystemConfig",
    "UniverseTrackConfig",
    "EmailConfig",
    "CloudGraderConfig",
    "get_config",
    "reload_config",
    # Configuration orchestration (Phase 1-3)
    "ConfigurationOrchestrator",
    "get_config_orchestrator",
    "reset_config_orchestrator",
    # Monitoring (Phase 2)
    "ConfigMonitor",
    "VaultSubscriptionClientProxy",
    # Validation & Reconciliation (Phase 3)
    "ConfigValidator",
    "ReconciliationValidator",
    "ConfigArchiver",
    "SizeEnforcer",
    "ConfigSyncLogger",
    "SyncLogEntry",
    # Real-Time Sync & Git Integration (Phase 4)
    "ConfigSyncEngine",
    "ConfigTemplateEngine",
    "TemplateContext",
    "TemplateType",
    # Conflict Resolution (Phase 5A)
    "ConflictPolicy",
    "ConflictResolutionPolicy",
    "ConflictResolutionStrategy",
    # State & Events
    "ConfigEvent",
    "ConfigState",
    "FileMetadata",
    "ChangeSet",
    "ConfigConflict",
    "ValidationReport",
    "ConfigSchema",
    # Utilities
    "GitUtils",
]
