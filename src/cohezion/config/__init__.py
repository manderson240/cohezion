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
    "ChangeSet",
    "CloudGraderConfig",
    "ConfigArchiver",
    "ConfigConflict",
    # State & Events
    "ConfigEvent",
    # Monitoring (Phase 2)
    "ConfigMonitor",
    "ConfigSchema",
    "ConfigState",
    # Real-Time Sync & Git Integration (Phase 4)
    "ConfigSyncEngine",
    "ConfigSyncLogger",
    "ConfigTemplateEngine",
    # Validation & Reconciliation (Phase 3)
    "ConfigValidator",
    # Configuration orchestration (Phase 1-3)
    "ConfigurationOrchestrator",
    # Conflict Resolution (Phase 5A)
    "ConflictPolicy",
    "ConflictResolutionPolicy",
    "ConflictResolutionStrategy",
    "EmailConfig",
    "FileMetadata",
    # Utilities
    "GitUtils",
    "ReconciliationValidator",
    "SizeEnforcer",
    "SyncLogEntry",
    # System config (existing)
    "SystemConfig",
    "TemplateContext",
    "TemplateType",
    "UniverseTrackConfig",
    "ValidationReport",
    "VaultSubscriptionClientProxy",
    "get_config",
    "get_config_orchestrator",
    "reload_config",
    "reset_config_orchestrator",
]

import contextlib

# Wiring-sweep 2026-06-22: event_wiring and semver_validator were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.config.event_wiring import CommitBatcher as CommitBatcher
    from cohezion.config.event_wiring import EventSubscriber as EventSubscriber

with contextlib.suppress(Exception):
    from cohezion.config.semver_validator import BumpType as BumpType
    from cohezion.config.semver_validator import SemVer as SemVer
