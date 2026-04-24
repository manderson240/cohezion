"""Synthetic benchmark for CompoundExecutor.execute_task.

Read-only profiling pass (Z6 wave) — runs N iterations with mocked
external dependencies, captures cProfile data for the 11-step pipeline.

Usage:
    uv run python scripts/profiling/profile_executor.py

Outputs:
    /tmp/executor_profile.prof   (binary, loadable with pstats)
    stdout                       (top-30 cumulative + top-30 self-time)
"""

from __future__ import annotations

import cProfile
import io
import pstats
import sys
from collections import defaultdict
from time import perf_counter
from unittest.mock import MagicMock

N_ITERATIONS = 100

# ---------------------------------------------------------------------------
# Per-step timing (poor-man's pipeline breakdown — patches the helpers
# called by each pipeline step and accumulates wall time).
# ---------------------------------------------------------------------------

STEP_TIMES: dict[str, float] = defaultdict(float)
STEP_COUNTS: dict[str, int] = defaultdict(int)


def _wrap_for_step(step_name: str, fn):
    """Wrap a callable so its wall time accumulates under step_name."""

    def wrapper(*args, **kwargs):
        t0 = perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            STEP_TIMES[step_name] += perf_counter() - t0
            STEP_COUNTS[step_name] += 1

    return wrapper


def build_executor():
    """Construct a CompoundExecutor with all heavy deps mocked."""
    from cohezion.compound.executor import CompoundExecutor
    from cohezion.compound.journey_tracker import JourneyTracker
    from cohezion.compound.metrics import CompoundMetricsCollector

    mcp_client = MagicMock()
    mcp_client.vault_find_relevant_context.return_value = []
    mcp_client.vault_log_experiment.return_value = "experiments/test.md"
    mcp_client.vault_edit.return_value = None
    mcp_client.vault_extract_pattern.return_value = "patterns/test.md"

    collector = CompoundMetricsCollector()
    tracker = JourneyTracker()

    executor = CompoundExecutor(
        mcp_client=mcp_client,
        enable_guardrails=False,
        enable_skill_refinement=True,
        metrics_collector=collector,
        journey_tracker=tracker,
    )

    # Skip context auto-load (.context files don't exist in worktree)
    executor._context_loaded = True

    # Wrap several known integration points to bucket time per step.
    # We patch on the *instance* so we don't disturb other tests.
    if executor.logger is not None:
        executor.logger.log_execution_start = _wrap_for_step(
            "step_2_log_start", executor.logger.log_execution_start
        )
        executor.logger.log_execution_result = _wrap_for_step(
            "step_4_log_result", executor.logger.log_execution_result
        )
        executor.logger.extract_execution_pattern = _wrap_for_step(
            "step_6_extract_pattern", executor.logger.extract_execution_pattern
        )
        if hasattr(executor.logger, "log_execution_trace"):
            executor.logger.log_execution_trace = _wrap_for_step(
                "step_4_5_log_trace", executor.logger.log_execution_trace
            )

    if executor.inflection_detector is not None:
        executor.inflection_detector.detect_anomaly = _wrap_for_step(
            "step_5_detect_anomaly", executor.inflection_detector.detect_anomaly
        )

    if executor.skill_refiner is not None:
        executor.skill_refiner.refine = _wrap_for_step(
            "step_7_refine_skill", executor.skill_refiner.refine
        )

    if executor._journey_tracker is not None:
        executor._journey_tracker.track_execution = _wrap_for_step(
            "step_9_track_journey", executor._journey_tracker.track_execution
        )

    if executor._metrics_collector is not None:
        executor._metrics_collector.record_execution = _wrap_for_step(
            "step_8_record_metrics", executor._metrics_collector.record_execution
        )

    # Wrap experience guidance (Step 1) at the executor level
    executor.get_experience_guidance = _wrap_for_step(
        "step_1_get_guidance", executor.get_experience_guidance
    )

    return executor


def run_one(executor, i: int):
    """Execute a single synthetic task. Vary description to defeat template cache."""
    return executor.execute_task(
        task_description=f"synthetic perf benchmark iteration {i}",
        skill_name=f"perf_skill_{i % 3}",
        operation_type="generate",
        execute_fn=lambda guidance: (f"output {i}", {"coherence": 0.5}),
        project="profile",
    )


def main() -> int:
    print("Building CompoundExecutor with mocked deps ...", flush=True)
    executor = build_executor()

    # Warm-up: 5 iterations to populate caches and trigger lazy imports
    print("Warm-up (5 iterations) ...", flush=True)
    t_warm0 = perf_counter()
    for i in range(5):
        run_one(executor, i)
    print(f"  warm-up: {perf_counter() - t_warm0:.3f}s", flush=True)

    # Reset step counters after warmup so we measure steady-state
    STEP_TIMES.clear()
    STEP_COUNTS.clear()

    # Profile the measured iterations
    print(f"Profiling {N_ITERATIONS} iterations ...", flush=True)
    profiler = cProfile.Profile()

    t0 = perf_counter()
    profiler.enable()
    for i in range(N_ITERATIONS):
        run_one(executor, i + 1000)  # offset to avoid warmup overlap
    profiler.disable()
    elapsed = perf_counter() - t0

    profiler.dump_stats("/tmp/executor_profile.prof")

    # Total measured time
    print("\n=== TOTAL ===")
    print(f"  iterations:        {N_ITERATIONS}")
    print(f"  wall time:         {elapsed:.3f}s")
    print(f"  per-iteration:     {elapsed / N_ITERATIONS * 1000:.2f} ms")

    # Per-step breakdown
    total_step_time = sum(STEP_TIMES.values())
    print(f"\n=== PER-STEP BREAKDOWN ({N_ITERATIONS} iterations) ===")
    print(f"{'step':<32}{'total (ms)':>14}{'per-call (ms)':>16}{'% of pipeline':>16}")
    print("-" * 78)
    for step in sorted(STEP_TIMES.keys()):
        total_ms = STEP_TIMES[step] * 1000
        count = STEP_COUNTS[step]
        per_call_ms = total_ms / count if count else 0
        pct = (STEP_TIMES[step] / elapsed * 100) if elapsed else 0
        print(f"{step:<32}{total_ms:>14.2f}{per_call_ms:>16.3f}{pct:>15.1f}%")
    print("-" * 78)
    print(
        f"{'sum (instrumented)':<32}{total_step_time * 1000:>14.2f}"
        f"{'':>16}{(total_step_time / elapsed * 100):>15.1f}%"
    )
    print(
        f"{'unaccounted':<32}{(elapsed - total_step_time) * 1000:>14.2f}"
        f"{'':>16}{((elapsed - total_step_time) / elapsed * 100):>15.1f}%"
    )

    # cProfile reports
    print("\n=== Top 30 by CUMULATIVE time ===")
    buf = io.StringIO()
    pstats.Stats(profiler, stream=buf).sort_stats("cumulative").print_stats(30)
    print(buf.getvalue())

    print("\n=== Top 30 by SELF (tottime) ===")
    buf2 = io.StringIO()
    pstats.Stats(profiler, stream=buf2).sort_stats("tottime").print_stats(30)
    print(buf2.getvalue())

    # Filter to cohezion-internal calls
    print("\n=== Top 25 cohezion-internal by CUMULATIVE ===")
    buf3 = io.StringIO()
    pstats.Stats(profiler, stream=buf3).sort_stats("cumulative").print_stats("cohezion", 25)
    print(buf3.getvalue())

    return 0


if __name__ == "__main__":
    sys.exit(main())
