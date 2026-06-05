"""Discriminating tests for RecursiveTraceLoop.run() (V-model audit, 2026-06-05).

Pre-registered gate: docs/research/RECURSIVE_TRACE_FALSIFIABLE_GATE_2026-06-05.md

The mechanism under test is failure-class-informed strategy selection. The most
plausible WRONG implementation is "autoresearch with a dedup cache": pick the next
unused strategy in list order, IGNORING the failure map. Every test below is written
to FAIL that wrong impl, not merely to prove run() fires.
"""
from __future__ import annotations

from cohezion.recursive_trace.core import RecursiveTraceLoop, TraceTask


# Map a failure-class to the strategy that fixes it (mirrors OuroborosBridge).
STRATEGIES = ["standard_healer", "contextual_modifier", "semantic_remap", "chain_insertion"]
FAILURE_MAP = {
    "latency": ["semantic_remap"],
    "coherence_drop": ["contextual_modifier"],
    "structural_mismatch": ["chain_insertion"],
}


def _solver(task: TraceTask, strategy: str) -> bool:
    return strategy == task.solving_strategy


def test_failure_map_routes_to_mapped_strategy_first_not_list_order() -> None:
    # Discriminating: failure_class 'latency' maps to 'semantic_remap', which is index 2
    # in STRATEGIES. A map-ignoring impl would try 'standard_healer' (index 0) first and
    # take >1 iteration. The correct impl solves in exactly 1.
    loop = RecursiveTraceLoop(STRATEGIES, FAILURE_MAP)
    task = TraceTask("t1", failure_class="latency", solving_strategy="semantic_remap")
    result = loop.run(task, _solver)
    assert result.solved is True
    assert result.iterations == 1
    assert result.path[0] == "semantic_remap"


def test_dedup_never_retries_a_strategy() -> None:
    # The loop must not repeat strategies. Solver only accepts the last-listed strategy,
    # forcing a full sweep; path must be a permutation with no repeats.
    loop = RecursiveTraceLoop(STRATEGIES, FAILURE_MAP)
    task = TraceTask("t2", failure_class="coherence_drop", solving_strategy="chain_insertion")
    result = loop.run(task, _solver)
    assert result.solved is True
    assert len(result.path) == len(set(result.path))  # no repeats
    assert result.path[0] == "contextual_modifier"     # map consulted first


def test_unsolvable_task_exhausts_and_returns_not_solved() -> None:
    # Discriminates an impl that loops forever or claims success: a task no strategy
    # solves must terminate with solved=False after trying each strategy exactly once.
    loop = RecursiveTraceLoop(STRATEGIES, FAILURE_MAP)
    task = TraceTask("t3", failure_class="latency", solving_strategy="NONEXISTENT")
    result = loop.run(task, _solver)
    assert result.solved is False
    assert result.iterations == len(STRATEGIES)
    assert len(result.path) == len(set(result.path))


def test_unmapped_failure_class_falls_back_without_crashing() -> None:
    # A failure_class with no map entry must not KeyError; falls back to list order.
    loop = RecursiveTraceLoop(STRATEGIES, FAILURE_MAP)
    task = TraceTask("t4", failure_class="unknown_symptom", solving_strategy="standard_healer")
    result = loop.run(task, _solver)
    assert result.solved is True
    assert result.path[0] == "standard_healer"  # first in list order
