r"""Unit tests for Cohezion Master Orchestrator."""

from __future__ import annotations

from cohezion.core.master_orchestrator import CohezionMasterOrchestrator


def test_master_orchestrator_v_model_cycle() -> None:
    orchestrator = CohezionMasterOrchestrator()
    outcome = orchestrator.execute_v_model_cycle(
        task_intent="Unify Hybrid Swarm Inference with Systems Engineering V-Model Rigor",
        domain="core_architecture",
    )

    assert (
        outcome.task_intent == "Unify Hybrid Swarm Inference with Systems Engineering V-Model Rigor"
    )
    assert outcome.domain == "core_architecture"
    assert len(outcome.left_side_invariants) == 4
    assert outcome.right_side_autoharness_verified is True
    assert outcome.right_side_zk_proof_valid is True
    assert outcome.system_validation_review_passed is True
    # publish_and_persist reports honestly (True only when SurrealDB took the write), so the
    # value depends on live infrastructure this unit test does not control; the event bridge's
    # own tests cover the truth of the flag.
    assert isinstance(outcome.surrealdb_event_published, bool)
    assert outcome.total_cycle_time_seconds > 0.0
