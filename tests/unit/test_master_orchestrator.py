r"""Unit tests for Cohezion Master Orchestrator."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cohezion.core.master_orchestrator import CohezionMasterOrchestrator, VModelExecutionOutcome
from cohezion.core.persistence.surreal_client import InsecureSurrealCredentialsError


TASK_INTENT = "Unify Hybrid Swarm Inference with Systems Engineering V-Model Rigor"


def _run_cycle(surreal_query: AsyncMock) -> VModelExecutionOutcome:
    """Run a cycle with the event_log client stubbed and the kanban sinks (live vault, :8001) off."""
    orchestrator = CohezionMasterOrchestrator()
    with (
        patch.object(
            orchestrator.event_bridge, "surreal_client", SimpleNamespace(query=surreal_query)
        ),
        patch("cohezion.core.master_orchestrator.persist_item"),
    ):
        return orchestrator.execute_v_model_cycle(
            task_intent=TASK_INTENT,
            domain="core_architecture",
        )


def test_master_orchestrator_v_model_cycle() -> None:
    surreal_query = AsyncMock(return_value=[])
    outcome = _run_cycle(surreal_query)

    assert outcome.task_intent == TASK_INTENT
    assert outcome.domain == "core_architecture"
    assert len(outcome.left_side_invariants) == 4
    assert outcome.right_side_autoharness_verified is True
    assert outcome.right_side_zk_proof_valid is True
    assert outcome.system_validation_review_passed is True
    assert outcome.surrealdb_event_published is True
    assert outcome.total_cycle_time_seconds > 0.0

    surreal_query.assert_awaited_once()
    assert "event_log" in surreal_query.call_args.args[0]


def test_v_model_cycle_reports_unpublished_when_credentials_are_refused() -> None:
    """A refused write must read as unpublished, and must not abort the cycle."""
    outcome = _run_cycle(AsyncMock(side_effect=InsecureSurrealCredentialsError("refused")))

    assert outcome.surrealdb_event_published is False
    assert outcome.system_validation_review_passed is True
