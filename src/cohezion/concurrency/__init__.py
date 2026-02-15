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
from cohezion.concurrency.ollama_gate import OllamaGate, get_gate, reset_gate
from cohezion.concurrency.safe_singleton import safe_singleton
from cohezion.concurrency.shared_resources import (
    CapabilityUsageTracker,
    SkillRegistry,
)


__all__ = [
    "CapabilityUsageTracker",
    "ConfigManager",
    "FileLock",
    "FileLockError",
    "OllamaGate",
    "SkillRegistry",
    "get_gate",
    "reset_gate",
    "safe_file_access",
    "safe_singleton",
]
