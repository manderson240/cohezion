"""Item 239: problems_resolved_since_scan() — resolved problems (2026-06-08).

``problems_resolved_since_scan(baseline: list[Problem], current_ids: frozenset[str])``
-> ``list[Problem]``:
Returns baseline problems whose ``finding_id`` is NOT in ``current_ids``.
These are the findings that were present before but have since been fixed.
Preserves baseline order.  Empty ``current_ids`` → all baseline returned.
Empty ``baseline`` → ``[]``.  Pure; no I/O.

Symmetric complement of ``problems_added_since_scan``.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns baseline problems ABSENT from current_ids (kills
     impl returning problems IN current_ids — the intersection).
  2. Baseline problems in current_ids are excluded (still present, not resolved).
     Kills an impl that ignores current_ids.
  3. Empty current_ids → all baseline returned (everything was resolved).
     Kills an impl that returns [] when current_ids is empty.
  4. Baseline order preserved among returned problems.
     Kills an impl that sorts or reverses.
  5. Empty baseline → [].
     Kills an impl that raises or returns None.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_resolved_since_scan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_baseline_problems_absent_from_current() -> None:
    """Returns baseline problems whose finding_id is NOT in current_ids.

    PRIMARY DISCRIMINATOR: kills an impl that returns problems IN current_ids
    (the set intersection rather than set difference).
    p0 and p1 are still present (in current_ids); p2 is resolved.
    """
    p0 = _p("alpha", 0)
    p1 = _p("alpha", 1)
    p2 = _p("alpha", 2)
    current_ids = frozenset({p0.finding_id, p1.finding_id})

    result = problems_resolved_since_scan([p0, p1, p2], current_ids)

    assert len(result) == 1, "Only p2 is resolved; got " + repr(result)
    assert result[0].finding_id == p2.finding_id, "Resolved problem must be p2; got " + repr(
        result[0].finding_id
    )


def test_baseline_problems_in_current_ids_excluded() -> None:
    """Problems still in current_ids are not considered resolved.

    Kills an impl that ignores current_ids and returns all baseline problems.
    """
    problems = [_p("alpha", i) for i in range(4)]
    current_ids = frozenset(p.finding_id for p in problems)  # all still present

    result = problems_resolved_since_scan(problems, current_ids)

    assert result == [], "All baseline problems still present → result must be []; got " + repr(
        result
    )


def test_empty_current_ids_returns_all_baseline() -> None:
    """Empty current_ids → all baseline problems are resolved.

    Kills an impl that returns [] when current_ids is empty (mistaking empty
    current scan for "nothing resolved").
    """
    baseline = [_p("alpha", i) for i in range(3)]

    result = problems_resolved_since_scan(baseline, frozenset())

    assert len(result) == 3, "Empty current_ids → all 3 baseline problems resolved; got " + repr(
        len(result)
    )


def test_baseline_order_preserved() -> None:
    """Resolved problems appear in baseline order.

    Kills an impl that sorts or reverses.
    """
    p0 = Problem(problem_class="alpha", finding_id="alpha:z")
    p1 = Problem(problem_class="alpha", finding_id="alpha:a")
    p2 = Problem(problem_class="alpha", finding_id="alpha:m")
    current_ids = frozenset({p0.finding_id})  # p0 still present; p1, p2 resolved

    result = problems_resolved_since_scan([p0, p1, p2], current_ids)

    assert len(result) == 2
    assert result[0].finding_id == "alpha:a", (
        "p1 (first resolved in baseline order) must be first; got " + repr(result[0].finding_id)
    )
    assert result[1].finding_id == "alpha:m", "p2 must be second; got " + repr(result[1].finding_id)


def test_empty_baseline_returns_empty_list() -> None:
    """Empty baseline → [].

    Kills an impl that raises or returns None.
    """
    current_ids = frozenset({"alpha:0", "beta:1"})
    result = problems_resolved_since_scan([], current_ids)
    assert result == [], "Empty baseline → []; got " + repr(result)
