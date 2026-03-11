"""Substrate Governor & Temporal Dilation (Story 1.3, FR9, FR10, NFR-5).

Links hardware pressure signals to the system-wide Temporal Dilation
protocol. When VRAM/GTT exceeds 90%, the swarm's reasoning frequency
(pulse) slows deterministically to prevent OOM crashes.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

PRESSURE_THRESHOLD = 0.90  # 90% triggers dilation
CRITICAL_THRESHOLD = 0.95  # 95% triggers emergency eviction
MAX_DILATION_FACTOR = 10.0  # Maximum slowdown multiplier
RECOVERY_TARGET = 0.85  # Target pressure after recovery


class PressureLevel(Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"  # > 90%
    CRITICAL = "critical"  # > 95%


@dataclass
class DilationState:
    """Current temporal dilation state."""

    factor: float = 1.0  # 1.0 = normal speed, >1.0 = slowed
    pressure: float = 0.0
    level: PressureLevel = PressureLevel.NORMAL
    last_update: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "factor": self.factor,
            "pressure": self.pressure,
            "level": self.level.value,
        }


@dataclass
class GovernorEvent:
    """A governor event (dilation change or emergency eviction)."""

    event_type: str  # "dilation_start" | "dilation_increase" | "emergency_eviction" | "recovery"
    pressure: float
    dilation_factor: float
    timestamp: float = field(default_factory=time.time)


class SubstrateGovernor:
    """Manages temporal dilation based on hardware pressure.

    Flow:
    1. Monitor pressure (VRAM/GTT usage fraction)
    2. If > 90%: inject temporal_dilation factor into 12D state
    3. If > 95%: trigger emergency context eviction
    4. If < 85%: recovery, remove dilation
    """

    def __init__(
        self,
        pressure_threshold: float = PRESSURE_THRESHOLD,
        critical_threshold: float = CRITICAL_THRESHOLD,
        max_dilation: float = MAX_DILATION_FACTOR,
        recovery_target: float = RECOVERY_TARGET,
    ) -> None:
        self._pressure_threshold = pressure_threshold
        self._critical_threshold = critical_threshold
        self._max_dilation = max_dilation
        self._recovery_target = recovery_target
        self._state = DilationState()
        self._events: list[GovernorEvent] = []

    @property
    def state(self) -> DilationState:
        return self._state

    @property
    def events(self) -> list[GovernorEvent]:
        return list(self._events)

    def update_pressure(self, pressure: float) -> DilationState:
        """Update pressure reading and adjust dilation accordingly."""
        self._state.pressure = pressure
        self._state.last_update = time.time()

        if pressure >= self._critical_threshold:
            self._state.level = PressureLevel.CRITICAL
            self._state.factor = self._max_dilation
            self._emit("emergency_eviction", pressure, self._state.factor)
            logger.warning(
                "CRITICAL pressure %.1f%% — emergency eviction, dilation=%.1fx",
                pressure * 100,
                self._state.factor,
            )

        elif pressure >= self._pressure_threshold:
            self._state.level = PressureLevel.ELEVATED
            # Graduated dilation: linearly scale between 1.0 and max
            range_size = self._critical_threshold - self._pressure_threshold
            progress = (pressure - self._pressure_threshold) / range_size
            self._state.factor = 1.0 + progress * (self._max_dilation - 1.0)

            event_type = "dilation_start" if len(self._events) == 0 else "dilation_increase"
            self._emit(event_type, pressure, self._state.factor)
            logger.info(
                "Elevated pressure %.1f%% — dilation=%.1fx",
                pressure * 100,
                self._state.factor,
            )

        elif pressure < self._recovery_target and self._state.factor > 1.0:
            self._state.level = PressureLevel.NORMAL
            self._state.factor = 1.0
            self._emit("recovery", pressure, 1.0)
            logger.info("Pressure recovered to %.1f%% — dilation removed", pressure * 100)

        else:
            self._state.level = PressureLevel.NORMAL

        return self._state

    def get_pulse_interval(self, base_interval_ms: float = 100.0) -> float:
        """Get the current pulse interval (ms), adjusted for dilation."""
        return base_interval_ms * self._state.factor

    def _emit(self, event_type: str, pressure: float, factor: float) -> None:
        self._events.append(
            GovernorEvent(
                event_type=event_type,
                pressure=pressure,
                dilation_factor=factor,
            )
        )
