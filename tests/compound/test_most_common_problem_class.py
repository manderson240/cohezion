"""Item 392: most_common_problem_class() — class with the highest record count (2026-06-08).

``most_common_problem_class(problems) -> str | None``:
Returns the problem_class string with the maximum total record count.
Ties broken by class name ascending (lexicographic).
Empty -> None.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the CLASS NAME string, not the count integer.
     Kills impl returning the count from problem_class_histogram.
  2. Tie broken lexicographically ascending (a < b wins).
     Kills impl with non-deterministic or reverse tie-breaking.
  3. Empty input returns None, not '' or raise.
     Kills impl with unguarded min/max on empty dict.
  4. Single-element input returns that class.
     Kills impl that needs >=2 to operate.
  5. Count is total records, not distinct finding_ids.
     Kills impl deduplicating by finding_id before counting.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_common_problem_class,
)


def _p(cls: str, fid: str = "f", sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_class_name_not_count() -> None:
    """Returns the class NAME string, not the integer count.

    PRIMARY DISCRIMINATOR: kills impl returning the count.
    """
    problems = [_p("alpha"), _p("alpha"), _p("beta")]
    result = most_common_problem_class(problems)
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "alpha", "alpha(2) > beta(1) → 'alpha'; got " + repr(result)


def test_tie_broken_lexicographically_ascending() -> None:
    """Ties broken by class name ascending (a wins over b).

    Kills impl with non-deterministic or reverse tie-breaking.
    """
    problems = [_p("b"), _p("b"), _p("a"), _p("a"), _p("c")]
    result = most_common_problem_class(problems)
    assert result == "a", "a and b both have count 2; a < b → 'a'; got " + repr(result)


def test_empty_returns_none() -> None:
    """Empty input returns None without raising.

    Kills impl with unguarded min/max on empty structure.
    """
    assert most_common_problem_class([]) is None


def test_single_element_returns_that_class() -> None:
    """Single element list returns its class.

    Kills impl requiring >=2 problems to function.
    """
    problems = [_p("only")]
    assert most_common_problem_class(problems) == "only"


def test_count_is_total_records_not_distinct_fids() -> None:
    """Count is total records, not distinct finding_id count.

    Kills impl deduplicating by finding_id before counting.
    alpha has 3 records (all same fid); beta has 2 distinct fids → alpha wins.
    """
    problems = [
        _p("alpha", "same-fid"),
        _p("alpha", "same-fid"),
        _p("alpha", "same-fid"),
        _p("beta", "fid-1"),
        _p("beta", "fid-2"),
    ]
    result = most_common_problem_class(problems)
    assert result == "alpha", "alpha(3 records) > beta(2 distinct fids); got " + repr(result)
