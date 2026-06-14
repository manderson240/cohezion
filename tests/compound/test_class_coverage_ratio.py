"""Item 419: class_coverage_ratio() — fraction of records in each class (2026-06-08).

``class_coverage_ratio(problems) -> dict[str, float]``:
Returns each problem_class mapped to its fraction of total record count.
Values are in (0.0, 1.0]; sum of all values == 1.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are FRACTIONS in (0, 1] not integers or percentages.
     Kills impl returning raw counts or 0-100 percentages.
  2. All fractions sum to 1.0 (within float tolerance).
     Kills impl dividing by wrong total (e.g. class count instead of record count).
  3. Single class -> {class: 1.0}.
     Validates degenerate case.
  4. Empty -> {} (not ZeroDivisionError).
     Kills impl with unguarded division.
  5. Two-class dataset -> correct proportions.
     Validates core ratio calculation.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_coverage_ratio,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_fractions_not_counts_or_percentages() -> None:
    """Values are floats in (0, 1], not raw counts or percentages.

    PRIMARY DISCRIMINATOR: kills impl returning counts or 0-100 values.
    """
    problems = [_p("a"), _p("a"), _p("b")]
    result = class_coverage_ratio(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, ratio in result.items():
        assert isinstance(ratio, float), "Values must be float; got " + repr(type(ratio))
        assert 0.0 < ratio <= 1.0, "Fraction must be in (0, 1]; got " + repr(ratio)


def test_all_fractions_sum_to_one() -> None:
    """Sum of all class fractions equals 1.0.

    Kills impl dividing by wrong denominator.
    """
    problems = [_p("x"), _p("x"), _p("y"), _p("z")]
    result = class_coverage_ratio(problems)
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-9, "Fractions must sum to 1.0; got " + repr(total)


def test_single_class_returns_one() -> None:
    """Single class -> {class: 1.0}."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = class_coverage_ratio(problems)
    assert result == {"only": 1.0}, "Single class -> 1.0; got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}, not ZeroDivisionError."""
    result = class_coverage_ratio([])
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_two_class_correct_proportions() -> None:
    """Two-class dataset returns correct proportions."""
    # 2 records in 'big', 1 in 'small' -> big=2/3, small=1/3
    problems = [_p("big"), _p("big"), _p("small")]
    result = class_coverage_ratio(problems)
    assert abs(result["big"] - 2 / 3) < 1e-9, "big=2/3; got " + repr(result["big"])
    assert abs(result["small"] - 1 / 3) < 1e-9, "small=1/3; got " + repr(result["small"])
