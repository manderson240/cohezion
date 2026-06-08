"""Item 580: class_problem_density() -- problem density per class (2026-06-08).

``class_problem_density(problems) -> dict[str, float]``:
For each class, returns the ratio: total_problems / distinct_fids_in_class.
Measures how concentrated problems are within each class.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: density = problems / distinct_fids (not raw count).
     [A: f1 x3, f2 x1] -> A has 4 problems, 2 distinct fids -> density=2.0.
     Kills impl returning problem count (would give 4.0 not 2.0).
  2. Denominator is DISTINCT fids (not total problems or 1).
     [A: f1 x3] -> 3 problems / 1 distinct fid = 3.0 (not 1.0).
     Kills impl dividing by 1 always.
  3. Empty -> {} (not raise).
     Kills impl without empty guard.
  4. Multiple classes with different densities.
     [A: 4 probs / 2 fids = 2.0], [B: 1 prob / 1 fid = 1.0] distinct.
     Kills impl computing same density for all classes.
  5. Returns float values (not int).
     [A: 1 prob / 2 fids = 0.5] -- kills impl integer division.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_density


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_density_is_problems_per_distinct_fid_primary_discriminator() -> None:
    """PRIMARY DISC.: density = total_problems / distinct_fids (not raw count).

    Class A: f1 appears 3x, f2 appears 1x -> 4 total problems, 2 distinct fids.
    density = 4 / 2 = 2.0 (NOT 4.0 which would be the raw problem count).
    Kills impl returning raw problem count instead of ratio.
    """
    problems = [
        _p("A", "f1", "H"),  # f1: problem 1
        _p("A", "f1", "H"),  # f1: problem 2
        _p("A", "f1", "H"),  # f1: problem 3
        _p("A", "f2", "H"),  # f2: problem 4
    ]
    result = class_problem_density(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class A must be in result; got {result}"
    assert abs(result["A"] - 2.0) < 1e-9, (
        f"A: 4 problems / 2 distinct fids = 2.0; got {result['A']} "
        f"(4.0 = raw count, 2.0 = correct density)"
    )


def test_denominator_is_distinct_fids_not_one() -> None:
    """Denominator is distinct fids count (not always 1).

    Class A: f1 appears 3 times -> 3 problems / 1 distinct fid = 3.0.
    Kills impl always dividing by 1 (would give 3.0 coincidentally here,
    but we cross-check with a multi-fid case).
    """
    problems = [
        _p("A", "f1", "H"),
        _p("A", "f1", "H"),
        _p("A", "f1", "H"),
    ]
    result = class_problem_density(problems)
    assert abs(result["A"] - 3.0) < 1e-9, f"3 problems / 1 fid = 3.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_problem_density([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_classes_different_densities() -> None:
    """Multiple classes with different densities are computed independently.

    [A: 4 problems / 2 fids = 2.0], [B: 1 problem / 1 fid = 1.0].
    Kills impl computing the same density for all classes.
    """
    problems = [
        _p("A", "f1", "H"),  # A: f1 x2, f2 x2 -> 4 probs / 2 fids = 2.0
        _p("A", "f1", "H"),
        _p("A", "f2", "H"),
        _p("A", "f2", "H"),
        _p("B", "f3", "H"),  # B: f3 x1 -> 1 prob / 1 fid = 1.0
    ]
    result = class_problem_density(problems)
    assert abs(result["A"] - 2.0) < 1e-9, f"A: 2.0; got {result['A']}"
    assert abs(result["B"] - 1.0) < 1e-9, f"B: 1.0; got {result['B']}"


def test_float_division_not_integer_division() -> None:
    """Returns float (not int) -- 3 problems / 2 fids = 1.5 (not 1 from int div).

    Kills impl using integer division (//).
    """
    # 3 problems, 2 distinct fids: g1 x2, g2 x1 -> 3/2 = 1.5
    problems = [
        _p("B", "g1", "H"),
        _p("B", "g1", "H"),
        _p("B", "g2", "H"),
    ]
    result = class_problem_density(problems)
    assert abs(result["B"] - 1.5) < 1e-9, (
        f"3 problems / 2 distinct fids = 1.5 (not 1 from int div); got {result['B']}"
    )
