"""Item 595: fid_class_ratio() -- ratio of distinct classes to total problems per fid (2026-06-08).

``fid_class_ratio(problems) -> dict[str, float]``:
Returns {fid: distinct_classes / total_problems_with_that_fid}.
FID-axis complement of class_fid_ratio.
Reciprocal of fid_problem_density (total_problems / distinct_classes).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: numerator=distinct_classes, denominator=total_problems_with_fid.
     fid_x in classes A,B,C with 1 problem each -> distinct_classes=3, total=3 -> ratio=1.0.
     fid_problem_density would give 3/3=1.0 too (same value, different formula).
     Use asymmetric case: fid_x in A only, 5 times -> ratio=1/5=0.2 (density=5/1=5.0).
     Kills impl reusing fid_problem_density (reciprocal).
  2. FID axis: outer dict keyed by fid name (not class name).
     Kills impl reusing class_fid_ratio on wrong axis.
  3. Denominator=total_problems (not distinct_classes).
     fid_x in A,A,B -> distinct=2, total=3 -> ratio=2/3 (not 2/2=1.0).
     Kills impl dividing by distinct classes count instead of total problems.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns float (not int).
     Kills impl returning integer counts.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_ratio


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_distinct_classes_over_total_problems_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio = distinct_classes / total_problems.

    fid_x in class A only, 5 times -> distinct=1, total=5 -> ratio=0.2.
    fid_problem_density(fid_x) = 5 total / 1 class = 5.0 (inverted).
    Kills impl reusing fid_problem_density (the reciprocal formula).
    """
    problems = [_p("A", "fx") for _ in range(5)]
    result = fid_class_ratio(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "fx" in result, f"fid 'fx' must be in result; got {result}"
    assert abs(result["fx"] - 0.2) < 1e-9, (
        f"1 distinct class / 5 problems = 0.2; got {result['fx']} "
        f"(5.0 = density formula (inverted), i.e. total/distinct)"
    )


def test_fid_axis_not_class_axis() -> None:
    """Outer dict keyed by FID (not class name).

    Kills impl reusing class_fid_ratio on wrong axis.
    """
    problems = [_p("A", "f1"), _p("A", "f2")]
    result = fid_class_ratio(problems)
    assert "f1" in result, f"fid 'f1' must be a key; got {list(result)}"
    assert "f2" in result, f"fid 'f2' must be a key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be a key (FID axis); got {result}"


def test_denominator_is_total_problems_not_distinct_classes() -> None:
    """Denominator = total_problems (not distinct classes count).

    fid_x in A,A,B -> distinct=2, total=3 -> ratio=2/3 ~0.667 (not 2/2=1.0).
    Kills impl dividing by distinct classes count.
    """
    problems = [_p("A", "fx"), _p("A", "fx"), _p("B", "fx")]
    result = fid_class_ratio(problems)
    expected = 2.0 / 3.0
    assert abs(result["fx"] - expected) < 1e-9, (
        f"2 distinct classes / 3 total problems = {expected:.4f}; got {result['fx']} "
        f"(1.0 = dividing by distinct_classes count instead of total)"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = fid_class_ratio([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_returns_float() -> None:
    """Returns dict[str, float] (not int)."""
    problems = [_p("A", "fa"), _p("B", "fa")]
    result = fid_class_ratio(problems)
    assert isinstance(result["fa"], float), (
        f"Ratio must be float; got {type(result['fa']).__name__}"
    )
    assert abs(result["fa"] - 1.0) < 1e-9, (
        f"2 distinct classes / 2 total problems = 1.0; got {result['fa']}"
    )
