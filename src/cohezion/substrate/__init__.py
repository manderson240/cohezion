"""Cohezion substrate layer - foundation for 12D simulation."""

from __future__ import annotations

from cohezion.substrate.kv_cache_tracker import (
    AllocationResult,
    KVCacheEntry,
    KVCacheTracker,
)
from cohezion.substrate.overload_coordinator import (
    OverloadCoordinator,
    OverloadError,
    ProtectionAction,
    ProtectionConfig,
    ProtectionLevel,
)


__all__ = [
    "AllocationResult",
    "KVCacheEntry",
    "KVCacheTracker",
    "OverloadCoordinator",
    "OverloadError",
    "ProtectionAction",
    "ProtectionConfig",
    "ProtectionLevel",
]
