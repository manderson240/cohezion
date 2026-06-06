"""Cohezion substrate layer - foundation for 12D simulation."""

from __future__ import annotations

import contextlib

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

# Wiring-sweep 2026-06-06: popcorn was a genuine production orphan — its Popcorn-CLI kernel
# submission API (submit / SubmitResult) had ZERO importers anywhere (the lone "Popcorn" grep
# hit in scripts/compound_kernel_cycle.py is a LOG STRING, not an import). Cycle-safe (no
# cohezion module-scope import; subprocess/stdlib only). Guarded re-export makes it statically
# reachable; SEPARATE suppress block keeps the load-bearing tracker/coordinator imports above
# unaffected if popcorn ever grows an optional dep.
with contextlib.suppress(Exception):
    from cohezion.substrate.popcorn import (
        SubmitResult as SubmitResult,
    )
    from cohezion.substrate.popcorn import (
        submit as submit,
    )

    __all__ += ["SubmitResult", "submit"]
