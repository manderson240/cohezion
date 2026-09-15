"""Tests for Systems Engineering V-Model Mesh Engine.

Validates:
1. V-Model Level correspondence (L0..L3 <-> R0..R3).
2. Proof obligations and gate invariants.
3. Bottom-vertex AutonomousLoop execution binding.
4. End-to-end V-Model traceability closure.
5. SurrealDB schema queries generation.
"""

from __future__ import annotations

from cohezion.graph.vmodel_mesh import (
    ProofObligation,
    ProofStatus,
    VModelGate,
    VModelLevel,
    VModelMeshEngine,
)


def test_vmodel_level_symmetry() -> None:
    """Validate left-leg specification matches right-leg verification level."""
    assert VModelLevel.L0_OPERATIONAL_INTENT.counterpart == VModelLevel.R0_ACCEPTANCE
    assert VModelLevel.L1_SYSTEM_REQUIREMENT.counterpart == VModelLevel.R1_SYSTEM_QUALIFICATION
    assert VModelLevel.L2_SUBSYSTEM_SPEC.counterpart == VModelLevel.R2_INTEGRATION_CONTRACT
    assert VModelLevel.L3_COMPONENT_CONTRACT.counterpart == VModelLevel.R3_UNIT_AUTOHARNESS
    assert VModelLevel.VERTEX_EXECUTION.counterpart == VModelLevel.VERTEX_EXECUTION


def test_proof_obligation_satisfaction() -> None:
    """Test verification and proof satisfaction mechanics."""
    po = ProofObligation(
        id="po_autoharness_zero_cost",
        formula="cost_ms == 0 and valid_ast == true",
        verifier="autoharness",
    )
    assert po.status == ProofStatus.UNVERIFIED

    po.satisfy(proof_hash="sha256_abcdef123456")
    assert po.status == ProofStatus.SATISFIED
    assert po.proof_hash == "sha256_abcdef123456"


def test_vmodel_gate_evaluation() -> None:
    """Test that a gate requires all obligations to be satisfied."""
    gate = VModelGate(
        id="gate_r3_unit",
        level=VModelLevel.R3_UNIT_AUTOHARNESS,
        name="Unit AutoHarness Invariant Gate",
    )

    po1 = ProofObligation(id="po_1", formula="dim_bounds_ok", verifier="autoharness")
    po2 = ProofObligation(id="po_2", formula="palette_range_ok", verifier="autoharness")

    gate.add_obligation(po1)
    gate.add_obligation(po2)

    assert gate.is_unlocked is False

    po1.satisfy("hash1")
    assert gate.is_unlocked is False  # po2 still pending

    po2.satisfy("hash2")
    assert gate.is_unlocked is True


def test_vmodel_mesh_end_to_end_traceability() -> None:
    """Test full V-Model mesh construction and closure."""
    mesh = VModelMeshEngine()

    # Register left-leg requirements
    mesh.register_spec(
        spec_id="spec_arc_001",
        level=VModelLevel.L1_SYSTEM_REQUIREMENT,
        description="ARC-AGI-2 grid size must be in [1, 30]",
    )

    # Register right-leg verification gate
    gate = mesh.create_gate(
        gate_id="gate_arc_r1",
        level=VModelLevel.R1_SYSTEM_QUALIFICATION,
        name="ARC System Qualification Gate",
    )
    po = ProofObligation(
        id="po_arc_bounds",
        formula="all(1 <= shape <= 30 for g in grids)",
        verifier="autoharness",
    )
    gate.add_obligation(po)
    mesh.register_gate(gate)

    # Link spec across the V
    mesh.link_traceability(spec_id="spec_arc_001", gate_id="gate_arc_r1")

    # Initial state: not closed
    assert mesh.is_level_closed(VModelLevel.L1_SYSTEM_REQUIREMENT) is False

    # Satisfy obligation
    po.satisfy("proof_hash_arc_7788")
    assert mesh.is_level_closed(VModelLevel.L1_SYSTEM_REQUIREMENT) is True


def test_surrealdb_schema_generation() -> None:
    """Test generation of SurrealQL statements for V-Model mesh persistence."""
    mesh = VModelMeshEngine()
    mesh.register_spec(
        spec_id="spec_test_01",
        level=VModelLevel.L0_OPERATIONAL_INTENT,
        description="Autonomous zero-regression self-healing",
    )
    gate = mesh.create_gate(
        gate_id="gate_test_01",
        level=VModelLevel.R0_ACCEPTANCE,
        name="Acceptance Gate",
    )
    po = ProofObligation(id="po_acc", formula="pass_rate == 1.0", verifier="multiperspective")
    po.satisfy("proof_999")
    gate.add_obligation(po)
    mesh.register_gate(gate)
    mesh.link_traceability("spec_test_01", "gate_test_01")

    surql = mesh.to_surrealql()
    assert "vmodel_spec:spec_test_01" in surql
    assert "vmodel_gate:gate_test_01" in surql
    assert "proof_obligation:po_acc" in surql
    assert "RELATE" in surql


def test_vmodel_poincare_hyperbolic_embedding() -> None:
    """Test Poincaré hyperbolic coordinate embedding for V-Model mesh nodes."""
    mesh = VModelMeshEngine()
    mesh.register_spec("spec_0", VModelLevel.L0_OPERATIONAL_INTENT, "Intent")
    mesh.register_spec("spec_1", VModelLevel.L1_SYSTEM_REQUIREMENT, "Requirement")
    gate = mesh.create_gate("gate_0", VModelLevel.R0_ACCEPTANCE, "Acceptance")
    mesh.register_gate(gate)

    kg = mesh.to_knowledge_graph_mesh()
    assert len(kg.nodes) == 3

    for node in kg.nodes.values():
        assert node.embedding is not None
        # All embeddings must strictly satisfy the Poincaré ball boundary constraint: ||u|| < 1.0
        norm = float((node.embedding**2).sum() ** 0.5)
        assert norm < 1.0 - 1e-5

