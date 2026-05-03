"""Performance timing utilities for Cohezion."""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any


logger = logging.getLogger(__name__)


class TimeitStats:
    """Aggregated timing statistics for a timed function."""

    def __init__(self) -> None:
        self.count: int = 0
        self.total: float = 0.0
        self.min: float = float("inf")
        self.max: float = 0.0

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    def record(self, elapsed: float) -> None:
        """Record a new timing sample."""
        self.count += 1
        self.total += elapsed
        if elapsed < self.min:
            self.min = elapsed
        if elapsed > self.max:
            self.max = elapsed

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "total": self.total,
            "mean": self.mean,
            "min": self.min,
            "max": self.max,
        }


def timeit(log: logging.Logger | None = None, threshold_ms: float = 0.0):
    """Decorator measuring function wall-clock time via perf_counter.

    Aggregated statistics live on the decorated function at
    ``fn._timeit_stats`` (a TimeitStats instance).

    If *threshold_ms* > 0, warn via *log* when a call exceeds it.
    """
    _log = log or logger

    def decorator(fn):
        stats = TimeitStats()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - t0) * 1000  # ms
                stats.record(elapsed)
                if threshold_ms and elapsed > threshold_ms:
                    _log.warning(
                        "%s took %.2f ms (threshold %.2f ms)",
                        fn.__name__,
                        elapsed,
                        threshold_ms,
                    )

        wrapper._timeit_stats = stats
        return wrapper

    return decorator


def get_stats(fn) -> TimeitStats:
    """Return the TimeitStats for a decorated function.

    Raises AttributeError if *fn* was never decorated with @timeit.
    """
    return fn._timeit_stats
