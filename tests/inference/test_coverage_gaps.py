"""Discriminating tests for the coverage-gap report (item 62, thread E, 2026-06-06).

`coverage_gaps(queries)` returns the SET of task classes that route to FALLBACK *with a task set* —
classifiable, but no local $0 specialist — the prioritized "register a specialist for these" list
(closes back to specialist thread 38/57). A gap is `model_id is None AND task is not None`; an
UNCLASSIFIABLE query (`task is None`) is a router fallback, NOT a missing-specialist gap.

Composes item-34 `FleetRoutingSpecialist.route`. Pure (no inference). The gap branch can't be
exercised by the real registry (every Task currently has a local $0 specialist), so the discriminating
tests inject a stub specialist returning the REAL `RoutingDecision` objects the production path
constructs; one test uses the real specialist to prove the served/unclassifiable composition.

Each test fails a plausible wrong impl:
  - lumps ALL fallbacks (incl. unclassifiable task=None) as gaps → test_unclassifiable_not_a_gap,
  - calls a served task (model_id set) a gap → test_served_task_not_a_gap,
  - misses a classifiable-no-specialist fallback → test_classifiable_no_specialist_is_gap,
  - doesn't dedup / mishandles empty → test_mixed_dedup / test_empty.
"""

from __future__ import annotations

from cohezion.inference.fleet_routing_specialist import (
    FleetRoutingSpecialist,
    RoutingDecision,
)
from cohezion.inference.local_coverage import coverage_gaps
from cohezion.inference.registry import Task


class _StubSpec:
    """A fake specialist returning crafted (real) RoutingDecision objects, keyed by query."""

    def __init__(self, mapping: dict[str, RoutingDecision]) -> None:
        self._mapping = mapping

    def route(self, query: str, **_kw: object) -> RoutingDecision:
        return self._mapping[query]


def _served(task: str) -> RoutingDecision:
    return RoutingDecision(model_id="m", lane="NPU", task=task, escalate=False, rationale="served")


def _gap(task: str) -> RoutingDecision:
    return RoutingDecision(model_id=None, lane=None, task=task, escalate=False, rationale="no $0")


def _unclassifiable() -> RoutingDecision:
    return RoutingDecision(
        model_id=None, lane=None, task=None, escalate=False, rationale="fallback"
    )


def test_classifiable_no_specialist_is_gap() -> None:
    spec = _StubSpec({"q": _gap("IMAGE_GEN")})
    assert coverage_gaps(["q"], specialist=spec) == {"IMAGE_GEN"}


def test_served_task_not_a_gap() -> None:
    spec = _StubSpec({"q": _served("RERANK")})
    assert coverage_gaps(["q"], specialist=spec) == set()


def test_unclassifiable_not_a_gap() -> None:
    # task=None (router fallback) must NOT be a gap — kills the impl that lumps all model_id=None.
    spec = _StubSpec({"q": _unclassifiable()})
    assert coverage_gaps(["q"], specialist=spec) == set()


def test_mixed_dedup() -> None:
    spec = _StubSpec(
        {
            "a": _gap("IMAGE_GEN"),
            "b": _gap("IMAGE_GEN"),  # same gap twice → deduped by the set
            "c": _gap("VIDEO_GEN"),
            "d": _served("RERANK"),  # served → excluded
            "e": _unclassifiable(),  # unclassifiable → excluded
        }
    )
    assert coverage_gaps(["a", "b", "c", "d", "e"], specialist=spec) == {"IMAGE_GEN", "VIDEO_GEN"}


def test_empty() -> None:
    assert coverage_gaps([], specialist=_StubSpec({})) == set()


def test_real_composition_served_and_unclassifiable() -> None:
    # Real FleetRoutingSpecialist + a stub classifier: RERANK has a local $0 specialist (served),
    # everything else is unclassifiable (task=None). Neither is a gap → empty set, end-to-end.
    def classifier(q: str) -> Task | None:
        return Task.RERANK if q.startswith("rank") else None

    spec = FleetRoutingSpecialist(classifier=classifier)
    assert coverage_gaps(["rank a", "noise b"], specialist=spec) == set()
