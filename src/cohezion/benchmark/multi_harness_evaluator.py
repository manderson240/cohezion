"""Backward compatibility alias for cohezion.benchmarks.multi_harness_evaluator."""

from cohezion.benchmarks.multi_harness_evaluator import (
    HarnessBenchmarkTask as HarnessBenchmarkTask,
    HarnessEvaluationResult as HarnessEvaluationResult,
    HarnessType as HarnessType,
    MultiHarnessEvaluator as MultiHarnessEvaluator,
)


__all__ = [
    "HarnessBenchmarkTask",
    "HarnessEvaluationResult",
    "HarnessType",
    "MultiHarnessEvaluator",
]
