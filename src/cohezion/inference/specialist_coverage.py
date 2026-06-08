"""Specialist verification-gap report (items 38 + 77, 2026-06-06/08) — report-only.

Item 38 surfaces the gap between two orthogonal registry states for the 6 specialist Tasks:
  - REGISTERED  — a ``ModelEntry`` exists for the Task (additive; items 4/19/21/23/28
    drove this to 6/6).
  - SERVING-VERIFIED — ``verified_working=True``, i.e. the model was actually invoked
    successfully at least once (needs-experiment; currently 0/6, pending lanes-up proofs).

Item 77 adds live-lane reachability: ``specialist_liveness_gaps`` partitions the 6 Tasks
into ``ready`` (lane UP → a verification attempt is possible today) vs ``lane_down`` (lane
DOWN or gap → explains why the verification campaign is stuck). Injectable ``check_fleet_fn``
keeps it deterministic in tests.

A read-only instrument in the family of ``loop_telemetry`` (item 25) and
``skill_adoption_report`` (item 32): pure functions over an injectable ``FleetRegistry``,
no writes, no graph.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cohezion.inference.registry import FleetRegistry, Task, get_registry


# The specialist Task slots added 2026-06-05/06 (see the Task enum comment in registry.py).
# These are the "small-specialist lanes" for_task() can express beyond the 4 Gemma tiers.
SPECIALIST_TASKS: tuple[Task, ...] = (
    Task.EXTRACTION,
    Task.VISION,
    Task.FIM,
    Task.FUNCTION_CALL,
    Task.RERANK,
    Task.OCR_DOC,
)


@dataclass(frozen=True)
class SpecialistCoverage:
    """One specialist Task's coverage row. ``model_id is None`` means a GAP (no model)."""

    task: str
    model_id: str | None
    verified_working: bool


@dataclass(frozen=True)
class SpecialistCoverageReport:
    """Per-Task coverage for the 6 specialist slots — registered vs serving-verified."""

    rows: list[SpecialistCoverage]

    @property
    def gaps(self) -> list[str]:
        """Specialist Tasks with NO registered model (the true coverage holes)."""
        return [r.task for r in self.rows if r.model_id is None]

    @property
    def registered(self) -> list[SpecialistCoverage]:
        """Tasks that have a model (a gap is not registered)."""
        return [r for r in self.rows if r.model_id is not None]

    @property
    def verified(self) -> list[SpecialistCoverage]:
        """Registered AND serving-verified."""
        return [r for r in self.rows if r.model_id is not None and r.verified_working]

    @property
    def unverified(self) -> list[SpecialistCoverage]:
        """Registered but NOT serving-verified — the gap the report exists to surface."""
        return [r for r in self.rows if r.model_id is not None and not r.verified_working]


def specialist_coverage_report(
    registry: FleetRegistry | None = None,
) -> SpecialistCoverageReport:
    """Report registered-vs-verified coverage for each specialist Task. Pure/read-only.

    For each specialist Task, reports the priority-preferred (first) ``for_task``
    candidate, or a gap row (``model_id=None``) when no model is registered.
    """
    reg = registry if registry is not None else get_registry()
    rows: list[SpecialistCoverage] = []
    for task in SPECIALIST_TASKS:
        candidates = reg.for_task(task)
        if candidates:
            top = candidates[0]  # priority-sorted: preferred specialist
            rows.append(
                SpecialistCoverage(
                    task=str(task),
                    model_id=top.model_id,
                    verified_working=top.verified_working,
                )
            )
        else:
            rows.append(SpecialistCoverage(task=str(task), model_id=None, verified_working=False))
    return SpecialistCoverageReport(rows=rows)


@dataclass(frozen=True)
class SpecialistCoverageDelta:
    """Signed change in specialist coverage between two snapshots (item 57). Report-only."""

    newly_registered: list[str]  # Tasks that went gap → has-model
    newly_verified: list[str]  # Tasks that went unverified → verified (model_id unchanged)
    regressed: list[str]  # Tasks that LOST verification (verified → unverified)


def specialist_coverage_delta(
    before: SpecialistCoverageReport,
    after: SpecialistCoverageReport,
) -> SpecialistCoverageDelta:
    """Track the specialist verification campaign across two coverage snapshots (item 57).

    Extends item 38 into the harness-blessed pure-delta family (CB11 ``diff_snapshots`` / item-39
    ``loop_progress_delta``). Per Task (matched by name, present in both):
      - ``newly_registered``: a gap (``model_id=None``) gained a model;
      - ``newly_verified``: an unverified specialist flipped to verified (model unchanged);
      - ``regressed``: a verified specialist LOST verification.
    A Task unchanged in both dimensions appears in NO list. Pure — no I/O.
    """
    by_task_before = {r.task: r for r in before.rows}
    newly_registered: list[str] = []
    newly_verified: list[str] = []
    regressed: list[str] = []
    for after_row in after.rows:
        before_row = by_task_before.get(after_row.task)
        if before_row is None:
            continue
        if before_row.model_id is None and after_row.model_id is not None:
            newly_registered.append(after_row.task)
        if not before_row.verified_working and after_row.verified_working:
            newly_verified.append(after_row.task)
        if before_row.verified_working and not after_row.verified_working:
            regressed.append(after_row.task)
    return SpecialistCoverageDelta(
        newly_registered=sorted(newly_registered),
        newly_verified=sorted(newly_verified),
        regressed=sorted(regressed),
    )


# ---------------------------------------------------------------------------
# Item 77 — Specialist liveness gaps (live-lane reachability partition)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecialistLivenessReport:
    """Partition of specialist Tasks by live-lane reachability (item 77). Report-only.

    ``ready`` tasks: the specialist's lane is UP today — a verification attempt is
    feasible right now.  ``lane_down`` tasks: the lane is DOWN or the Task has no
    registered model (gap) — explains why the verification campaign is stuck.

    Invariant: ``{r.task for r in ready} ∩ {r.task for r in lane_down} == ∅``
    Invariant: ``len(ready) + len(lane_down) == len(SPECIALIST_TASKS)``
    """

    ready: list[SpecialistCoverage]  # lane UP → verification possible
    lane_down: list[SpecialistCoverage]  # lane DOWN or gap → can't test now

    @property
    def unverifiable_tasks(self) -> list[str]:
        """Task names blocked from verification because their lane is down (or gap)."""
        return [r.task for r in self.lane_down]

    @property
    def verifiable_tasks(self) -> list[str]:
        """Task names whose lane is currently UP — verification attempts are possible."""
        return [r.task for r in self.ready]


def specialist_liveness_gaps(
    *,
    registry: FleetRegistry | None = None,
    check_fleet_fn: Callable[[], Any] | None = None,
) -> SpecialistLivenessReport:
    """Partition specialist Tasks by live-lane reachability (item 77). Pure/read-only.

    Composes item-38 ``specialist_coverage_report`` with ``FleetRegistry.audit_liveness``
    to answer the operator question: *which specialist Tasks can even be verified right now?*

    A specialist Task is ``ready`` when its registered model's lane is live (``live_status
    == "up"``).  It is ``lane_down`` when: (a) the Task has no registered model (gap), or
    (b) the lane hosting its model is unreachable or unknown.

    Args:
        registry: injectable ``FleetRegistry`` (module singleton by default).
        check_fleet_fn: injectable no-arg callable that returns a health object with a
            ``.lanes`` dict matching the ``FleetRegistry.audit_liveness`` protocol. Defaults
            to ``cohezion.inference.health.check_fleet``. **Always inject in tests** — the
            default triggers live network probes.

    Returns:
        :class:`SpecialistLivenessReport` with ``ready`` and ``lane_down`` partitions.
    """
    reg = registry if registry is not None else get_registry()
    coverage = specialist_coverage_report(reg)
    audit = reg.audit_liveness(check_fleet_fn)

    up_model_ids: frozenset[str] = frozenset(
        item.model_id for item in audit.items if item.live_status == "up"
    )

    ready: list[SpecialistCoverage] = []
    lane_down: list[SpecialistCoverage] = []
    for row in coverage.rows:
        if row.model_id is None:
            lane_down.append(row)  # no model registered — gap always blocks
        elif row.model_id in up_model_ids:
            ready.append(row)
        else:
            lane_down.append(row)

    return SpecialistLivenessReport(ready=ready, lane_down=lane_down)


# ---------------------------------------------------------------------------
# FUTURE HOOKS
# ---------------------------------------------------------------------------
# [ ] Item 77b: expose ``specialist_liveness_gaps`` on the /api/compound/health
#     endpoint alongside ``DegradationDetector.get_health_summary()`` — complete
#     the loop from "lane probe" to "operator dashboard visibility".
# [ ] Item 77c: wire ``SpecialistLivenessReport.unverifiable_tasks`` into the
#     autoresearch loop's campaign planner so it silently skips tasks whose lane
#     is down (rather than surfacing a misleading "can't verify" failure).
# [ ] Item 77d: stream-delta variant — emit a ``SpecialistLivenessReport`` diff
#     on each autoresearch round so the operator can track lane-recovery events.
