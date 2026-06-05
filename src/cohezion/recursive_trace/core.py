"""Recursive-Trace core — failure-class-informed strategy selection.

Pre-registered falsifiable gate:
    docs/research/RECURSIVE_TRACE_FALSIFIABLE_GATE_2026-06-05.md

The leveraged claim (the ONLY thing that distinguishes this from autoresearch):
    flat autoresearch samples the next candidate INDEPENDENT of why the previous
    attempt failed; RecursiveTraceLoop conditions the next candidate on the TYPED
    failure-class of the prior attempt (`failure_map[failure_class] -> strategy`),
    while both dedup (never retry a strategy).

Scope (Stage 1): this module implements the selection mechanism and the bounded
loop. The latent-retrieval components (`TraceMemory`, `LatentStateTracker`) that
would jump-start from past successes via LeWM embeddings are Stage-2 and remain
deliberately minimal — they are NOT on the gate's critical path and are marked so.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field


@dataclass
class TraceTask:
    """A unit of work the loop tries to solve by picking the right strategy.

    `failure_class` is the observed symptom (e.g. 'latency'); `solving_strategy` is
    the hidden oracle answer the loop is trying to reach.
    """

    task_id: str
    failure_class: str
    solving_strategy: str


@dataclass
class RecursiveTraceResult:
    """Outcome of a single `run()`: did we solve, in how many picks, and the path."""

    solved: bool
    iterations: int
    path: list[str] = field(default_factory=list)


class TraceMemory:
    """Minimal trace store (Stage-2 latent retrieval deferred).

    Stage 1 needs no embeddings; this keeps a plain record of solved (task ->
    strategy) pairs so a future Stage-2 pass can add cosine-similarity jump-starts
    without changing the public surface. It is intentionally NOT an embedding store
    yet — wiring LeWM/nomic-embed retrieval is gated behind a Stage-2 experiment.
    """

    def __init__(self) -> None:
        self._solved: dict[str, str] = {}

    def record_success(self, failure_class: str, strategy: str) -> None:
        self._solved[failure_class] = strategy

    def best_for(self, failure_class: str) -> str | None:
        return self._solved.get(failure_class)


class LatentStateTracker:
    """Stage-2 LeWM latent state search (deferred).

    Placeholder for encoding task state into LeWM latent space for similarity
    retrieval. Not on the Stage-1 gate path; left explicitly unimplemented so the
    audit flags it as pending rather than mistaking a hollow stub for capability.
    """

    def __init__(self) -> None:
        self.enabled = False


# -- RecursiveTraceLoop ---------------------------------------------------------


class RecursiveTraceLoop:
    """Bounded-depth loop that selects the next strategy from the prior failure-class.

    Algorithm (one iteration):
      1. Select the next strategy: prefer the strategy(ies) mapped from the task's
         failure-class (the failure signal informing selection); fall back to the
         next unused strategy in declared order. Never repeat (dedup).
      2. Apply via `scorer_fn(task, strategy)`. On success: record to TraceMemory and
         return solved. On failure: continue until strategies exhaust or max_depth.

    `max_depth` defaults to the number of strategies (a full non-repeating sweep).
    """

    def __init__(
        self,
        strategies: Sequence[str],
        failure_map: Mapping[str, Sequence[str]],
        *,
        max_depth: int | None = None,
        memory: TraceMemory | None = None,
    ) -> None:
        self.strategies = list(strategies)
        self.failure_map = {k: list(v) for k, v in failure_map.items()}
        self.max_depth = max_depth if max_depth is not None else len(self.strategies)
        self.memory = memory if memory is not None else TraceMemory()

    def _select_next(self, failure_class: str, tried: list[str]) -> str | None:
        """Failure-informed pick: mapped strategy first, then list-order fallback."""
        for mapped in self.failure_map.get(failure_class, []):
            if mapped not in tried and mapped in self.strategies:
                return mapped
        for strategy in self.strategies:
            if strategy not in tried:
                return strategy
        return None

    def run(
        self, task: TraceTask, scorer_fn: Callable[[TraceTask, str], bool]
    ) -> RecursiveTraceResult:
        tried: list[str] = []
        for _ in range(self.max_depth):
            strategy = self._select_next(task.failure_class, tried)
            if strategy is None:
                break
            tried.append(strategy)
            if scorer_fn(task, strategy):
                self.memory.record_success(task.failure_class, strategy)
                return RecursiveTraceResult(True, len(tried), tried)
        return RecursiveTraceResult(False, len(tried), tried)
