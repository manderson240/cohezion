"""Item 581: fid_problem_density() -- problems per distinct class per fid (2026-06-08).

``fid_problem_density(problems) -> dict[str, float]``:
For each fid, returns total_problems_with_that_fid / distinct_classes_for_that_fid.
FID-axis complement of class_problem_density.
Unweighted.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis; denominator = distinct CLASSES for that fid.
     fid 'fx' in classes A, B, C (1 problem each) -> 3 problems / 3 classes = 1.0.
     class_problem_density would give per-class ratio; fid_problem_density gives per-fid ratio.
     Kills impl reusing class_problem_density on wrong axis.
  2. Denominator = distinct CLASSES (not total problems for that fid).
     fid 'fx' in class A only, 5 times -> density = 5 problems / 1 class = 5.0 (not 5/5=1.0).
     Kills impl dividing by total fid occurrences.
  3. Returns dict[str, float] (not int).
     Kills impl returning integer counts.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Single problem -> density = 1.0 (1 problem / 1 distinct class).
     Kills impl with off-by-one.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_density


def _p(cls: str, fid: str, sev: str = "HIGH") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_denominator_classes_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis; denominator = distinct CLASSES for that fid.

    fid 'fx' appears in classes A, B, C (1 problem each) -> density = 3/3 = 1.0.
    class_problem_density would give per-class ratios, not this.
    Kills impl reusing class_problem_density on wrong axis.
    """
    problems = [
        _p("A", "fx"),  # fx in class A
        _p("B", "fx"),  # fx in class B
        _p("C", "fx"),  # fx in class C
    ]
    result = fid_problem_density(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "fx" in result, f"fid 'fx' must be in result; got {result}"
    assert isinstance(result["fx"], float), (
        f"Density must be float; got {type(result['fx']).__name__}"
    )
    assert abs(result["fx"] - 1.0) < 1e-9, (
        f"3 problems / 3 distinct classes = 1.0; got {result['fx']} "
        f"(class_problem_density would give per-class breakdown, not per-fid)"
    )


def test_denominator_is_distinct_classes_not_total_occurrences() -> None:
    """Denominator = distinct CLASSES (not total fid occurrences).

    fid 'fx' in class A only, 5 times -> 5 problems / 1 distinct class = 5.0.
    Kills impl dividing by total fid occurrences (5/5=1.0 is wrong).
    """
    problems = [_p("A", "fx") for _ in range(5)]  # fx in class A, 5 times
    result = fid_problem_density(problems)
    assert abs(result["fx"] - 5.0) < 1e-9, (
        f"5 problems / 1 distinct class = 5.0; got {result['fx']} "
        f"(1.0 = dividing by total occurrences instead of distinct classes)"
    )


def test_returns_dict_of_float() -> None:
    """Returns dict[str, float] (not dict[str, int]).

    Kills impl returning integer counts.
    """
    problems = [_p("A", "fa"), _p("B", "fa")]
    result = fid_problem_density(problems)
    assert isinstance(result["fa"], float), (
        f"Density must be float; got {type(result['fa']).__name__}"
    )
    assert abs(result["fa"] - 1.0) < 1e-9, (
        f"2 problems / 2 distinct classes = 1.0; got {result['fa']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = fid_problem_density([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_single_problem_density_is_one() -> None:
    """Single problem -> density = 1.0 (1 problem / 1 distinct class).

    Kills impl with off-by-one or wrong initialisation.
    """
    result = fid_problem_density([_p("Z", "fz")])
    assert abs(result["fz"] - 1.0) < 1e-9, f"1 problem / 1 class = 1.0; got {result['fz']}"
