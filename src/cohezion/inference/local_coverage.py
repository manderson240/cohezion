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
