"""Unit tests for Master Trace-to-Loop/Goal Refactoring Engine."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from cohezion.compound.graph_loop_refactor import (
    BipartiteEdgeType,
    GoalLoopGraph,
    GoalNode,
    LoopNode,
    TraceRefactorEngine,
)
from scripts.ops.master_trace_refactor_loops_goals import (
    execute_autonomous_goal_loops,
    ingest_all_raw_traces,
)


def test_ingest_all_raw_traces_includes_active_session() -> None:
    events = ingest_all_raw_traces()
    assert len(events) >= 30
    intents = {e["intent"] for e in events}
    # Historical September session intents
    assert "gemma4_adk_agent_governance" in intents
    assert "biohub_cell_tracking_tra_maximization" in intents
    assert "rsna_knee_roc_auc_rank_maximization" in intents
    assert "arc_prize_world_model_synthesis" in intents
    assert "casmi26_cheminformatics_discovery" in intents
    # Active October 1-6 Grandmaster session intents
    assert "arc3_macro_go_explore_quota_ascent" in intents
    assert "rsna_knee_v26_32slice_calibration" in intents
    assert "arc2_monotonic_improvement_invariant" in intents
    assert "casmi26_unclipped_cleavage_fusion" in intents
    assert "two_party_cryptographic_ivv_separation" in intents
    assert "continuous_experiential_learning_pipeline" in intents
    assert "host_oom_and_swap_reclamation" in intents
    # Active October 19 Grandmaster dogfooding & benchmark intents
    assert "dogfooding_integration_roadmap_saturation" in intents
    assert "gaia_agentic_benchmark_suite" in intents
    assert "arc2_v20_zero_mutual_information" in intents
    assert "differential_runtime_monitoring_scc" in intents


def test_bipartite_graph_synthesis_and_mdl_compression() -> None:
    raw_events = ingest_all_raw_traces()
    engine = TraceRefactorEngine()
    graph = engine.refactor(raw_events)

    assert len(graph.goal_nodes) >= 10
    assert len(graph.loop_nodes) >= 10
    assert len(graph.edges) >= 20

    # Verify strictly bipartite structure (no goal->goal or loop->loop edges)
    for edge in graph.edges:
        is_goal_to_loop = edge.source_id in graph.goal_nodes and edge.target_id in graph.loop_nodes
        is_loop_to_goal = edge.source_id in graph.loop_nodes and edge.target_id in graph.goal_nodes
        assert is_goal_to_loop or is_loop_to_goal, f"Non-bipartite edge detected: {edge}"

    # Verify MDL compression ratio
    ratio = graph.calculate_compression_ratio(raw_events)
    assert ratio > 1.5


def test_autonomous_loops_convergence_and_lyapunov_descent() -> None:
    engine = TraceRefactorEngine()
    test_events = [
        {
            "timestamp": "2026-09-25T00:00:00Z",
            "intent": "gemma4_fix",
            "action": "inspect",
            "observation": "PathTraversalError",
            "success": False,
        },
        {
            "timestamp": "2026-09-25T00:01:00Z",
            "intent": "gemma4_fix",
            "action": "patch",
            "observation": "removed .. traversal",
            "success": True,
        },
    ]
    graph = engine.refactor(test_events)
    assert len(graph.goal_nodes) == 1
    goal = list(graph.goal_nodes.values())[0]

    results = execute_autonomous_goal_loops(graph)
    assert len(results) == 1
    assert results[0]["converged"] is True
    assert goal.lyapunov_potential == 0.0
    assert goal.status == "satisfied"
