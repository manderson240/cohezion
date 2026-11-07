r"""Unit tests for Cohezion Master Orchestrator."""

from __future__ import annotations

from typing import Any

import pytest

from cohezion.core import master_orchestrator
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import EventType
from cohezion.core.master_orchestrator import CohezionMasterOrchestrator


@pytest.fixture
def persistence(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """Stub the two external writes (SurrealDB event log, Obsidian vault + SurrealDB kanban).

    The unit test used to perform both for real, so it passed or failed on whether the runner
    had usable SurrealDB credentials, and wrote to the vault as a side effect.
    """
    calls: dict[str, list[Any]] = {"events": [], "items": []}

    def fake_publish(self: CrossSessionEventBridge, event: Any) -> bool:
        calls["events"].append(event)
        return True

    monkeypatch.setattr(CrossSessionEventBridge, "publish_and_persist", fake_publish)
    monkeypatch.setattr(master_orchestrator, "persist_item", calls["items"].append)
    return calls


def test_master_orchestrator_v_model_cycle(persistence: dict[str, list[Any]]) -> None:
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
    assert outcome.surrealdb_event_published is True
    assert outcome.total_cycle_time_seconds > 0.0

    # The flag must come from the bridge, and the cycle must emit exactly one completion event.
    [event] = persistence["events"]
    assert event.type == EventType.AGENT_COMPLETE
    assert event.source == "MasterOrchestrator"
    [item] = persistence["items"]
    assert item["category"] == "v_model_execution"


def test_publish_failure_is_reported_not_masked(
    persistence: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(CrossSessionEventBridge, "publish_and_persist", lambda self, event: False)
    outcome = CohezionMasterOrchestrator().execute_v_model_cycle(
        task_intent="x", domain="core_architecture"
    )
    assert outcome.surrealdb_event_published is False
