"""Item 651: class_severity_spread() -- count of distinct severity levels per class.

Returns {class: distinct_severity_count}.
int >= 1.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_spread


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_distinct_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: counts DISTINCT severities, not total problems.

    Class A: CRIT,CRIT,HIGH,LOW -> spread=3 (not 4 total).
    Kills impl counting total problems or fid count.
    """
    problems = [_p("A", "CRITICAL")] * 2 + [_p("A", "HIGH")] + [_p("A", "LOW")]
    result = class_severity_spread(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 3, (
        f"CRIT,CRIT,HIGH,LOW -> 3 distinct severities; got {result['A']} "
        f"(4=total wrong, 1=wrong)"
    )
    assert isinstance(result["A"], int), "Must be int"


def test_single_severity_spread_one() -> None:
    """Single severity -> spread=1."""
    problems = [_p("A", "HIGH")] * 6
    result = class_severity_spread(problems)
    assert result["A"] == 1, f"Single severity -> spread=1; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_spread([]) == {}


def test_all_distinct_severities() -> None:
    """Each problem has a different severity -> spread=N."""
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "MEDIUM"), _p("A", "LOW")]
    result = class_severity_spread(problems)
    assert result["A"] == 4, f"4 distinct severities -> spread=4; got {result['A']}"


def test_multiple_classes_independent_spreads() -> None:
    """Multiple classes each get independent severity spread.

    Class A: CRIT, HIGH -> spread=2.
    Class B: CRIT, HIGH, LOW, INFO -> spread=4.
    """
    problems = (
        [_p("A", "CRITICAL"), _p("A", "HIGH")]
        + [_p("B", "CRITICAL"), _p("B", "HIGH"), _p("B", "LOW"), _p("B", "INFO")]
    )
    result = class_severity_spread(problems)
    assert result["A"] == 2, f"A: CRIT+HIGH -> spread=2; got {result.get('A')}"
    assert result["B"] == 4, f"B: 4 distinct -> spread=4; got {result.get('B')}"
