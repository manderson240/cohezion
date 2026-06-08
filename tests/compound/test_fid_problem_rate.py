"""Item 601: fid_problem_rate() -- average problems per distinct class per fid (2026-06-08).

``fid_problem_rate(problems) -> dict[str, float]``:
Returns {fid: total_problems_with_fid / distinct_classes_containing_fid}.
FID-axis complement of class_problem_rate.
Reciprocal of fid_class_ratio (distinct_classes / total_problems).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns total_problems/distinct_classes (NOT distinct_classes/total_problems).
     fid_class_ratio returns distinct_classes/total; class_problem_rate formula is inverted.
     fid_x in A once, B once, C once -> rate=3/3=1.0 (not ratio=3/3=1.0 -- same here, use next).
     fid_y in A x4 only -> rate=4/1=4.0 (not ratio=1/4=0.25 which is fid_class_ratio).
     Kills impl reusing fid_class_ratio or inverting formula.
  2. Denominator is distinct CLASSES (not total_problems).
     fid_x in A x3, B x1 -> 4 total / 2 distinct = 2.0 (not 4/4=1.0 which ignores distinct).
     Kills impl dividing by total_problems.
  3. FID axis (not class axis).
     Result must be keyed by fid name, not class name.
     Kills impl reusing class_problem_rate on wrong axis.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns float (not int).
     Kills impl returning integer division result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_rate


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_total_over_distinct_classes_primary_discriminator() -> None:
    """PRIMARY DISC.: total_problems / distinct_classes (NOT the inverse).

    fid_y in A x4 only -> rate=4.0 (4 total / 1 distinct class).
    fid_class_ratio would give 0.25 (1 distinct / 4 total) -- exact reciprocal.
    Kills impl returning inverse.
    """
    problems = [_p("A", "fy")] * 4
    result = fid_problem_rate(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "fy" in result, f"fid 'fy' must be in result; got {list(result)}"
    assert result["fy"] == 4.0, (
        f"4 problems / 1 class -> rate=4.0; got {result['fy']} (0.25 = fid_class_ratio inverse)"
    )


def test_denominator_is_distinct_classes_not_total() -> None:
    """Denominator is count of DISTINCT classes, not total problems.

    fid_x in A x3, B x1 -> 4 total / 2 distinct_classes = 2.0.
    If denominator were total (4): 4/4=1.0 (wrong).
    Kills impl dividing total / total.
    """
    problems = [_p("A", "fx")] * 3 + [_p("B", "fx")]
    result = fid_problem_rate(problems)
    assert result["fx"] == 2.0, (
        f"4 total / 2 distinct classes -> 2.0; got {result['fx']} "
        f"(1.0 = dividing by total, not distinct_classes)"
    )


def test_fid_axis_not_class_axis() -> None:
    """Result is keyed by fid name, not class name.

    Kills impl reusing class_problem_rate on class axis.
    """
    problems = [_p("A", "f1"), _p("B", "f1"), _p("C", "f2")]
    result = fid_problem_rate(problems)
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "f2" in result, f"fid 'f2' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = fid_problem_rate([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_returns_float() -> None:
    """Return type per fid is float (not int).

    Kills impl using integer division.
    """
    problems = [_p("A", "fx"), _p("B", "fx")]
    result = fid_problem_rate(problems)
    assert isinstance(result["fx"], float), (
        "Value for 'fx' must be float; got " + type(result["fx"]).__name__
    )
