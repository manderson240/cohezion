"""Item 615: class_severity_distinct_count() -- cardinality of severity labels per class.

Returns {class: distinct_non_empty_sev_count}.  int.  Unlabelled excluded.
Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_distinct_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_distinct_count_not_total_count_primary_discriminator() -> None:
    """PRIMARY DISC.: counts DISTINCT severity labels, not total problems.

    Class A: HIGH=3, LOW=2 -> distinct=2 (HIGH and LOW), not 5 (total).
    class_severity_count_total would return 5.
    Kills impl returning total problem count.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 2
    result = class_severity_distinct_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert result["A"] == 2, f"HIGH x3, LOW x2 -> 2 distinct labels; got {result['A']}"
    assert isinstance(result["A"], int), "Must be int; got " + type(result["A"]).__name__
    assert result["A"] != 5, "Must return DISTINCT count (2), not total (5)"


def test_single_severity_returns_one() -> None:
    """Single distinct severity -> distinct_count=1."""
    problems = [_p("A", "CRITICAL")] * 7
    result = class_severity_distinct_count(problems)
    assert result["A"] == 1, f"7 CRITICAL (one label) -> distinct=1; got {result['A']}"


def test_three_distinct_severities() -> None:
    """Three distinct severities -> distinct_count=3 regardless of counts."""
    problems = [_p("A", "HIGH")] * 10 + [_p("A", "LOW")] + [_p("A", "CRITICAL")] * 3
    result = class_severity_distinct_count(problems)
    assert result["A"] == 3, f"HIGH, LOW, CRITICAL -> 3 distinct; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_distinct_count([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class counts its own distinct severities independently."""
    problems = [_p("A", "HIGH")] * 2 + [_p("A", "LOW")] * 2 + [_p("B", "CRITICAL")] * 5
    result = class_severity_distinct_count(problems)
    assert result["A"] == 2, f"A: HIGH, LOW -> 2 distinct; got {result['A']}"
    assert result["B"] == 1, f"B: CRITICAL only -> 1 distinct; got {result['B']}"
