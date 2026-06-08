"""Item 172: problem_diff() — TIDE findings delta between two scans (2026-06-08).

``problem_diff(before: list[Problem], after: list[Problem])`` → ``ProblemDiff``:
compares two :func:`discover_problems` result lists by ``finding_id`` and classifies
each id into:

- ``added``   — in *after* but NOT in *before*  (new smell introduced).
- ``resolved`` — in *before* but NOT in *after*  (smell fixed).
- ``stable``  — in BOTH before and after         (smell unchanged).

Pure fold; no I/O; no SurrealDB.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: id in after-only → in ``added``.
     Kills an impl that always returns empty ``added``.
  2. id in before-only → in ``resolved``.
     Kills an impl that ignores the resolved partition.
  3. id in both → in ``stable`` (not in added or resolved).
     Kills an impl that puts every before-id in resolved.
  4. Identical inputs → ``added==[]``, ``resolved==[]``, ``stable`` == all ids.
     Kills an impl that treats identical scans as fully different.
  5. Empty inputs → all three partitions empty (no raises).
     Kills an impl that raises on empty lists.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    ProblemDiff,
    problem_diff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_after_only_id_appears_in_added() -> None:
    """id in after but NOT in before → in added.

    PRIMARY DISCRIMINATOR: kills an impl that always returns empty added
    (would make the loop health report unable to detect new smells).
    """
    before: list[Problem] = []
    after = [_p("complexity_outlier")]

    diff = problem_diff(before, after)

    assert "complexity_outlier:0" in diff.added, (
        f"New finding must be in diff.added; got {diff.added!r}"
    )
    assert diff.resolved == [], (
        f"Nothing was in before so resolved must be []; got {diff.resolved!r}"
    )
    assert diff.stable == [], f"No overlap so stable must be []; got {diff.stable!r}"


def test_before_only_id_appears_in_resolved() -> None:
    """id in before but NOT in after → in resolved.

    Kills an impl that ignores the resolved partition (would hide fixed smells
    from the loop health report, making improvements invisible).
    """
    before = [_p("nesting_outlier")]
    after: list[Problem] = []

    diff = problem_diff(before, after)

    assert "nesting_outlier:0" in diff.resolved, (
        f"Removed finding must be in diff.resolved; got {diff.resolved!r}"
    )
    assert diff.added == [], f"Nothing new so added must be []; got {diff.added!r}"
    assert diff.stable == [], f"No overlap so stable must be []; got {diff.stable!r}"


def test_shared_id_appears_in_stable_not_added_or_resolved() -> None:
    """id in both before and after → in stable, NOT in added or resolved.

    Kills an impl that puts every before-id in resolved regardless of whether
    it also appears in after.
    """
    shared = _p("long_function")
    before = [shared]
    after = [shared]

    diff = problem_diff(before, after)

    assert shared.finding_id in diff.stable, (
        f"Shared finding must be in diff.stable; got {diff.stable!r}"
    )
    assert shared.finding_id not in diff.added, (
        f"Shared finding must NOT be in diff.added; got {diff.added!r}"
    )
    assert shared.finding_id not in diff.resolved, (
        f"Shared finding must NOT be in diff.resolved; got {diff.resolved!r}"
    )


def test_identical_inputs_all_stable() -> None:
    """Identical before and after → added=[], resolved=[], stable=all ids.

    Kills an impl that treats identical scans as fully different (e.g., one
    that always puts all ids in added and all in resolved at the same time).
    """
    problems = [_p("compound_smell", i) for i in range(3)]

    diff = problem_diff(problems, problems)

    assert diff.added == [], f"No new findings; got {diff.added!r}"
    assert diff.resolved == [], f"No fixed findings; got {diff.resolved!r}"
    expected_stable = {p.finding_id for p in problems}
    assert set(diff.stable) == expected_stable, (
        f"All findings must be stable; got {diff.stable!r} expected {expected_stable!r}"
    )


def test_empty_inputs_all_partitions_empty() -> None:
    """Both before and after empty → all partitions empty (no raises).

    Kills an impl that raises an IndexError or similar on empty input.
    """
    diff = problem_diff([], [])

    assert diff.added == [], f"Empty inputs → added=[]; got {diff.added!r}"
    assert diff.resolved == [], f"Empty inputs → resolved=[]; got {diff.resolved!r}"
    assert diff.stable == [], f"Empty inputs → stable=[]; got {diff.stable!r}"
    assert isinstance(diff, ProblemDiff), f"Must return ProblemDiff; got {type(diff)}"
