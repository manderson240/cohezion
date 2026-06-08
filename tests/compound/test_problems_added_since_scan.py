"""Item 238: problems_added_since_scan() — new problems since a baseline (2026-06-08).

``problems_added_since_scan(problems: list[Problem], baseline_ids: frozenset[str])``
-> ``list[Problem]``:
Returns problems whose ``finding_id`` is NOT in ``baseline_ids``.
These are the "new" findings since the baseline scan was taken.
Preserves input order.  Empty ``baseline_ids`` → all problems returned.
Empty ``problems`` → ``[]``.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns problems ABSENT from baseline (kills impl returning
     problems IN the baseline — i.e. the complement/intersection).
  2. Problems in baseline are excluded.
     Kills an impl that ignores the baseline and returns all problems.
  3. Empty baseline → all problems returned (nothing was previously seen).
     Kills an impl that returns [] when baseline is empty.
  4. Input order preserved among returned problems.
     Kills an impl that sorts or reverses the result.
  5. Empty problems → [].
     Kills an impl that raises or returns None.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_added_since_scan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_problems_absent_from_baseline() -> None:
    """Returns only problems whose finding_id is NOT in the baseline.

    PRIMARY DISCRIMINATOR: kills an impl that returns problems IN the baseline
    (the intersection rather than the difference).
    p0 and p1 are in the baseline; p2 is new.
    """
    p0 = _p("alpha", 0)
    p1 = _p("alpha", 1)
    p2 = _p("alpha", 2)
    baseline = frozenset({p0.finding_id, p1.finding_id})

    result = problems_added_since_scan([p0, p1, p2], baseline)

    assert len(result) == 1, "Only p2 is new; got " + repr(result)
    assert result[0].finding_id == p2.finding_id, (
        "New problem must be p2; got " + repr(result[0].finding_id)
    )


def test_problems_in_baseline_excluded() -> None:
    """Problems with finding_ids in baseline are not returned.

    Kills an impl that returns all problems regardless of baseline.
    """
    problems = [_p("alpha", i) for i in range(4)]
    baseline = frozenset(p.finding_id for p in problems)  # all seen before

    result = problems_added_since_scan(problems, baseline)

    assert result == [], "All problems in baseline → result must be []; got " + repr(result)


def test_empty_baseline_returns_all_problems() -> None:
    """Empty baseline → all problems are new.

    Kills an impl that returns [] when baseline is empty (mistaking empty
    baseline for "everything was seen before").
    """
    problems = [_p("alpha", i) for i in range(3)]

    result = problems_added_since_scan(problems, frozenset())

    assert len(result) == 3, (
        "Empty baseline → all 3 problems are new; got " + repr(len(result))
    )


def test_order_preserved_in_result() -> None:
    """New problems appear in original input order.

    Kills an impl that sorts or reverses the result.
    """
    p0 = Problem(problem_class="alpha", finding_id="alpha:z")
    p1 = Problem(problem_class="alpha", finding_id="alpha:a")
    p2 = Problem(problem_class="alpha", finding_id="alpha:m")
    baseline = frozenset({p0.finding_id})  # p0 is old; p1, p2 are new

    result = problems_added_since_scan([p0, p1, p2], baseline)

    assert len(result) == 2
    assert result[0].finding_id == "alpha:a", (
        "p1 (first new in input order) must be first; got " + repr(result[0].finding_id)
    )
    assert result[1].finding_id == "alpha:m", (
        "p2 must be second; got " + repr(result[1].finding_id)
    )


def test_empty_problems_returns_empty_list() -> None:
    """Empty problems → [].

    Kills an impl that raises or returns None.
    """
    baseline = frozenset({"alpha:0", "beta:1"})
    result = problems_added_since_scan([], baseline)
    assert result == [], "Empty problems → []; got " + repr(result)
