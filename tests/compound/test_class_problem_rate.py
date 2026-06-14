"""Item 600: class_problem_rate() -- average problems per distinct fid per class (2026-06-08).

``class_problem_rate(problems) -> dict[str, float]``:
Returns {class: total_problems / distinct_fids}.
Reciprocal of class_fid_ratio (distinct_fids / total_problems).
Measures average problem intensity per fid within each class.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: formula = total_problems / distinct_fids (NOT distinct_fids / total_problems).
     class A with f1 x3 and f2 x1: total=4, distinct=2 -> rate=4/2=2.0.
     class_fid_ratio gives 2/4=0.5 (the exact reciprocal).
     Kills impl reusing class_fid_ratio (would give 0.5 instead of 2.0).
  2. Denominator = distinct_fids (not total problems).
     class A with f1 x5 only: distinct=1, total=5 -> rate=5.0 (not 1.0).
     Kills impl dividing total_problems / total_problems (=1).
  3. Returns float (not int).
     class A with 4 problems, 2 distinct fids -> rate=2.0 (float).
     Kills impl returning integer result.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Multiple classes independent.
     Kills impl computing rate across all classes jointly.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_rate


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_total_over_distinct_fids_primary_discriminator() -> None:
    """PRIMARY DISC.: rate = total_problems / distinct_fids.

    class A: f1 x3, f2 x1 -> total=4, distinct=2 -> rate=4/2=2.0.
    class_fid_ratio gives 2/4=0.5 (reciprocal).
    Kills impl reusing class_fid_ratio formula.
    """
    problems = [_p("A", "f1")] * 3 + [_p("A", "f2")]
    result = class_problem_rate(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {result}"
    assert abs(result["A"] - 2.0) < 1e-9, (
        f"4 total / 2 distinct fids = 2.0; got {result['A']} "
        f"(0.5 = class_fid_ratio reciprocal, wrong formula)"
    )


def test_denominator_is_distinct_fids_not_total() -> None:
    """Denominator = distinct fids (not total problems).

    class A: f1 x5 only -> distinct=1, total=5 -> rate=5.0 (not 1.0).
    Kills impl using total / total = 1 always.
    """
    problems = [_p("A", "f1")] * 5
    result = class_problem_rate(problems)
    assert abs(result["A"] - 5.0) < 1e-9, (
        f"5 total / 1 distinct fid = 5.0; got {result['A']} (1.0 = dividing by total_problems)"
    )


def test_returns_float() -> None:
    """Returns float (not int).

    Kills impl returning integer result.
    """
    problems = [_p("A", "f1")] * 4 + [_p("A", "f2")] * 2
    result = class_problem_rate(problems)
    assert isinstance(result["A"], float), f"Rate must be float; got {type(result['A']).__name__}"
    assert abs(result["A"] - 3.0) < 1e-9, f"6 total / 2 distinct fids = 3.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = class_problem_rate([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_classes_independent() -> None:
    """Multiple classes each compute their own rate independently.

    Kills impl computing rate across all classes.
    """
    problems = (
        [_p("A", "fa")] * 6
        + [_p("A", "fb")] * 2  # A: 8 total, 2 distinct -> 4.0
        + [_p("B", "fc")] * 3  # B: 3 total, 1 distinct -> 3.0
    )
    result = class_problem_rate(problems)
    assert "A" in result and "B" in result, f"Both classes must be present; got {list(result)}"
    assert abs(result["A"] - 4.0) < 1e-9, f"Class A: 8/2=4.0; got {result['A']}"
    assert abs(result["B"] - 3.0) < 1e-9, f"Class B: 3/1=3.0; got {result['B']}"
