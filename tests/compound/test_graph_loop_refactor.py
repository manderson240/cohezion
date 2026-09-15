"""Tests for Trace to Goal-Loop Graph Refactoring Engine.

Validates:
1. Ingestion and segmentation of execution traces.
2. Repair cycle and retry motif detection.
3. Goal and Loop entity synthesis.
4. Bipartite graph construction and invariant checks.
5. Cycle characterization (progressive vs livelock).
6. MDL (Minimum Description Length) compression ratio.
"""

from __future__ import annotations

import pytest

from cohezion.compound.graph_loop_refactor import (
    TraceRefactorEngine,
)


@pytest.fixture
def sample_trace_events() -> list[dict]:
    """Sample linear execution trace with a repair loop and two distinct goals."""
    return [
        # Segment 1: Task A initial attempt -> failure -> diagnose -> repair -> pass
        {
            "timestamp": "2026-09-14T01:00:00Z",
            "action": "execute_test",
            "state": {"status": "start", "error_count": 2},
            "observation": "AssertionError in module_x",
            "intent": "fix_module_x_tests",
            "success": False,
        },
        {
            "timestamp": "2026-09-14T01:01:00Z",
            "action": "diagnose_error",
            "state": {"status": "diagnosing", "error_count": 2},
            "observation": "Found off-by-one error at line 42",
            "intent": "fix_module_x_tests",
            "success": True,
        },
        {
            "timestamp": "2026-09-14T01:02:00Z",
            "action": "apply_patch",
            "state": {"status": "patching", "error_count": 1},
            "observation": "Patch applied cleanly",
            "intent": "fix_module_x_tests",
            "success": True,
        },
        {
            "timestamp": "2026-09-14T01:03:00Z",
            "action": "execute_test",
            "state": {"status": "verifying", "error_count": 0},
            "observation": "All 12 tests passed",
            "intent": "fix_module_x_tests",
            "success": True,
        },
        # Segment 2: Task B optimization
        {
            "timestamp": "2026-09-14T01:04:00Z",
            "action": "profile_benchmark",
            "state": {"status": "benchmarking", "latency_ms": 120.0},
            "observation": "Latency exceeds 50ms budget",
            "intent": "optimize_latency",
            "success": False,
        },
        {
            "timestamp": "2026-09-14T01:05:00Z",
            "action": "vectorize_kernel",
            "state": {"status": "optimizing", "latency_ms": 32.0},
            "observation": "Vectorized AVX-512 path verified",
            "intent": "optimize_latency",
            "success": True,
        },
        {
            "timestamp": "2026-09-14T01:06:00Z",
            "action": "profile_benchmark",
            "state": {"status": "benchmarking", "latency_ms": 32.0},
            "observation": "Latency within budget: 32ms < 50ms",
            "intent": "optimize_latency",
            "success": True,
        },
    ]


def test_segment_trace(sample_trace_events: list[dict]) -> None:
    """Test segmentation based on intention boundaries."""
    engine = TraceRefactorEngine()
    segments = engine.segment_trace(sample_trace_events)

    assert len(segments) == 2
    assert segments[0].intent == "fix_module_x_tests"
    assert len(segments[0].events) == 4
    assert segments[0].terminal_success is True

    assert segments[1].intent == "optimize_latency"
    assert len(segments[1].events) == 3
    assert segments[1].terminal_success is True


def test_detect_repair_cycles(sample_trace_events: list[dict]) -> None:
    """Test detection of repair/retry control motifs."""
    engine = TraceRefactorEngine()
    segments = engine.segment_trace(sample_trace_events)
    repair_loops = engine.detect_repair_cycles(segments[0])

    assert len(repair_loops) == 1
    loop = repair_loops[0]
    assert loop.cycle_pattern == "attempt_diagnose_repair_verify"
    assert loop.converged is True
    assert loop.iteration_count >= 1


def test_refactor_trace_into_bipartite_graph(sample_trace_events: list[dict]) -> None:
    """Test full conversion of linear traces into a bipartite Goal-Loop Graph."""
    engine = TraceRefactorEngine()
    graph = engine.refactor(sample_trace_events)

    # Graph should contain goal nodes and loop nodes
    assert len(graph.goal_nodes) == 2
    assert len(graph.loop_nodes) >= 2

    # Bipartite property: All edges must connect Goal -> Loop or Loop -> Goal
    for edge in graph.edges:
        source_is_goal = edge.source_id in graph.goal_nodes
        source_is_loop = edge.source_id in graph.loop_nodes
        target_is_goal = edge.target_id in graph.goal_nodes
        target_is_loop = edge.target_id in graph.loop_nodes

        assert (source_is_goal and target_is_loop) or (source_is_loop and target_is_goal), (
            f"Edge {edge} violates bipartite constraint!"
        )


def test_mdl_compression_ratio(sample_trace_events: list[dict]) -> None:
    """Test that graph representation compresses linear trace description length."""
    engine = TraceRefactorEngine()
    graph = engine.refactor(sample_trace_events)

    compression_ratio = graph.calculate_compression_ratio(sample_trace_events)
    # 7 events compressed into 2 goals and 2 loops -> ratio > 1.0
    assert compression_ratio > 1.0


def test_cycle_progressiveness(sample_trace_events: list[dict]) -> None:
    """Test progressive vs degenerate livelock cycle classification."""
    engine = TraceRefactorEngine()
    graph = engine.refactor(sample_trace_events)

    for loop in graph.loop_nodes.values():
        progress_score = loop.calculate_progress_score()
        assert progress_score > 0.0
        assert loop.is_progressive is True
        assert loop.is_livelock is False
