"""Item 127: Discovered-problem delta — report-only (2026-06-08).

``discovered_problem_delta(before, after)`` measures the TIDE iteration progress
across two ``discover_problems`` runs: did debt grow or shrink?

  - ``resolved``: problems in ``before`` but NOT ``after`` (fixed since last scan)
  - ``introduced``: problems in ``after`` but NOT ``before`` (new debt)

A problem present in BOTH is in neither list (still open, neither resolved nor
new).  Comparison is by ``finding_id`` (the stable TIDE identity key), so two
findings with the same ``problem_class`` but different ``finding_id``s are tracked
independently.

Mirrors the harness-blessed ``DegradationDetector.diff_snapshots`` (CB11) and
the item-39/57/74/81 pure-delta pattern family.

Report-only — measures the discovery loop's progress between ticks. Pure (no I/O,
no writes, no LLM).
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.compound.problem_discovery import Problem


@dataclass(frozen=True)
class ProblemDelta:
    """Delta between two problem-discovery scans.

    Attributes:
        resolved:
            Problems that were in the ``before`` scan but NOT in ``after``
            — i.e. fixed or no longer detected since the last scan.
        introduced:
            Problems that are in ``after`` but NOT in ``before``
            — i.e. new debt since the last scan.
    """

    resolved: list[Problem]
    introduced: list[Problem]


def discovered_problem_delta(
    before: list[Problem],
    after: list[Problem],
) -> ProblemDelta:
    """Return the delta between two ``discover_problems`` result lists.

    Args:
        before: Problems from the earlier scan (the baseline).
        after:  Problems from the more recent scan (the current state).

    Returns:
        ``ProblemDelta(resolved, introduced)`` where:
        - ``resolved`` = in ``before`` but not ``after`` (fixed debt).
        - ``introduced`` = in ``after`` but not ``before`` (new debt).
        - A problem in BOTH is in neither list (still open, unchanged).

    Pure — no I/O, no writes.  Report-only.
    """
    # Key by finding_id for set operations (Problem is frozen → hashable).
    before_ids: set[str] = {p.finding_id for p in before}
    after_ids: set[str] = {p.finding_id for p in after}

    # Build lookup maps so we can reconstruct the full Problem objects.
    before_by_id: dict[str, Problem] = {p.finding_id: p for p in before}
    after_by_id: dict[str, Problem] = {p.finding_id: p for p in after}

    resolved_ids = before_ids - after_ids
    introduced_ids = after_ids - before_ids

    return ProblemDelta(
        resolved=sorted(
            (before_by_id[fid] for fid in resolved_ids),
            key=lambda p: p.finding_id,
        ),
        introduced=sorted(
            (after_by_id[fid] for fid in introduced_ids),
            key=lambda p: p.finding_id,
        ),
    )
