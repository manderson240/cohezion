"""
ASCENDED COHEZION - Configuration Module

Includes:
- Unified system configuration
- Configuration orchestration (CLAUDE.md/GEMINI.md sync)
"""

from cohezion.config.configuration_orchestrator import (
    ConfigurationOrchestrator,
    get_config_orchestrator,
    reset_config_orchestrator,
)
from cohezion.config.config_events import ConfigEvent
from cohezion.config.config_monitoring import ConfigMonitor, VaultSubscriptionClientProxy
from cohezion.config.config_state import (
    ChangeSet,
    ConfigConflict,
    ConfigSchema,
    ConfigState,
    FileMetadata,
    ValidationReport,
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
    # Configuration orchestration (Phase 1-2)
    "ConfigurationOrchestrator",
    "get_config_orchestrator",
    "reset_config_orchestrator",
    "ConfigMonitor",
    "VaultSubscriptionClientProxy",
    "ConfigEvent",
    "ConfigState",
    "FileMetadata",
    "ChangeSet",
    "ConfigConflict",
    "ValidationReport",
    "ConfigSchema",
    "GitUtils",
]
