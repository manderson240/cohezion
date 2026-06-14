"""Item 332: problems_below_density_threshold() — filter problems from low-density classes (2026-06-08).

``problems_below_density_threshold(problems, threshold) -> list[Problem]``:
Returns Problem objects from classes whose density (count/total) < threshold.
Complement of problems_above_density_threshold.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: threshold > 1.0 returns ALL problems (every density <= 1.0 < threshold).
     Kills impl returning empty when threshold > max density.
  2. threshold=0.0 returns [] (no density can be < 0.0).
     Kills impl returning all problems on zero threshold.
  3. above + below partition: above(t) U below(t) == all problems for 0 < t < 1.
     Kills impl with overlap or gap.
  4. Empty input returns [].
     Kills impl raising on division by zero.
  5. Class at exactly threshold is EXCLUDED from below (strict <, not <=).
     Kills impl using <= instead of <.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_above_density_threshold,
    problems_below_density_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_threshold_above_one_returns_all_problems() -> None:
    """threshold > 1.0 returns ALL problems.

    PRIMARY DISCRIMINATOR: every class density <= 1.0 < threshold, so all qualify.
    Kills impl returning empty when threshold exceeds the max density.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("gamma", 0)]
    result = problems_below_density_threshold(problems, 1.5)
    assert set(p.finding_id for p in result) == {"alpha:0", "beta:0", "gamma:0"}, (
        "threshold=1.5 > any density -> all 3 problems; got " + repr(result)
    )


def test_zero_threshold_returns_empty() -> None:
    """threshold=0.0 returns [].

    No class can have density < 0.0, so nothing qualifies.
    Kills impl returning all problems on zero threshold.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problems_below_density_threshold(problems, 0.0)
    assert result == [], "threshold=0.0 -> nothing qualifies -> []; got " + repr(result)


def test_above_and_below_partition_all_problems() -> None:
    """above(t) + below(t) == all problems for threshold in (0, 1).

    Kills impl with overlap (duplicates) or gap (missing problems).
    alpha×3 (density=0.6), beta×2 (density=0.4); threshold=0.5.
    above: alpha×3. below: beta×2. Union = all 5.
    """
    problems = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("alpha", 1),
        _p("beta", 1),
        _p("alpha", 2),
    ]
    above = problems_above_density_threshold(problems, 0.5)
    below = problems_below_density_threshold(problems, 0.5)
    above_ids = {p.finding_id for p in above}
    below_ids = {p.finding_id for p in below}
    all_ids = {p.finding_id for p in problems}
    assert above_ids & below_ids == set(), "above ∩ below must be empty (disjoint)"
    assert above_ids | below_ids == all_ids, "above ∪ below must equal all problems"


def test_empty_input_returns_empty_list() -> None:
    """Empty input returns [] without raising.

    Kills impl raising ZeroDivisionError on empty.
    """
    result = problems_below_density_threshold([], 0.5)
    assert result == [], "empty -> []; got " + repr(result)


def test_class_at_exact_threshold_excluded_from_below() -> None:
    """Class with density == threshold is NOT in below (strict < not <=).

    Kills impl using <= instead of <.
    2 classes, each density=0.5.  threshold=0.5 -> neither is < 0.5 -> [].
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problems_below_density_threshold(problems, 0.5)
    assert result == [], (
        "density=0.5 == threshold=0.5 -> excluded from below (strict <); got " + repr(result)
    )
