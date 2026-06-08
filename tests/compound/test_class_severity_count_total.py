"""Item 613: class_severity_count_total() -- total problem count per class.

Returns {class: total_count}.  int.  Counts ALL problems regardless of severity.
Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_count_total


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_total_not_distinct_severities_primary_discriminator() -> None:
    """PRIMARY DISC.: counts ALL problems, not distinct severity labels.

    Class A: HIGH=3, LOW=2 -> total=5 (not 2 = number of distinct severities).
    Kills impl returning severity cardinality (like len(set(severities))).
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 2
    result = class_severity_count_total(problems)
    assert isinstance(result, dict), "Must return dict"
    assert result["A"] == 5, f"3 HIGH + 2 LOW = total 5; got {result['A']}"
    assert isinstance(result["A"], int), "Must be int; got " + type(result["A"]).__name__
    assert result["A"] != 2, "Must return total (5), not distinct severity count (2)"


def test_single_class_single_severity() -> None:
    """Single class, single severity -> its total count."""
    problems = [_p("A", "CRITICAL")] * 4
    result = class_severity_count_total(problems)
    assert result["A"] == 4, f"4 problems -> total=4; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_count_total([]) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes each get independent total counts."""
    problems = [_p("A", "HIGH")] * 3 + [_p("B", "LOW")] * 5
    result = class_severity_count_total(problems)
    assert result["A"] == 3, f"A: 3 problems; got {result['A']}"
    assert result["B"] == 5, f"B: 5 problems; got {result['B']}"


def test_unlabelled_problems_counted_too() -> None:
    """Unlabelled (severity='') problems are counted in total.

    Total = ALL problems, not just labelled ones.
    """
    problems = [_p("A", "HIGH")] * 2 + [_p("A", "")]  # 2 labelled + 1 unlabelled
    result = class_severity_count_total(problems)
    assert result["A"] == 3, f"2 HIGH + 1 unlabelled = total 3; got {result['A']}"
