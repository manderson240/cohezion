"""Unit tests for V-Model Compound Graph Engineering System."""

from __future__ import annotations

import pytest

from cohezion.compound.vmodel_compound_graph_system import (
    CompoundGraphEngineer,
    DeterministicProofVerifier,
    ExperientialLearningSynthesizer,
    GoalVertex,
    LoopVertex,
    ProofType,
    ProofVertex,
    SystemsVModelArchitect,
    TokenEfficiencyGovernor,
    VModelCompoundGraph,
    VModelEdgeType,
    VModelLevel,
    VModelMasterTraceRefactorEngine,
)


def test_vmodel_graph_structure_and_edge_types() -> None:
    graph = VModelCompoundGraph()
    goal = GoalVertex(
        id="goal_test_sys",
        intent="Test System Intent",
        target_metric="accuracy",
        target_threshold=0.95,
        lyapunov_potential=0.5,
        vmodel_level=VModelLevel.SYSTEM,
    )
    graph.add_goal(goal)

    loop = LoopVertex(
        id="loop_test_1",
        cycle_pattern="PDCA",
        actions=["observe", "act", "verify"],
        converged=True,
        progress_score=1.0,
    )
    graph.add_loop(loop)

    proof = ProofVertex(
        id="proof_test_1",
        theorem_name="Theorem 1: Lyapunov Convergence",
        proof_type=ProofType.LYAPUNOV_POTENTIAL,
        formal_claim="V(s) decreases monotonically",
        proof_certificate_hash="abc123hash",
        verified=True,
        verification_duration_ms=0.1,
    )
    graph.add_proof(proof)

    graph.add_edge("goal_test_sys", "loop_test_1", VModelEdgeType.DISPATCHED_TO)
    graph.add_edge("loop_test_1", "goal_test_sys", VModelEdgeType.PRODUCES)
    graph.add_edge("proof_test_1", "goal_test_sys", VModelEdgeType.VMODEL_VALIDATES)

    assert len(graph.goals) == 1
    assert len(graph.loops) == 1
    assert len(graph.proofs) == 1
    assert len(graph.edges) == 3


def test_vmodel_decomposition_and_traceability_matrix() -> None:
    verifier = DeterministicProofVerifier()
    architect = SystemsVModelArchitect(verifier)
    engineer = CompoundGraphEngineer()
    graph = VModelCompoundGraph()

    sys_goal = GoalVertex(
        id="goal_rsna_sys",
        intent="RSNA Knee ROC-AUC Maximization",
        target_metric="roc_auc",
        target_threshold=0.957,
        lyapunov_potential=0.4,
        vmodel_level=VModelLevel.SYSTEM,
    )
    subsystems = [
        ("Multi-View 3D Alignment", "alignment_score", 1.0),
        ("Kolmogorov Parent Monotonicity", "monotonicity_score", 1.0),
    ]
    sub_goals = architect.decompose_system_goal(sys_goal, subsystems)
    assert len(sub_goals) == 2

    # Verification via deterministic Kolmogorov proof
    valid, cert, dt = verifier.verify_kolmogorov_monotonicity({"Abnormal": 0.92, "ACL": 0.85, "Meniscus": 0.70})
    assert valid is True

    proof = ProofVertex(
        id="proof_kolmogorov_rsna",
        theorem_name="Parent Kolmogorov Monotonicity",
        proof_type=ProofType.GROUP_INVARIANT,
        formal_claim="P(Abnormal) >= max P(k)",
        proof_certificate_hash=cert,
        verified=valid,
        verification_duration_ms=dt,
    )

    loop = LoopVertex(
        id="loop_rsna_1",
        cycle_pattern="PDCA",
        actions=["predict", "project_monotonicity", "evaluate"],
        converged=True,
        progress_score=1.0,
    )

    engineer.assemble_vmodel_trajectory(
        graph, sys_goal, sub_goals, [loop], [proof], []
    )

    vtm = graph.get_verification_traceability_matrix()
    assert len(vtm) == 3  # 1 sys + 2 sub goals
    for entry in vtm:
        assert entry["is_verified"] is True
        assert len(entry["validating_proofs"]) > 0


def test_topological_acyclicity_via_kahns_algorithm() -> None:
    graph = VModelCompoundGraph()
    g1 = GoalVertex(id="g1", intent="Goal 1")
    g2 = GoalVertex(id="g2", intent="Goal 2")
    l1 = LoopVertex(id="l1", cycle_pattern="PDCA", actions=["act"])

    graph.add_goal(g1)
    graph.add_goal(g2)
    graph.add_loop(l1)

    graph.add_edge("g1", "g2", VModelEdgeType.VMODEL_DECOMPOSES)
    graph.add_edge("g2", "l1", VModelEdgeType.DISPATCHED_TO)

    is_dag, order = graph.verify_acyclicity()
    assert is_dag is True
    assert order.index("g1") < order.index("g2")


def test_token_efficiency_governor_deterministic_bypass() -> None:
    gov = TokenEfficiencyGovernor()

    # Deterministic verifier present -> Tier 0 strictly 0 tokens
    tier, tokens = gov.evaluate_delegation("verify_ast_policy", has_deterministic_verifier=True, task_complexity=0.8)
    assert "Tier 0" in tier
    assert tokens == 0.0
    assert gov.tokens_saved_by_deterministic_bypass == 2048

    # Low complexity -> Tier 1 local NPU
    tier_l, tokens_l = gov.evaluate_delegation("parse_json", has_deterministic_verifier=False, task_complexity=0.2)
    assert "Tier 1" in tier_l
    assert tokens_l == 256.0


def test_master_trace_refactor_trajectory_synthesis() -> None:
    engine = VModelMasterTraceRefactorEngine()
    test_traces = [
        {
            "domain": "biohub",
            "intent": "biohub_cell_tracking",
            "action": "mitotic_com_conservation",
            "success": True,
        },
        {
            "domain": "biohub",
            "intent": "biohub_cell_tracking",
            "action": "temporal_persistence_filter",
            "success": True,
        },
        {
            "domain": "kaggriculture",
            "intent": "kaggriculture_market",
            "action": "preemptive_liquidation_freeze",
            "success": True,
        },
    ]

    graph = engine.refactor_traces_into_vmodel_graph(test_traces)
    assert len(graph.goals) >= 6  # 2 sys + 4 sub
    assert len(graph.loops) == 2
    assert len(graph.proofs) >= 4  # 2 proofs per domain
    assert len(graph.learnings) == 2

    # Check SurrealQL serialization
    surrealql = graph.to_surrealql()
    assert "DEFINE TABLE goal" in surrealql
    assert "VMODEL_DECOMPOSES" in surrealql
    assert "VMODEL_VALIDATES" in surrealql
    assert "proof:" in surrealql
