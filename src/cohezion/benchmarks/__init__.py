"""Benchmarking suite: agentic, coding, cyber, and unified orchestration."""

import contextlib


# Wiring-sweep 2026-06-22: all benchmark modules were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.benchmarks.agentic_benchmark import (
        AgenticBenchmark as AgenticBenchmark,
    )
    from cohezion.benchmarks.agentic_benchmark import AgenticTask as AgenticTask
    from cohezion.benchmarks.agentic_benchmark import TaskResult as TaskResult

with contextlib.suppress(Exception):
    from cohezion.benchmarks.agentic_metrics import (
        AgenticMetrics as AgenticMetrics,
    )
    from cohezion.benchmarks.agentic_metrics import (
        AgenticResults as AgenticResults,
    )

with contextlib.suppress(Exception):
    from cohezion.benchmarks.benchmark_suite import (
        IntrinsicResults as IntrinsicResults,
    )

with contextlib.suppress(Exception):
    from cohezion.benchmarks.coding_benchmark import (
        SWEBenchRunner as SWEBenchRunner,
    )

with contextlib.suppress(Exception):
    from cohezion.benchmarks.cyber_benchmark import (
        CyberBenchmark as CyberBenchmark,
    )

with contextlib.suppress(Exception):
    from cohezion.benchmarks.mock_evaluation import (
        MockBenchmarkEvaluator as MockBenchmarkEvaluator,
    )

with contextlib.suppress(Exception):
    from cohezion.benchmarks.orchestrator import (
        UnifiedBenchmarkOrchestrator as UnifiedBenchmarkOrchestrator,
    )
