r"""Unit tests for Cohezion Master Orchestrator.

The live boundaries (hybrid inference router, EventBus/SurrealDB bridge, kanban persistence)
are stubbed: as a unit test this used to make a real inference call (45 s timeout to the
unverified fallback on CI) and require a live SurrealDB, so it failed on every runner without
one. The outcome must still report what the bridge actually returned, in both directions.
"""

from __future__ import annotations

import pytest

import cohezion.core.master_orchestrator as mo
from cohezion.core.master_orchestrator import CohezionMasterOrchestrator
from cohezion.inference.unified_hybrid_router import HybridRouteResponse, TaskClass


INTENT = "Unify Hybrid Swarm Inference with Systems Engineering V-Model Rigor"


def _orchestrator(monkeypatch: pytest.MonkeyPatch, *, published: bool):
    orch = CohezionMasterOrchestrator()
    response = HybridRouteResponse(
        content="ok",
        tier_used="Tier 1 (stub)",
        model_name="stub-model",
        latency_ms=1.0,
        verified=True,
        task_class=next(iter(TaskClass)),
        evi_score=0.9,
    )
    monkeypatch.setattr(orch.router, "route_query", lambda *_a, **_k: response)
    monkeypatch.setattr(orch.event_bridge, "publish_and_persist", lambda _evt: published)
    monkeypatch.setattr(mo, "persist_item", lambda _item: {"surreal": False, "obsidian": False})
    return orch


def test_master_orchestrator_v_model_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    outcome = _orchestrator(monkeypatch, published=True).execute_v_model_cycle(
        task_intent=INTENT, domain="core_architecture"
    )

    assert outcome.task_intent == INTENT
    assert outcome.domain == "core_architecture"
    assert len(outcome.left_side_invariants) == 4
    assert outcome.apex_model_used == "stub-model"
    assert outcome.right_side_autoharness_verified is True
    assert outcome.right_side_zk_proof_valid is True
    assert outcome.system_validation_review_passed is True
    assert outcome.surrealdb_event_published is True
    assert outcome.total_cycle_time_seconds > 0.0


def test_outcome_reports_a_failed_publish(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discriminating: an outcome that always claims success would pass the test above."""
    outcome = _orchestrator(monkeypatch, published=False).execute_v_model_cycle(
        task_intent=INTENT, domain="core_architecture"
    )
    assert outcome.surrealdb_event_published is False
