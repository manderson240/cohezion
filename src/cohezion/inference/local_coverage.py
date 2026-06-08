"""Local-fleet coverage report (item 45, thread E) — report-only.

Routes a representative query set through ``FleetRoutingSpecialist.route`` (item 34) and reports the
"$0 front-door coverage" metric: how much of the task space the local fleet serves WITHOUT cloud.
Pure — no inference is executed; ``route`` only classifies + looks up the registry, and the gate /
budget are injected, so the report is deterministic.

Buckets partition the query set:
  - ``local``     — routed to a local $0 specialist and NOT escalated (served on the box, free),
  - ``escalated`` — a local specialist exists but the gate failed AND budget>0 (cloud advised),
  - ``fallback``  — no local specialist (unclassifiable, or classifiable with no $0 lane).
``coverage = local / total`` (0.0 for an empty query set — no division by zero).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cohezion.inference.fleet_routing_specialist import FleetRoutingSpecialist
from cohezion.inference.registry import ModelEntry


# ---------------------------------------------------------------------------
# Item 98 — Model use-case coverage (the INVERSE of item-62 coverage_gaps)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsecaseCoverageReport:
    """Audit of whether every served fleet model maps to ≥1 Task (item 98). Report-only.

    Attributes
    ----------
    covered:
        Served model_ids that have ≥1 Task in their ``task_affinity`` — they earn
        a routing slot in the local fleet.
    no_usecase:
        Served model_ids with empty ``task_affinity`` OR not present in the registry
        at all — they occupy compute with no routing purpose.
    """

    covered: frozenset[str]
    no_usecase: frozenset[str]


def model_usecase_coverage(
    served_models: Iterable[str],
    registry: Iterable[ModelEntry],
) -> UsecaseCoverageReport:
    """Audit which served fleet models map to ≥1 Task and which have no routing purpose (item 98).

    The INVERSE of item-62 ``coverage_gaps``: that function asks "which Tasks have no local
    specialist?"; this function asks "which served models serve no Task?" — two orthogonal
    diagnostic axes over the same fleet.

    Args:
        served_models: model_ids currently being served (e.g. from the :13305 roster).
            Injected — no live serving call is made.
        registry: the fleet registry entries.  Injected — use the live
            ``get_registry().models.values()`` at call sites or a stub for tests.

    Returns:
        A :class:`UsecaseCoverageReport` with:

        - ``covered``   — served model_ids mapped to ≥1 Task via ``task_affinity``.
        - ``no_usecase`` — served model_ids with empty affinity OR absent from registry.

        A model in the registry but NOT in ``served_models`` appears in NEITHER set
        (that model's routing coverage is item 62's concern, not ours).
        Empty ``served_models`` → both sets empty (no ZeroDivision).

    Pure (injected inputs; no inference, no registry singleton call).
    """
    registry_by_id: dict[str, ModelEntry] = {e.model_id: e for e in registry}

    covered: set[str] = set()
    no_usecase: set[str] = set()

    for model_id in served_models:
        entry = registry_by_id.get(model_id)
        if entry is not None and entry.task_affinity:
            covered.add(model_id)
        else:
            no_usecase.add(model_id)

    return UsecaseCoverageReport(
        covered=frozenset(covered),
        no_usecase=frozenset(no_usecase),
    )


@dataclass(frozen=True)
class LocalCoverageReport:
    """The $0 front-door coverage of the local fleet over a query set. Report-only."""

    local: int
    fallback: int
    escalated: int
    coverage: float  # local / total


def local_coverage_report(
    queries: Iterable[str],
    *,
    budget_usd: float = 0.0,
    local_quality_gate: Callable[[ModelEntry], bool] | None = None,
    specialist: FleetRoutingSpecialist | None = None,
) -> LocalCoverageReport:
    """Bucket each query's route into local / fallback / escalated and report coverage. Pure."""
    spec = specialist or FleetRoutingSpecialist()
    qlist = list(queries)
    local = fallback = escalated = 0
    for q in qlist:
        decision = spec.route(q, budget_usd=budget_usd, local_quality_gate=local_quality_gate)
        if decision.model_id is None:
            fallback += 1
        elif decision.escalate:
            escalated += 1
        else:
            local += 1
    coverage = local / len(qlist) if qlist else 0.0
    return LocalCoverageReport(
        local=local, fallback=fallback, escalated=escalated, coverage=coverage
    )


def coverage_gaps(
    queries: Iterable[str],
    *,
    budget_usd: float = 0.0,
    local_quality_gate: Callable[[ModelEntry], bool] | None = None,
    specialist: FleetRoutingSpecialist | None = None,
) -> set[str]:
    """Task classes that route to FALLBACK *with a task set* — the "register a specialist" list (item 62).

    Splits item-45's ``fallback`` bucket into its two causes and keeps only the actionable one: a GAP
    is a query that classified to a task (``task is not None``) but found NO local $0 specialist
    (``model_id is None``) — a missing-specialist hole the specialist thread (38/57) should fill. An
    UNCLASSIFIABLE query (``task is None``) is a complexity-router fallback, NOT a task gap, so it is
    excluded (an impl that lumps all ``model_id is None`` fallbacks would wrongly include it). Returns
    the deduplicated SET of gap task names. Pure — ``route`` only classifies + looks up the registry.
    """
    spec = specialist or FleetRoutingSpecialist()
    gaps: set[str] = set()
    for q in queries:
        decision = spec.route(q, budget_usd=budget_usd, local_quality_gate=local_quality_gate)
        if decision.model_id is None and decision.task is not None:
            gaps.add(decision.task)
    return gaps


def coverage_gap_delta(
    before: set[str],
    after: set[str],
) -> dict[str, set[str]]:
    """Delta between two item-62 ``coverage_gaps`` snapshots — the gap-closure tracker (item 94).

    Args:
        before: Task-gap set from an earlier ``coverage_gaps`` call.
        after:  Task-gap set from a later ``coverage_gaps`` call.

    Returns:
        A dict with two keys:

        - ``"filled"``: gaps present in ``before`` but absent in ``after`` — a local specialist
          was registered for the task between the two scans (the fleet improved coverage).
        - ``"opened"``: gaps absent in ``before`` but present in ``after`` — a new coverage
          hole appeared (a new Task was added without a specialist, or one was removed).

        Gaps present in BOTH snapshots appear in NEITHER list (stable unresolved gaps).
        Identical snapshots → both sets empty.

    Pure (operates on injected sets; no inference, no registry read).
    """
    return {
        "filled": before - after,  # in before but not after → gap was closed
        "opened": after - before,  # in after but not before → new gap appeared
    }
