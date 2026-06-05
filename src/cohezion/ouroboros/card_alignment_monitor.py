"""Card alignment monitor — tracks the card_alignment_rate and emits
a HEALING_EVENT precipitation when the rate drops below threshold.

This is the producer-side of Connection C (Ouroboros card-alignment
signal). The verifier side lives in `verify_evolve.py::_query_ouroboros_healing_events`.

Architecture:
    Every aligned execute_fn call (PR 1) records `card_aligned=True`
    in its metrics. The DegradationDetector already watches
    `cache_hit_rate` + `token_efficiency`; the CardAlignmentMonitor
    adds a third signal: `card_alignment_rate`. On a sustained drop
    below threshold (default 50% over a 10-call window), the
    monitor emits a HEALING_EVENT precipitation. Existing consumers
    (Ouroboros' HealerAgent, verify_evolve's quantitative check) read
    these events.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass

from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind


logger = logging.getLogger(__name__)


@dataclass
class AlignmentVerdict:
    dipped: bool
    rate: float
    window_size: int


class CardAlignmentMonitor:
    """Tracks the card_alignment_rate and emits HEALING_EVENTs on
    sustained drops.

    Usage:
        monitor = CardAlignmentMonitor(threshold=0.5, window_size=10)
        monitor.record_execution(card_aligned=True)
        # ... more executions ...
        verdict = monitor.check()
        if verdict.dipped:
            # A HEALING_EVENT was emitted to the bus
            ...
    """

    def __init__(
        self, threshold: float = 0.5, window_size: int = 10
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold {threshold} must be in [0, 1]")
        if window_size < 1:
            raise ValueError(f"window_size {window_size} must be >= 1")
        self.threshold = threshold
        self.window_size = window_size
        self._window: deque[bool] = deque(maxlen=window_size)
        self._emitted_this_drop: bool = False

    def record_execution(self, *, card_aligned: bool) -> None:
        """Record a single execution outcome."""
        self._window.append(bool(card_aligned))

    def _rate(self) -> float:
        if not self._window:
            return 1.0
        return sum(self._window) / len(self._window)

    def check(self) -> AlignmentVerdict:
        """If the window is full and the rate is below threshold, emit
        a HEALING_EVENT and reset the latch.

        Returns the current verdict. The HEALING_EVENT emission is
        best-effort and never raises.
        """
        rate = self._rate()
        dipped = (
            len(self._window) >= self.window_size
            and rate < self.threshold
            and not self._emitted_this_drop
        )
        if dipped:
            self._emitted_this_drop = True
            self._emit_healing_event(rate)
        elif rate >= self.threshold:
            # Recovery: re-arm the latch
            self._emitted_this_drop = False
        return AlignmentVerdict(
            dipped=dipped, rate=rate, window_size=len(self._window)
        )

    def _emit_healing_event(self, rate: float) -> None:
        try:
            from cohezion.precipitation import bus
            event = PrecipitationEvent(
                kind=PrecipitationKind.HEALING_EVENT,
                universe_id="cohezion_card_alignment_monitor",
                coherence=1.0 - rate,  # low coherence = healing needed
                twelve_d={
                    "x": 0.5, "y": 0.5, "z": 0.5, "time": 0.5,
                    "physics": 0.5, "biology": 0.5, "logic": 0.5, "quantum": 0.5,
                    "field": 0.5, "control": 0.5, "novelty": 0.5, "precipitation": 0.5,
                },
                payload={
                    "source": "ouroboros.card_alignment_monitor",
                    "rate": rate,
                    "threshold": self.threshold,
                    "window_size": self.window_size,
                },
            )
            bus.emit(event)
            logger.info(
                "CardAlignmentMonitor emitted HEALING_EVENT (rate=%.2f < %.2f)",
                rate, self.threshold,
            )
        except Exception as e:
            logger.debug("HEALING_EVENT emission failed (non-blocking): %s", e)
