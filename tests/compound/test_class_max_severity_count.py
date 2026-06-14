"""Item 608: class_max_severity_count() -- count of dominant severity per class.

Returns {class: max_per_severity_count}.  int.  NOT the label.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_max_severity_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_returns_count_not_label_primary_discriminator() -> None:
    """PRIMARY DISC.: returns the INTEGER COUNT, not the severity label.

    HIGH=5, LOW=1 -> result['A'] == 5 (not 'HIGH').
    class_top_severity would return 'HIGH'.
    """
    problems = [_p("A", "HIGH")] * 5 + [_p("A", "LOW")]
    result = class_max_severity_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert result["A"] == 5, f"max count=5; got {result['A']}"
    assert isinstance(result["A"], int), "Must be int; got " + type(result["A"]).__name__
    assert result["A"] != "HIGH", "Must return count (5), not label ('HIGH')"


def test_single_severity_returns_its_count() -> None:
    """Single severity -> its count."""
    problems = [_p("A", "CRITICAL")] * 7
    result = class_max_severity_count(problems)
    assert result["A"] == 7, f"7 CRITICAL -> max=7; got {result['A']}"


def test_returns_max_not_min() -> None:
    """Returns MAX count (not min or sum)."""
    problems = [_p("A", "HIGH")] * 4 + [_p("A", "LOW")]
    result = class_max_severity_count(problems)
    assert result["A"] == 4, f"HIGH=4 > LOW=1 -> max=4; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_max_severity_count([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class gets its own max count independently."""
    problems = [_p("A", "HIGH")] * 3 + [_p("B", "LOW")] * 7
    result = class_max_severity_count(problems)
    assert result["A"] == 3, f"A: HIGH=3 -> max=3; got {result['A']}"
    assert result["B"] == 7, f"B: LOW=7 -> max=7; got {result['B']}"
