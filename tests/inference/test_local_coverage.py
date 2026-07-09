"""Discriminating tests for the local-fleet coverage report (item 45, thread E, 2026-06-06).

`local_coverage_report(queries)` routes a query set through FleetRoutingSpecialist.route (item 34)
and reports {local, fallback, escalated, coverage=local/total} — the "$0 front-door coverage" metric
(how much of the task space the local fleet serves without cloud).

Each test fails a plausible wrong impl:
  - coverage not local/total → test_coverage_k_of_n,
  - counts a gate-fail as escalated regardless of budget (CC2) → test_gate_fail_no_budget_stays_local,
  - div-by-zero / wrong empty handling → test_empty_queries,
  - buckets don't partition (local+fallback+escalated != total) → test_partition.
"""

from __future__ import annotations

from cohezion.inference.fleet_routing_specialist import FleetRoutingSpecialist
from cohezion.inference.local_coverage import local_coverage_report
from cohezion.inference.registry import ModelEntry, Task


# A stub classifier: queries starting "rank" → RERANK (has a local specialist), else unclassifiable.
def _stub_classifier(query: str) -> Task | None:
    return Task.RERANK if query.startswith("rank") else None


def _spec() -> FleetRoutingSpecialist:
    return FleetRoutingSpecialist(classifier=_stub_classifier)


def test_coverage_k_of_n() -> None:
    # 2 of 4 classify to RERANK (a registered local specialist); the other 2 are unclassifiable.
    queries = ["rank a", "rank b", "summarize x", "essay y"]
    rep = local_coverage_report(queries, specialist=_spec())
    assert rep.local == 2
    assert rep.fallback == 2
    assert rep.escalated == 0
    assert rep.coverage == 0.5


def test_all_unclassifiable_coverage_zero() -> None:
    rep = local_coverage_report(["a", "b", "c"], specialist=_spec())
    assert rep.local == 0
    assert rep.fallback == 3
    assert rep.coverage == 0.0


def test_gate_fail_plus_budget_counts_escalated() -> None:
    # RERANK has a local specialist, but the gate fails AND budget>0 → escalate (cloud advised).
    rep = local_coverage_report(
        ["rank a", "rank b"],
        specialist=_spec(),
        local_quality_gate=lambda _m: False,
        budget_usd=1.0,
    )
    assert rep.escalated == 2
    assert rep.local == 0
    assert rep.coverage == 0.0  # escalated is NOT local coverage


def test_gate_fail_no_budget_stays_local() -> None:
    # Same gate failure but budget=0 → CC2: stay local ($0 beats cloud), counts as local.
    rep = local_coverage_report(
        ["rank a", "rank b"],
        specialist=_spec(),
        local_quality_gate=lambda _m: False,
        budget_usd=0.0,
    )
    assert rep.escalated == 0
    assert rep.local == 2
    assert rep.coverage == 1.0


def test_empty_queries_coverage_zero() -> None:
    rep = local_coverage_report([], specialist=_spec())
    assert rep.local == 0 and rep.fallback == 0 and rep.escalated == 0
    assert rep.coverage == 0.0  # no div-by-zero


def test_buckets_partition_the_query_set() -> None:
    queries = ["rank a", "rank b", "rank c", "other", "other2"]
    rep = local_coverage_report(
        queries,
        specialist=_spec(),
        local_quality_gate=lambda m: isinstance(m, ModelEntry) and False,
        budget_usd=1.0,
    )
    assert rep.local + rep.fallback + rep.escalated == len(queries)
