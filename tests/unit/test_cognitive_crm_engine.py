"""Unit tests for Cognitive CRM & Agentic Kanban Mesh Engine."""

from __future__ import annotations

import numpy as np

from cohezion.crm.cognitive_crm_engine import CognitiveCRMEngine, KanbanStatus


def test_stakeholder_registration_and_hyperbolic_affinity() -> None:
    crm = CognitiveCRMEngine()
    v1 = np.array([0.1] * 12)
    v2 = np.array([0.15] * 12)
    v_distant = np.array([0.8] * 12)

    s1 = crm.register_stakeholder("s1", "Alice", "org_1", "alice@example.com", intent_vector_12d=v1)
    s2 = crm.register_stakeholder("s2", "Bob", "org_1", "bob@example.com", intent_vector_12d=v2)

    affinity_close = crm.compute_hyperbolic_affinity(v1, v2)
    affinity_far = crm.compute_hyperbolic_affinity(v1, v_distant)

    assert 0.0 < affinity_close <= 1.0
    assert affinity_close > affinity_far  # Close hyperbolic coordinates yield higher affinity


def test_kanban_card_creation_and_topological_gate_rejection() -> None:
    crm = CognitiveCRMEngine()
    card = crm.create_kanban_card("card_1", "Implement Metron Shader", owner_agent="Qwen3-Coder")

    assert card.status == KanbanStatus.BACKLOG

    # Attempt to transition to REVIEW without AST proof hash -> Rejected
    ok, msg = crm.transition_card_status("card_1", KanbanStatus.REVIEW, ast_proof_hash=None)
    assert ok is False
    assert "Missing AutoHarness AST proof hash" in msg

    # Attempt to transition with Sheaf obstruction (dim H^1 > 0) -> Rejected
    ok, msg = crm.transition_card_status(
        "card_1", KanbanStatus.REVIEW, ast_proof_hash="sha256_mock_hash", sheaf_dim_h1=1
    )
    assert ok is False
    assert "Sheaf cohomology obstruction" in msg

    # Transition with valid proof hash, sheaf consensus (H^1=0), and high retention -> Approved
    ok, msg = crm.transition_card_status(
        "card_1",
        KanbanStatus.REVIEW,
        ast_proof_hash="sha256_mock_hash",
        sheaf_dim_h1=0,
        retention_score=0.95,
    )
    assert ok is True
    assert card.status == KanbanStatus.REVIEW
