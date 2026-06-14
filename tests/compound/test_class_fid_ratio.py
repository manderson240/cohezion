"""Item 594: class_fid_ratio() -- ratio of distinct fids to total problems per class (2026-06-08).

``class_fid_ratio(problems) -> dict[str, float]``:
Returns {class: distinct_fids / total_problems}.
Reciprocal of class_problem_density (which returns total_problems / distinct_fids).
Single-problem class -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: numerator=distinct_fids, denominator=total_problems (NOT the reciprocal).
     Class A: f1 x3 + f2 x1 -> 4 problems, 2 distinct fids -> ratio=2/4=0.5.
     class_problem_density would give 4/2=2.0 (inverted).
     Kills impl reusing class_problem_density without inversion.
  2. Single-problem class -> ratio=1.0 (1 distinct fid / 1 total problem).
     Kills impl with off-by-one or wrong initialisation.
  3. All problems share one fid -> ratio=1/N (not 1.0).
     Class A: same fid repeated 5 times -> 1/5 = 0.2.
     Kills impl treating all repeats as distinct.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns float (not int).
     Kills impl returning integer counts.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_ratio


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_distinct_fids_over_total_problems_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio = distinct_fids / total_problems (NOT total_problems / distinct_fids).

    Class A: f1 appears 3 times + f2 appears once -> 4 total, 2 distinct -> ratio=0.5.
    class_problem_density(A) would give 4/2=2.0 (inverted).
    Kills impl reusing class_problem_density without inverting the formula.
    """
    problems = [_p("A", "f1"), _p("A", "f1"), _p("A", "f1"), _p("A", "f2")]
    result = class_fid_ratio(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class A must be in result; got {result}"
    assert abs(result["A"] - 0.5) < 1e-9, (
        f"2 distinct fids / 4 total problems = 0.5; got {result['A']} "
        f"(2.0 = density formula inverted, i.e. total/distinct)"
    )


def test_single_problem_ratio_is_one() -> None:
    """Single problem -> ratio=1.0 (1 distinct fid / 1 total problem).

    Kills impl with off-by-one or wrong initialisation.
    """
    result = class_fid_ratio([_p("A", "f1")])
    assert abs(result["A"] - 1.0) < 1e-9, (
        f"Single problem: 1 fid / 1 problem = 1.0; got {result['A']}"
    )


def test_same_fid_repeated_ratio_is_reciprocal_of_count() -> None:
    """Same fid repeated N times -> ratio = 1/N (not 1.0).

    Class A: f1 appears 5 times -> 1 distinct fid / 5 total = 0.2.
    Kills impl treating repeated occurrences as distinct fids.
    """
    problems = [_p("A", "f1") for _ in range(5)]
    result = class_fid_ratio(problems)
    assert abs(result["A"] - 0.2) < 1e-9, (
        f"1 distinct fid / 5 total problems = 0.2; got {result['A']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_fid_ratio([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_returns_float() -> None:
    """Returns dict[str, float] (not int).

    Kills impl returning integer counts.
    """
    problems = [_p("A", "f1"), _p("A", "f2")]
    result = class_fid_ratio(problems)
    assert isinstance(result["A"], float), f"Ratio must be float; got {type(result['A']).__name__}"
    assert abs(result["A"] - 1.0) < 1e-9, f"2 distinct fids / 2 problems = 1.0; got {result['A']}"
