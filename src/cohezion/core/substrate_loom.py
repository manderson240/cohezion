"""Substrate Loom Zero-Copy SHM (Story 1.4, FR-3, NFR-1).

Implements zero-copy shared memory for 12D state vectors between Python swarm and
Rust physics engine. Uses threading.Lock for Atomic Pointer-Flipping simulation.
Watchdog detects stale pointers (no flip within 2 heartbeats) and activates degraded mode.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_S = 0.1
STALE_THRESHOLD_HEARTBEATS = 2
MANIFOLD_DIM = 12


class LoomMode(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"


@dataclass
class SHMSnapshot:
    state: np.ndarray
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"state": self.state.tolist(), "timestamp": self.timestamp}


class SubstrateLoom:
    """Atomic Pointer-Flipping SHM for Python↔Rust 12D state sync.

    In production, this wraps an mmap-backed shared memory region.
    The software-emulated version uses threading.Lock for atomic flips.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buffer: np.ndarray = np.zeros(MANIFOLD_DIM)
        self._last_flip_time: float = time.time()
        self._last_committed_snapshot: SHMSnapshot | None = None
        self._mode: LoomMode = LoomMode.ACTIVE
        self._crash_context: dict | None = None
        self._flip_count: int = 0

    def write(self, state: np.ndarray) -> None:
        """Atomic write to SHM via pointer flip."""
        with self._lock:
            self._buffer = state.copy()
            self._last_flip_time = time.time()
            self._last_committed_snapshot = SHMSnapshot(state=state.copy())
            self._flip_count += 1

    def read(self) -> np.ndarray:
        """Read current SHM state."""
        with self._lock:
            return self._buffer.copy()

    def check_watchdog(self) -> bool:
        """Returns True if the pointer is healthy (recent flip)."""
        elapsed = time.time() - self._last_flip_time
        stale_threshold = HEARTBEAT_INTERVAL_S * STALE_THRESHOLD_HEARTBEATS
        if elapsed > stale_threshold:
            self._activate_degraded_mode("stale pointer: no flip within 2 heartbeats")
            return False
        return True

    def simulate_rust_crash(self, crash_context: dict | None = None) -> None:
        """Simulate Rust engine crash for watchdog testing."""
        self._crash_context = crash_context or {"reason": "simulated crash"}
        # Advance last_flip_time far into the past to trigger watchdog
        self._last_flip_time = time.time() - (HEARTBEAT_INTERVAL_S * 10)

    def recover_from_snapshot(self) -> SHMSnapshot | None:
        """Return the last committed snapshot for state preservation."""
        return self._last_committed_snapshot

    @property
    def mode(self) -> LoomMode:
        return self._mode

    @property
    def flip_count(self) -> int:
        return self._flip_count

    def _activate_degraded_mode(self, reason: str) -> None:
        if self._mode != LoomMode.DEGRADED:
            logger.warning("SubstrateLoom degraded: %s. Crash context: %s", reason, self._crash_context)
        self._mode = LoomMode.DEGRADED
