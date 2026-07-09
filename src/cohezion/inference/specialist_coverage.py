"""Specialist verification-gap report (item 38, 2026-06-06) — report-only.

Surfaces the gap between two orthogonal registry states for the 6 specialist Tasks:
  - REGISTERED  — a ``ModelEntry`` exists for the Task (additive; items 4/19/21/23/28
    drove this to 6/6).
  - SERVING-VERIFIED — ``verified_working=True``, i.e. the model was actually invoked
    successfully at least once (needs-experiment; currently 0/6, pending lanes-up proofs).

A read-only instrument in the family of ``loop_telemetry`` (item 25) and
``skill_adoption_report`` (item 32): pure function over an injectable ``FleetRegistry``,
no writes, no graph, no live health probe (that is ``FleetRegistry.audit_liveness``).
"""

from __future__ import annotations

from dataclasses import dataclass

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
