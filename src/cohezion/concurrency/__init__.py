"""Thread-safe concurrent execution utilities for multi-agent coordination.

Provides file locking, shared resource management, and synchronization
primitives for safe concurrent access to shared system resources.
"""

from cohezion.concurrency.file_lock import (
    ConfigManager,
    FileLock,
    FileLockError,
    safe_file_access,
)
from cohezion.concurrency.shared_resources import (
    CapabilityUsageTracker,
    GitLabRunnerConfig,
    SkillRegistry,
)

__all__ = [
    "FileLock",
    "FileLockError",
    "ConfigManager",
    "safe_file_access",
    "SkillRegistry",
    "CapabilityUsageTracker",
    "GitLabRunnerConfig",
]
