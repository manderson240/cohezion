"""Item 288: class_co_occurrence_count() — count finding_ids shared by two classes (2026-06-08).

``class_co_occurrence_count(problems, cls_a, cls_b) -> int``:
Returns the number of DISTINCT finding_ids that appear in BOTH cls_a and cls_b.
Counts distinct ids, not Problem instances. Returns 0 if either class is absent.
When cls_a == cls_b, returns the count of distinct ids in that class (intersection
of a set with itself). Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts distinct shared finding_ids, not Problem instances.
     Kills impl that counts rows (Problems) instead of distinct ids.
  2. One class absent -> 0.
     Kills impl raising KeyError on missing class.
  3. cls_a == cls_b -> |ids in that class| (intersection with self).
     Kills impl that hardcodes 0 for same-class queries.
  4. No shared ids -> 0.
     Verifies zero-intersection case.
  5. Empty problems -> 0.
     Kills impl raising on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_co_occurrence_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_distinct_ids_not_problems() -> None:
    """Counts distinct shared finding_ids, not Problem instance count.

    PRIMARY DISCRIMINATOR: kills impl counting rows instead of distinct ids.
    'shared' appears twice in alpha (2 Problems) and once in beta (1 Problem).
    Distinct intersection = {'shared'} -> count = 1, NOT 2 or 3.
    """
    problems = [
        _p("alpha", "shared"),
        _p("alpha", "shared"),   # duplicate — same finding_id, same class
        _p("alpha", "only_alpha"),
        _p("beta", "shared"),
    ]
    result = class_co_occurrence_count(problems, "alpha", "beta")
    assert result == 1, (
        "Distinct shared id count=1 (ignores dup Problem); got " + repr(result)
    )


def test_absent_class_returns_zero() -> None:
    """Returns 0 when one class is absent from problems.

    Kills impl raising KeyError on missing class.
    """
    problems = [_p("alpha", "a1")]
    result = class_co_occurrence_count(problems, "alpha", "nonexistent")
    assert result == 0, (
        "'nonexistent' class absent -> 0; got " + repr(result)
    )


def test_same_class_returns_distinct_id_count() -> None:
    """cls_a == cls_b returns count of distinct ids in that class.

    Kills impl returning 0 for same-class or raising on equal args.
    """
    problems = [
        _p("alpha", "a1"),
        _p("alpha", "a2"),
        _p("alpha", "a1"),  # duplicate
    ]
    result = class_co_occurrence_count(problems, "alpha", "alpha")
    assert result == 2, (
        "alpha has 2 distinct ids -> self-intersection=2; got " + repr(result)
    )


def test_no_shared_ids_returns_zero() -> None:
    """Classes with no shared finding_ids -> 0.

    Verifies the zero-intersection path.
    """
    problems = [
        _p("alpha", "a1"),
        _p("alpha", "a2"),
        _p("beta", "b1"),
        _p("beta", "b2"),
    ]
    result = class_co_occurrence_count(problems, "alpha", "beta")
    assert result == 0, (
        "No shared ids between alpha and beta -> 0; got " + repr(result)
    )


def test_empty_problems_returns_zero() -> None:
    """Empty input -> 0.

    Kills impl raising on empty input.
    """
    result = class_co_occurrence_count([], "alpha", "beta")
    assert result == 0, "Empty input -> 0; got " + repr(result)
