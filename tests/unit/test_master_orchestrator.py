r"""Unit tests for Cohezion Master Orchestrator.

Hermetic: the router, experience engine, event bridge, harness provisioner and kanban
writer are stubbed. The previous version called the live router (which reached
``deepseek-v4-pro:cloud`` from CI), the live event bridge and SurrealDB, so it failed on
every CI shard where SurrealDB was absent and spent cloud tokens where it was present.
The live path belongs in ``tests/integration/``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import cohezion.core.master_orchestrator as mo
from cohezion.core.master_orchestrator import CohezionMasterOrchestrator


INTENT = "Unify Hybrid Swarm Inference with Systems Engineering V-Model Rigor"


async def _fake_experience(**_kwargs):
    return SimpleNamespace(verified=True, proof_valid=True)


@pytest.fixture
def stubbed(monkeypatch):
    kanban: list[dict] = []
    monkeypatch.setattr(mo, "persist_item", kanban.append)
    orch = CohezionMasterOrchestrator()
    published: list = []
    route = SimpleNamespace(model_name="stub-npu-model", tier_used="Tier 0 (stub)", latency_ms=1.5)
    monkeypatch.setattr(orch.router, "route_query", lambda prompt, force_cloud=False: route)
    monkeypatch.setattr(orch.exp_engine, "process_experience", _fake_experience)
    monkeypatch.setattr(orch.provisioner, "provision_agent_harness", lambda **_kw: None)
    state = {"bridge_returns": True}

    def _publish(evt):
        published.append(evt)
        return state["bridge_returns"]

    monkeypatch.setattr(orch.event_bridge, "publish_and_persist", _publish)
    return SimpleNamespace(orch=orch, published=published, kanban=kanban, state=state)


def test_master_orchestrator_v_model_cycle(stubbed) -> None:
    outcome = stubbed.orch.execute_v_model_cycle(task_intent=INTENT, domain="core_architecture")

    assert outcome.task_intent == INTENT
    assert outcome.domain == "core_architecture"
    assert len(outcome.left_side_invariants) == 4
    assert outcome.apex_model_used == "stub-npu-model"
    assert outcome.right_side_autoharness_verified is True
    assert outcome.right_side_zk_proof_valid is True
    assert outcome.system_validation_review_passed is True
    assert outcome.surrealdb_event_published is True
    assert outcome.total_cycle_time_seconds > 0.0
    # The cycle's result is consumed: one event carrying the routed model, one kanban item.
    assert len(stubbed.published) == 1
    assert stubbed.published[0].payload["result"]["model_used"] == "stub-npu-model"
    assert [k["category"] for k in stubbed.kanban] == ["v_model_execution"]


def test_outcome_reports_a_failed_publish(stubbed) -> None:
    stubbed.state["bridge_returns"] = False
    outcome = stubbed.orch.execute_v_model_cycle(task_intent=INTENT)
    assert outcome.surrealdb_event_published is False
