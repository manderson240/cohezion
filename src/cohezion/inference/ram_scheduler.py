"""RamScheduler — 96 GB ceiling enforcer for the Strix Halo Lemonade fleet.

Strix Halo uses unified memory: NPU, iGPU, and CPU all share the same 128 GB
LPDDR5X pool.  Loading too many large models simultaneously causes OOM hangs
(N3 invariant: never ctx_size=0 on heavy models; this module enforces the RAM
ceiling before any load request reaches the router).

Design:
  - Model sizes come from the live Lemonade registry via LocalResearchFleet.
  - LRU tracking via collections.OrderedDict (O(1) eviction decisions).
  - 88 GB effective ceiling (96 GB − 8 GB safety buffer, mirrors N3).
  - ensure_loaded(model_id) is the main entry point: checks ceiling,
    evicts LRU large models if needed, then POSTs to /api/v1/load.
  - Lemonade auto-evicts via its own LRU when max_loaded_models is hit;
    this scheduler tracks estimated usage locally for pre-flight checks.
  - KV-cache overhead: +3 GB for models >10 GB, +1 GB for smaller models.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass


logger = logging.getLogger(__name__)

RAM_CEILING_GB = 96.0
RAM_EFFECTIVE_GB = 88.0  # N3: 8 GB headroom prevents OOM hangs


def _kv_overhead(size_gb: float) -> float:
    """Estimated KV-cache RAM overhead at ctx_size=16384."""
    return 3.0 if size_gb > 10.0 else 1.0


def model_footprint(model_id: str, fleet=None) -> float:
    """Total estimated RAM footprint: weights + KV cache.

    Args:
        model_id: Lemonade model identifier.
        fleet: LocalResearchFleet instance.  If None, uses the global singleton.
               Pass an injected fleet in tests to avoid HTTP calls.
    """
    from cohezion.inference.local_fleet import get_fleet
    f = fleet if fleet is not None else get_fleet()
    size = f.size_gb(model_id)
    return size + _kv_overhead(size)


@dataclass
class RamStatus:
    loaded_models: list[str]
    estimated_gb: float
    ceiling_gb: float
    headroom_gb: float
    at_risk: bool  # True when headroom < 12 GB


class RamScheduler:
    """Track model RAM usage and enforce the 96 GB ceiling.

    Thread-safety: not needed (single-threaded async Lemonade calls).

    Args:
        effective_ceiling_gb: Override the 88 GB default (for tests).
        fleet: LocalResearchFleet for size lookups.  Defaults to global singleton.
    """

    def __init__(
        self,
        effective_ceiling_gb: float = RAM_EFFECTIVE_GB,
        fleet=None,
    ) -> None:
        self._ceiling_gb = effective_ceiling_gb
        self._fleet = fleet  # None = lazy-resolve via get_fleet() at call time
        # LRU: model_id → (access_timestamp, footprint_gb)
        self._lru: OrderedDict[str, tuple[float, float]] = OrderedDict()

    # ── Public API ────────────────────────────────────────────────────────

    def can_load(self, model_id: str) -> bool:
        """Return True if loading model_id would not exceed the ceiling."""
        if model_id in self._lru:
            return True  # already accounted for
        new_footprint = model_footprint(model_id, self._fleet)
        return (self._current_gb() + new_footprint) <= self._ceiling_gb

    def ensure_loaded(self, model_id: str) -> list[str]:
        """Register model_id and return a list of model_ids to evict first.

        The caller is responsible for actually evicting (POST /api/v1/load
        with the new model causes Lemonade to evict via its own LRU).  This
        method ONLY provides the pre-flight eviction recommendation — it does
        not make HTTP calls.

        Returns [] when no eviction is needed.
        Returns [id, ...] of LRU models to evict before loading model_id.
        """
        if model_id in self._lru:
            self._touch(model_id)
            return []

        new_fp = model_footprint(model_id, self._fleet)
        to_evict: list[str] = []

        # Evict LRU large models until we have room.
        candidate_keys = [
            k for k in self._lru
            if self._lru[k][1] > 10.0  # only evict large models
        ]
        while self._current_gb() + new_fp > self._ceiling_gb and candidate_keys:
            victim = candidate_keys.pop(0)  # oldest first
            to_evict.append(victim)
            self._remove(victim)

        if self._current_gb() + new_fp > self._ceiling_gb:
            logger.warning(
                "RamScheduler: cannot fit %s (%.1f GB); current %.1f GB / %.1f GB",
                model_id, new_fp, self._current_gb(), self._ceiling_gb,
            )
        else:
            self._register(model_id, new_fp)

        return to_evict

    def record_eviction(self, model_id: str) -> None:
        """Notify scheduler that Lemonade evicted a model (LRU sync)."""
        self._remove(model_id)

    def status(self) -> RamStatus:
        loaded = list(self._lru.keys())
        used = self._current_gb()
        headroom = self._ceiling_gb - used
        return RamStatus(
            loaded_models=loaded,
            estimated_gb=round(used, 1),
            ceiling_gb=self._ceiling_gb,
            headroom_gb=round(headroom, 1),
            at_risk=headroom < 12.0,
        )

    def reset(self) -> None:
        self._lru.clear()

    # ── Internal ──────────────────────────────────────────────────────────

    def _current_gb(self) -> float:
        return sum(fp for _, fp in self._lru.values())

    def _register(self, model_id: str, footprint_gb: float) -> None:
        self._lru[model_id] = (time.monotonic(), footprint_gb)

    def _touch(self, model_id: str) -> None:
        _, fp = self._lru[model_id]
        self._lru.move_to_end(model_id)
        self._lru[model_id] = (time.monotonic(), fp)

    def _remove(self, model_id: str) -> None:
        self._lru.pop(model_id, None)


# Module-level singleton
_scheduler: RamScheduler | None = None


def get_scheduler() -> RamScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = RamScheduler()
    return _scheduler
