"""Item 610: class_min_severity_count() -- minimum per-severity count per class.

``class_min_severity_count(problems) -> dict[str, int]``:
Returns {class: min_per_severity_count} (count of the least frequent severity).
Dual of class_max_severity_count.
Returns INTEGER COUNT, not a severity label.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns count of LEAST frequent severity (not most frequent, not label).
     Class A HIGH=5, LOW=1 -> result['A']==1 (not 5 = max, not 'LOW' = label).
     Kills impl returning max or returning the severity label.
  2. Single-severity class -> its total count (only bucket = min and max).
     Kills impl returning 0 for single bucket.
  3. Uniform 2-severity -> tied count (min==max==either).
     Kills impl computing range (max-min=0) instead of min count.
  4. Empty -> {}.
     Kills impl without empty guard.
  5. Returns int (not float).
     Kills impl applying float division.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_min_severity_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_returns_min_count_not_max_not_label_primary_discriminator() -> None:
    """PRIMARY DISC.: returns count of LEAST frequent severity.

    Class A: HIGH=5, LOW=1 -> min_count=1 (not 5=max, not 'LOW'=label).
    Kills impl returning max count or the label string.
    """
    problems = [_p("A", "HIGH")] * 5 + [_p("A", "LOW")]
    result = class_min_severity_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 1, (
        f"HIGH=5, LOW=1: min_count=1; got {result['A']} (5=max_count wrong, 'LOW'=label wrong)"
    )


def test_single_severity_returns_total_count() -> None:
    """Single severity per class -> min_count equals total count (only bucket).

    Class A: CRITICAL x6 -> min_count=6.
    Kills impl returning 0 thinking 'no second bucket'.
    """
    problems = [_p("A", "CRITICAL")] * 6
    result = class_min_severity_count(problems)
    assert result["A"] == 6, f"6 CRITICAL -> min_count=6; got {result['A']}"


def test_uniform_distribution_returns_tied_count() -> None:
    """Uniform 2-severity -> min_count = either count (both equal).

    Class A: HIGH=3, LOW=3 -> min_count=3 (not range=0, not max=3... same here).
    Kills impl computing max-min (range=0) instead of min (=3).
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 3
    result = class_min_severity_count(problems)
    assert result["A"] == 3, f"Uniform [3,3]: min_count=3; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_min_severity_count([]) == {}


def test_returns_int_not_float() -> None:
    """Return type is int (not float).

    Kills impl using float division or returning a float.
    """
    problems = [_p("A", "HIGH")] * 7 + [_p("A", "LOW")] * 2
    result = class_min_severity_count(problems)
    assert isinstance(result["A"], int), "Value must be int; got " + type(result["A"]).__name__
    assert result["A"] == 2, f"HIGH=7, LOW=2: min_count=2; got {result['A']}"
