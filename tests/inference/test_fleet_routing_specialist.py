"""Discriminating tests for the Fleet-Routing Specialist (item 34, 2026-06-06).

`FleetRoutingSpecialist.route(query)` composes the task-type classifier + FleetRegistry.for_task
+ extend_claude's escalation semantics: classify → cheapest LOCAL $0 specialist → escalate ONLY
when an injected local quality gate fails AND budget>0 (CC2: $0 local beats cloud).

Each test fails a plausible wrong impl:
  - escalate on gate-fail regardless of budget → T_cc2,
  - escalate on budget>0 regardless of the gate → T_gatepass,
  - never classify (always fall back) → T_classify,
  - never fall back on an unclassifiable query → T_unclassifiable,
  - ignore the injected classifier → T_injected.
"""

from __future__ import annotations

from cohezion.inference.fleet_routing_specialist import (
    _LOCAL_LANES,
    FleetRoutingSpecialist,
)
from cohezion.inference.registry import Task, get_registry


def _expected_local_specialist(task: Task) -> str:
    local = [
        m
        for m in get_registry().for_task(task)
        if m.lane in _LOCAL_LANES and m.cost_per_1k_input_usd == 0.0
    ]
    return min(local, key=lambda m: m.priority).model_id


def test_classifiable_query_routes_to_cheapest_local_specialist() -> None:
    d = FleetRoutingSpecialist().route("rerank these chunks")
    assert d.task == "RERANK"
    assert d.model_id == _expected_local_specialist(Task.RERANK)  # the exact registry pick
    assert d.lane in {lane.name for lane in _LOCAL_LANES}
    assert d.escalate is False  # no gate provided → no escalation


def test_unclassifiable_query_falls_back_to_complexity_router() -> None:
    d = FleetRoutingSpecialist().route("xyzzy plugh foobar")
    assert d.model_id is None and d.task is None
    assert d.escalate is False
    assert "fallback" in d.rationale


def test_escalate_only_when_gate_fails_and_budget_positive() -> None:
    d = FleetRoutingSpecialist().route(
        "rerank these chunks", budget_usd=0.01, local_quality_gate=lambda _m: False
    )
    assert d.escalate is True
    assert d.model_id == _expected_local_specialist(Task.RERANK)  # still proposes the local route


def test_no_escalate_when_budget_zero_even_if_gate_fails() -> None:
    # CC2: $0 local beats cloud — a failed gate with no budget must NOT escalate.
    d = FleetRoutingSpecialist().route(
        "rerank these chunks", budget_usd=0.0, local_quality_gate=lambda _m: False
    )
    assert d.escalate is False


def test_no_escalate_when_gate_passes() -> None:
    d = FleetRoutingSpecialist().route(
        "rerank these chunks", budget_usd=0.01, local_quality_gate=lambda _m: True
    )
    assert d.escalate is False


def test_injected_classifier_is_used() -> None:
    # A wrong impl that ignores the injected classifier (hardcodes the real one) fails: this fake
    # forces RERANK regardless of the query text, so a nonsense query still routes to the specialist.
    spec = FleetRoutingSpecialist(classifier=lambda _q: Task.RERANK)
    d = spec.route("this text would not classify on its own")
    assert d.task == "RERANK"
    assert d.model_id == _expected_local_specialist(Task.RERANK)
