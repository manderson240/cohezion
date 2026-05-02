"""Utility functions for running and analyzing benchmarks."""

import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    operation: str
    samples: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    stddev_ms: float
    errors: int
    error_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def run_benchmark(
    name: str,
    func: Callable[[], Any],
    iterations: int = 10,
    warmup: int = 2,
) -> BenchmarkResult:
    """Run benchmark and collect statistics.

    Args:
        name: Operation name for reporting
        func: Callable that performs the operation to benchmark
        iterations: Number of measured iterations
        warmup: Number of warmup iterations before measurement

    Returns:
        BenchmarkResult with statistics
    """
    # Warmup runs (errors ignored)
    for _ in range(warmup):
        try:
            func()
        except Exception:
            pass

    # Measured runs
    times: list[float] = []
    errors = 0
    for _ in range(iterations):
        try:
            start = time.perf_counter()
            func()
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        except Exception:
            errors += 1

    # Calculate statistics
    if not times:
        times = [0.0]  # Avoid empty list errors

    sorted_times = sorted(times)
    n = len(sorted_times)

    return BenchmarkResult(
        operation=name,
        samples=len(times),
        mean_ms=sum(times) / len(times),
        median_ms=sorted_times[n // 2],
        p95_ms=sorted_times[int(n * 0.95)] if n >= 20 else sorted_times[-1],
        p99_ms=sorted_times[int(n * 0.99)] if n >= 100 else sorted_times[-1],
        min_ms=min(times),
        max_ms=max(times),
        stddev_ms=statistics.stdev(times) if len(times) > 1 else 0.0,
        errors=errors,
        error_rate=errors / (iterations + errors) if (iterations + errors) > 0 else 0.0,
    )
