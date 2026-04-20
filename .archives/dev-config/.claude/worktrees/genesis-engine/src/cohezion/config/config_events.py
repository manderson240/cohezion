"""Configuration system events for event-driven orchestration.

Extends core EventBus with configuration-specific event types
for monitoring CLAUDE.md, GEMINI.md, vault, and SurrealDB changes.
"""

from enum import Enum, auto


class ConfigEvent(Enum):
    """Configuration orchestration event types."""

    # Monitoring events
    VAULT_DECISION_ADDED = auto()
    VAULT_PATTERN_UPDATED = auto()
    VAULT_EXPERIMENT_CREATED = auto()
    SURREAL_UPDATED = auto()
    CONFIG_FILE_MODIFIED = auto()

    # Conflict detection
    MANUAL_EDIT_DETECTED = auto()
    CONFIG_CONFLICT_DETECTED = auto()

    # Validation events
    VALIDATION_STARTED = auto()
    VALIDATION_PASSED = auto()
    VALIDATION_FAILED = auto()
    SIZE_VIOLATION_DETECTED = auto()
    SCHEMA_VIOLATION_DETECTED = auto()
    REFERENCE_BROKEN = auto()

    # Sync events
    SYNC_INITIATED = auto()
    SYNC_COMPLETED = auto()
    SYNC_FAILED = auto()
    REGENERATED = auto()

    # Archive events
    ARCHIVE_TRIGGERED = auto()
    ARCHIVE_COMPLETED = auto()

    # Git events
    GIT_COMMIT_CREATED = auto()
    GIT_PUSH_INITIATED = auto()


# Event payload schemas (type hints)
VAULT_DECISION_ADDED_SCHEMA = {
    "path": str,
    "title": str,
    "status": str,
    "decision_type": str,
}

CONFIG_CONFLICT_DETECTED_SCHEMA = {
    "file": str,
    "vault_modified": float,  # timestamp
    "config_modified": float,
    "vault_hash": str,
    "config_hash": str,
}

REGENERATED_SCHEMA = {
    "file": str,
    "reason": str,  # "vault_change", "size_violation", "archival"
    "sections_added": int,
    "sections_removed": int,
}
