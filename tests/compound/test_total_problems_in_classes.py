"""Item 244: total_problems_in_classes() — aggregate count for a class subset (2026-06-08).

``total_problems_in_classes(problems: list[Problem], classes: frozenset[str])``
-> ``int``:
Returns the total number of problems whose ``problem_class`` is in *classes*.
Classes in *classes* that are not present in the scan contribute 0 (no
KeyError).  Empty *classes* → 0.  Empty *problems* → 0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: a class in *classes* but not in the scan contributes 0
     (kills an impl that raises KeyError on missing classes).
  2. Only problems whose class is in *classes* are counted — others excluded.
     Kills an impl that counts all problems regardless of the classes filter.
  3. Empty *classes* → 0.
     Kills an impl that ignores the filter and returns total problem count.
  4. Empty *problems* → 0.
     Kills an impl that raises or returns None.
  5. Correct aggregation: result equals sum of individual class counts.
     Kills an impl that counts by unique finding_id set size instead of raw count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    total_problems_in_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_missing_class_contributes_zero() -> None:
    """A class in *classes* that has no problems in the scan contributes 0.

    PRIMARY DISCRIMINATOR: kills an impl that raises KeyError on missing classes.
    Scan has no "delta" problems; asking for delta must return 0, not raise.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = total_problems_in_classes(problems, frozenset({"alpha", "delta"}))
    # alpha=1, delta=0 → total 1
    assert result == 1, "alpha(1) + delta(0) = 1; got " + repr(result)


def test_only_classes_in_filter_counted() -> None:
    """Problems outside the *classes* filter are not counted.

    Kills an impl that sums all problems regardless of the filter.
    alpha has 2 problems, beta has 3.  Filter = {alpha}.  Result must be 2.
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("beta", 0),
        _p("beta", 1),
        _p("beta", 2),
    ]
    result = total_problems_in_classes(problems, frozenset({"alpha"}))
    assert result == 2, "Only alpha(2) counted; got " + repr(result)


def test_empty_classes_returns_zero() -> None:
    """Empty *classes* → 0.

    Kills an impl that ignores the filter and returns the full problem count.
    """
    problems = [_p("alpha", i) for i in range(5)]
    result = total_problems_in_classes(problems, frozenset())
    assert result == 0, "Empty classes filter → 0; got " + repr(result)


def test_empty_problems_returns_zero() -> None:
    """Empty *problems* → 0.

    Kills an impl that raises or returns None.
    """
    result = total_problems_in_classes([], frozenset({"alpha", "beta"}))
    assert result == 0, "Empty problems → 0; got " + repr(result)


def test_aggregation_equals_sum_of_individual_counts() -> None:
    """Result equals the sum of per-class counts for all classes in the filter.

    Kills an impl that counts unique finding_ids instead of raw occurrences.
    alpha=3, beta=2, gamma=4 (not in filter).  Filter={alpha, beta}. 3+2=5.
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),
        _p("beta", 0),
        _p("beta", 1),
        _p("gamma", 0),
        _p("gamma", 1),
        _p("gamma", 2),
        _p("gamma", 3),
    ]
    result = total_problems_in_classes(problems, frozenset({"alpha", "beta"}))
    assert result == 5, "alpha(3)+beta(2)=5; got " + repr(result)
