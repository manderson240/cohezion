"""Unit tests for Trace to Goal-Loop Graph Refactoring Engine.

Tests:
1. Bipartite graph synthesis (Goal nodes, Loop nodes, Bipartite edges).
2. Minimum Description Length (MDL) compression calculation.
3. SurrealQL serialization (UPSERT and RELATE statements).
4. Progressive vs. livelock cycle classification.
5. Edge cases (empty traces, single-event traces).
"""

from __future__ import annotations

import pytest

from cohezion.compound.graph_loop_refactor import (
    BipartiteEdgeType,
    GoalLoopGraph,
    GoalNode,
    LoopNode,
    TraceRefactorEngine,
)


def test_bipartite_graph_synthesis_basic() -> None:
    events = [
        {
            "timestamp": "2026-09-19T00:01:00Z",
            "intent": "memory_sync",
            "action": "check_surrealdb",
            "observation": "table empty",
            "success": False,
        },
        {
            "timestamp": "2026-09-19T00:02:00Z",
            "intent": "memory_sync",
            "action": "upsert_wal",
            "observation": "upserted 10 records",
            "success": True,
        },
    ]

    engine = TraceRefactorEngine()
    graph = engine.refactor(events)

    assert len(graph.goal_nodes) == 1
    assert len(graph.loop_nodes) == 1
    assert len(graph.edges) == 2

    goal = list(graph.goal_nodes.values())[0]
    assert goal.intent == "memory_sync"
    assert goal.status == "satisfied"
    assert goal.lyapunov_potential == 0.0

    loop = list(graph.loop_nodes.values())[0]
    assert loop.converged is True
    assert loop.is_progressive is True
    assert loop.iteration_count == 1


def test_mdl_compression_ratio() -> None:
    events = [
        {
            "timestamp": f"2026-09-19T00:0{i}:00Z",
            "intent": "kaggle_evaluation",
            "action": f"poll_submission_{i}",
            "observation": "evaluating",
            "success": i == 4,
        }
        for i in range(5)
    ]

    engine = TraceRefactorEngine()
    graph = engine.refactor(events)

    compression = graph.calculate_compression_ratio(events)
    assert compression > 1.0  # Must achieve positive MDL compression over raw trace


def test_surrealql_serialization() -> None:
    goal = GoalNode(id="g_test", intent="test_intent", status="satisfied", lyapunov_potential=0.0)
    loop = LoopNode(id="l_test", cycle_pattern="attempt_repair_verify", actions=["act1", "act2"], converged=True)
    graph = GoalLoopGraph()
    graph.add_goal(goal)
    graph.add_loop(loop)
    graph.add_edge(goal.id, loop.id, BipartiteEdgeType.DISPATCHED_TO)
    graph.add_edge(loop.id, goal.id, BipartiteEdgeType.VERIFIES)

    surql = graph.to_surrealql()
    assert "UPSERT goal:g_test CONTENT" in surql
    assert "UPSERT autonomous_loop:l_test CONTENT" in surql
    assert "RELATE goal:g_test->DISPATCHED_TO->autonomous_loop:l_test" in surql
    assert "RELATE autonomous_loop:l_test->VERIFIES->goal:g_test" in surql


def test_progressive_vs_livelock() -> None:
    prog_loop = LoopNode(
        id="l_prog",
        cycle_pattern="direct",
        actions=["a1"],
        converged=True,
        progress_delta=1.0,
    )
    assert prog_loop.is_progressive is True
    assert prog_loop.is_livelock is False

    livelock_loop = LoopNode(
        id="l_stuck",
        cycle_pattern="cycle",
        actions=["a1", "a2"],
        converged=False,
        progress_delta=0.0,
    )
    assert livelock_loop.is_progressive is False
    assert livelock_loop.is_livelock is True


def test_empty_events_refactor() -> None:
    engine = TraceRefactorEngine()
    graph = engine.refactor([])
    assert len(graph.goal_nodes) == 0
    assert len(graph.loop_nodes) == 0
    assert len(graph.edges) == 0
    assert graph.calculate_compression_ratio([]) == 0.0
