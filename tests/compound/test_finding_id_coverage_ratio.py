"""Item 420: finding_id_coverage_ratio() — fraction of records for each fid (2026-06-08).

``finding_id_coverage_ratio(problems) -> dict[str, float]``:
Returns each finding_id mapped to its fraction of total record count.
Values are in (0.0, 1.0]; sum of all values == 1.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on finding_id (not problem_class).
     Kills impl reusing class_coverage_ratio.
  2. Values sum to 1.0 (within float tolerance).
     Kills impl dividing by wrong total.
  3. Single fid -> {fid: 1.0}.
     Validates degenerate case.
  4. Empty -> {} (not ZeroDivisionError).
     Kills impl with unguarded division.
  5. Two-fid dataset -> correct proportions.
     Validates core ratio calculation.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_coverage_ratio,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_keyed_on_finding_id_not_class() -> None:
    """Keys are finding_ids, not problem_class names.

    PRIMARY DISCRIMINATOR: kills impl reusing class_coverage_ratio.
    """
    problems = [_p("fid_a"), _p("fid_a"), _p("fid_b")]
    result = finding_id_coverage_ratio(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "fid_a" in result, "fid_a must be a key; got " + repr(set(result.keys()))
    assert "fid_b" in result
    assert "cls" not in result, "class name must NOT be a key; got " + repr(set(result.keys()))


def test_all_fractions_sum_to_one() -> None:
    """Sum of all fid fractions equals 1.0."""
    problems = [_p("x"), _p("x"), _p("y"), _p("z")]
    result = finding_id_coverage_ratio(problems)
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-9, "Fractions must sum to 1.0; got " + repr(total)


def test_single_fid_returns_one() -> None:
    """Single fid -> {fid: 1.0}."""
    problems = [_p("only"), _p("only")]
    result = finding_id_coverage_ratio(problems)
    assert result == {"only": 1.0}, "Single fid -> 1.0; got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}, not ZeroDivisionError."""
    result = finding_id_coverage_ratio([])
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_two_fid_correct_proportions() -> None:
    """Two-fid dataset returns correct proportions."""
    # 3 records of fid_a, 1 of fid_b -> fid_a=3/4, fid_b=1/4
    problems = [_p("fid_a"), _p("fid_a"), _p("fid_a"), _p("fid_b")]
    result = finding_id_coverage_ratio(problems)
    assert abs(result["fid_a"] - 3 / 4) < 1e-9, "fid_a=3/4; got " + repr(result["fid_a"])
    assert abs(result["fid_b"] - 1 / 4) < 1e-9, "fid_b=1/4; got " + repr(result["fid_b"])
