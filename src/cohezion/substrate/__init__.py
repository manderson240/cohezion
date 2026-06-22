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

import contextlib


with contextlib.suppress(Exception):
    from cohezion.substrate.hardware_monitor import HardwareMetrics as HardwareMetrics
    from cohezion.substrate.hardware_monitor import HardwareMonitor as HardwareMonitor
    from cohezion.substrate.hardware_monitor import get_hardware_monitor as get_hardware_monitor

with contextlib.suppress(Exception):
    from cohezion.substrate.popcorn import SubmitResult as SubmitResult
    from cohezion.substrate.popcorn import submit as submit
