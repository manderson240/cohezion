"""
ASCENDED COHEZION - Configuration Module

Includes:
- Unified system configuration
- Configuration orchestration (CLAUDE.md/GEMINI.md sync)
"""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.config.config_archival import ConfigArchiver as ConfigArchiver
    from cohezion.config.config_archival import SizeEnforcer as SizeEnforcer

with contextlib.suppress(Exception):
    from cohezion.config.config_events import ConfigEvent as ConfigEvent

with contextlib.suppress(Exception):
    from cohezion.config.config_monitoring import ConfigMonitor as ConfigMonitor
    from cohezion.config.config_monitoring import (
        VaultSubscriptionClientProxy as VaultSubscriptionClientProxy,
    )

with contextlib.suppress(Exception):
    from cohezion.config.config_state import ChangeSet as ChangeSet
    from cohezion.config.config_state import ConfigConflict as ConfigConflict
    from cohezion.config.config_state import ConfigSchema as ConfigSchema
    from cohezion.config.config_state import ConfigState as ConfigState
    from cohezion.config.config_state import FileMetadata as FileMetadata
    from cohezion.config.config_state import ValidationReport as ValidationReport

with contextlib.suppress(Exception):
    from cohezion.config.config_sync_engine import ConfigSyncEngine as ConfigSyncEngine

with contextlib.suppress(Exception):
    from cohezion.config.config_sync_logger import ConfigSyncLogger as ConfigSyncLogger
    from cohezion.config.config_sync_logger import SyncLogEntry as SyncLogEntry

with contextlib.suppress(Exception):
    from cohezion.config.config_templates import ConfigTemplateEngine as ConfigTemplateEngine
    from cohezion.config.config_templates import TemplateContext as TemplateContext
    from cohezion.config.config_templates import TemplateType as TemplateType

with contextlib.suppress(Exception):
    from cohezion.config.config_validation import ConfigValidator as ConfigValidator
    from cohezion.config.config_validation import ReconciliationValidator as ReconciliationValidator

with contextlib.suppress(Exception):
    from cohezion.config.configuration_orchestrator import (
        ConfigurationOrchestrator as ConfigurationOrchestrator,
    )
    from cohezion.config.configuration_orchestrator import (
        get_config_orchestrator as get_config_orchestrator,
    )
    from cohezion.config.configuration_orchestrator import (
        reset_config_orchestrator as reset_config_orchestrator,
    )

with contextlib.suppress(Exception):
    from cohezion.config.conflict_policy import ConflictPolicy as ConflictPolicy
    from cohezion.config.conflict_policy import (
        ConflictResolutionPolicy as ConflictResolutionPolicy,
    )
    from cohezion.config.conflict_policy import (
        ConflictResolutionStrategy as ConflictResolutionStrategy,
    )

with contextlib.suppress(Exception):
    from cohezion.config.git_utils import GitUtils as GitUtils

with contextlib.suppress(Exception):
    from cohezion.config.unified import CloudGraderConfig as CloudGraderConfig
    from cohezion.config.unified import EmailConfig as EmailConfig
    from cohezion.config.unified import SystemConfig as SystemConfig
    from cohezion.config.unified import UniverseTrackConfig as UniverseTrackConfig
    from cohezion.config.unified import get_config as get_config
    from cohezion.config.unified import reload_config as reload_config


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

# Wiring-sweep 2026-06-22: event_wiring and semver_validator were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.config.event_wiring import CommitBatcher as CommitBatcher
    from cohezion.config.event_wiring import EventSubscriber as EventSubscriber

with contextlib.suppress(Exception):
    from cohezion.config.semver_validator import BumpType as BumpType
    from cohezion.config.semver_validator import SemVer as SemVer
