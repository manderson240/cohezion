"""Event-driven memory-pressure monitor for PROACTIVE OOM avoidance.

Refactors OOM from reactive-at-load-time (poll psutil only when a load is attempted) to
event-driven: a monitor classifies memory/swap into a ``PressureLevel`` and EMITS a
``MemoryPressureEvent`` only when the level *transitions*, so subscribers react proactively
(block new loads, evict models, shed load) instead of every caller polling independently.

Grounded in harness K1 / strix-halo rule 5 (reuses ``resource_manager``'s thresholds + the
psutil read as the single source of truth — no duplication).

The sampling DRIVER is pluggable: call ``evaluate()`` from any periodic tick (the telemetry /
degradation loop, or each load attempt), or — for true kernel-event driving — from a poll() on
Linux PSI (``/proc/pressure/memory``). The event-on-transition contract is identical regardless
of driver, which is what makes the rest of the system event-driven rather than poll-coupled.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

# resource_manager does NOT import this module at module scope (it lazy-imports get_pressure_monitor
# inside can_load_model), so importing its helpers here is cycle-free and keeps one source of truth.
from cohezion.platform.resource_manager import SWAP_PRESSURE_PCT, _read_system_memory


logger = logging.getLogger(__name__)


class PressureLevel(IntEnum):
    OK = 0
    WARNING = 1
    CRITICAL = 2


# Thresholds (GiB available / swap %). Grounded in K1 (128 GiB box, ~10 GiB safety buffer) and
# rule-5 (swap >= 50% is the OOM-killer precursor). NEEDS-CALIBRATION against live telemetry.
CRITICAL_AVAIL_GB = 8.0
WARNING_AVAIL_GB = 16.0
WARNING_SWAP_PCT = 30.0
# The CRITICAL swap threshold IS rule-5's SWAP_PRESSURE_PCT (50) — imported, not re-declared.


@dataclass(frozen=True)
class MemoryPressureEvent:
    """Emitted on a pressure-LEVEL transition (never on a same-level re-evaluation)."""

    level: PressureLevel
    previous: PressureLevel
    available_gb: float
    swap_pct: float
    timestamp: float

    @property
    def rising(self) -> bool:
        """True when pressure increased (OK→WARNING, WARNING→CRITICAL, …)."""
        return self.level > self.previous

    @property
    def relieved(self) -> bool:
        """True when pressure decreased."""
        return self.level < self.previous


def classify_pressure(available_gb: float, swap_pct: float) -> PressureLevel:
    """Pure classifier: (available GiB, swap %) → PressureLevel (K1 / rule-5)."""
    if available_gb < CRITICAL_AVAIL_GB or swap_pct >= SWAP_PRESSURE_PCT:
        return PressureLevel.CRITICAL
    if available_gb < WARNING_AVAIL_GB or swap_pct >= WARNING_SWAP_PCT:
        return PressureLevel.WARNING
    return PressureLevel.OK


class MemoryPressureMonitor:
    """Classifies memory/swap and emits an event on each pressure-level TRANSITION."""

    def __init__(self) -> None:
        self._level = PressureLevel.OK
        self._subscribers: list[Callable[[MemoryPressureEvent], None]] = []
        self._last_event: MemoryPressureEvent | None = None

    @property
    def current_level(self) -> PressureLevel:
        return self._level

    @property
    def last_event(self) -> MemoryPressureEvent | None:
        return self._last_event

    def subscribe(self, handler: Callable[[MemoryPressureEvent], None]) -> None:
        """Register a handler invoked on every pressure transition (rising or relieved)."""
        self._subscribers.append(handler)

    def evaluate(self, *, snapshot: tuple[float, float] | None = None) -> PressureLevel:
        """Sample, classify, and EMIT iff the level changed. Returns the (new) level.

        Idempotent within a level: repeated evaluations at the same level emit NOTHING — that
        is the event-driven contract (transitions, not poll-spam). Fail-soft: if memory can't
        be read the level is held unchanged and no event fires.

        ``snapshot`` overrides the live reading for tests: ``(available_GiB, swap_used_pct)``.
        """
        snap = snapshot if snapshot is not None else _read_system_memory()
        if snap is None:
            return self._level
        available_gb, swap_pct = snap
        level = classify_pressure(available_gb, swap_pct)
        if level != self._level:
            event = MemoryPressureEvent(
                level=level,
                previous=self._level,
                available_gb=available_gb,
                swap_pct=swap_pct,
                timestamp=time.time(),
            )
            self._level = level
            self._last_event = event
            self._notify(event)
        return level

    def _notify(self, event: MemoryPressureEvent) -> None:
        for handler in self._subscribers:
            try:
                handler(event)
            except Exception as exc:
                logger.warning("memory-pressure subscriber failed: %s", exc)

    def loads_blocked(self) -> bool:
        """Proactive gate for the load path: True at CRITICAL — refuse new model loads."""
        return self._level == PressureLevel.CRITICAL


_monitor: MemoryPressureMonitor | None = None


def get_pressure_monitor() -> MemoryPressureMonitor:
    """Process-wide singleton so the load gate, router, and evictors share one event stream."""
    global _monitor
    if _monitor is None:
        _monitor = MemoryPressureMonitor()
    return _monitor
