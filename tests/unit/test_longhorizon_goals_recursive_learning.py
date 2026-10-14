"""Unit tests for Master Long-Horizon Autonomous Goals with Recursive Experiential Learning."""

from __future__ import annotations

import pytest

from cohezion.compound.vmodel_compound_graph_system import VModelLevel
from scripts.ops.master_longhorizon_goals_recursive_learning_refactor import (
    build_longhorizon_compound_graph,
    ingest_comprehensive_traces,
    run_recursive_experiential_learning_cycles,
)


def test_ingest_comprehensive_traces_contains_active_trajectories() -> None:
    events = ingest_comprehensive_traces()
    assert len(events) >= 50
    domains = {e.get("domain") for e in events}
    assert "adaptive_resilience" in domains
    assert "highperf_trajectories" in domains
    assert "recursive_learning" in domains


def test_longhorizon_compound_graph_topology_and_vtm() -> None:
    events = ingest_comprehensive_traces()
    graph = build_longhorizon_compound_graph(events)

    # 3 Master Goals + 8 Subsystem Goals
    assert len(graph.goals) == 11
    sys_goals = [g for g in graph.goals.values() if g.vmodel_level == VModelLevel.SYSTEM]
    sub_goals = [g for g in graph.goals.values() if g.vmodel_level == VModelLevel.SUBSYSTEM]
    assert len(sys_goals) == 3
    assert len(sub_goals) == 8

    # 3 Closed Loops
    assert len(graph.loops) == 3

    # 9 Deterministic Proofs
    assert len(graph.proofs) == 9

    # Topological Acyclicity DAG check
    is_dag, order = graph.verify_acyclicity()
    assert is_dag is True
    assert len(order) == len(graph.goals) + len(graph.loops) + len(graph.proofs)

    # VTM 100% formal verification
    vtm = graph.get_verification_traceability_matrix()
    verified_count = sum(1 for v in vtm if v["is_verified"])
    assert verified_count == 11
    assert len(vtm) == 11

    # MDL compression ratio
    ratio = graph.calculate_compression_ratio(len(events))
    assert ratio > 1.30


@pytest.mark.asyncio
async def test_recursive_experiential_learning_cycles() -> None:
    events = ingest_comprehensive_traces()
    graph = build_longhorizon_compound_graph(events)

    results = await run_recursive_experiential_learning_cycles(graph, events)
    assert len(results) == 3

    for r in results:
        # Strict Negentropy proof
        assert r.delta_entropy <= 0.0
        # ZKFV Polynomial Verification
        assert r.zkfv_verified is True
        # CTAC HIHO Coherence
        assert abs(r.ctac_coherence - 0.50) < 0.05
        # AutoHarness AST Score
        assert r.autoharness_score == 1.0

    # Verify that learnings were assembled into the graph
    assert len(graph.learnings) == 3
