"""Item 698: class_severity_rank_max() -- maximum severity rank per class.

class_severity_rank_max(problems) -> dict[str, int].
Returns the _SEVERITY_RANK of the highest-ranked severity present.
CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1, INFO=0.  Unknown=0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns MAX rank int, NOT label string, NOT avg;
     class A: LOW(1),HIGH(3),MEDIUM(2) -> max_rank=3;
     label-impl gives 'HIGH' (str, wrong type); avg-impl gives 2.0 wrong.
  2. Single CRITICAL -> max_rank = 4.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Unknown severity contributes rank 0; still max of all.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_max


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_max_rank_int_not_label_not_avg_primary_discriminator() -> None:
    """PRIMARY DISC.: max rank as int; NOT the label str; NOT avg.

    class A: LOW(1), HIGH(3), MEDIUM(2) -> max_rank=3 (int).
    label-impl gives 'HIGH' (wrong type); avg-impl gives 2.0 wrong.
    """
    problems = [_p("A", "LOW"), _p("A", "HIGH"), _p("A", "MEDIUM")]
    result = class_severity_rank_max(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert result["A"] == 3, f"HIGH=rank3 is max; got {got!r} (label 'HIGH' wrong, avg 2.0 wrong)"
    assert isinstance(result["A"], int), f"Must be int not {type(result['A'])}"


def test_single_critical_gives_four() -> None:
    """Single CRITICAL -> max_rank = 4."""
    problems = [_p("B", "CRITICAL")]
    result = class_severity_rank_max(problems)
    assert result["B"] == 4, f"CRITICAL=4; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_max([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class uses its own maximum."""
    problems = [_p("X", "LOW"), _p("X", "LOW")]  # max=1
    problems += [_p("Y", "CRITICAL"), _p("Y", "INFO")]  # max=4
    result = class_severity_rank_max(problems)
    assert result["X"] == 1, f"X: only LOW -> max=1; got {result.get('X')}"
    assert result["Y"] == 4, f"Y: has CRITICAL -> max=4; got {result.get('Y')}"


def test_unknown_severity_rank_zero_but_lower_than_known() -> None:
    """Unknown severity gets rank 0; known severities still win."""
    problems = [_p("Z", "BOGUS"), _p("Z", "LOW")]  # BOGUS=0, LOW=1 -> max=1
    result = class_severity_rank_max(problems)
    assert result["Z"] == 1, f"LOW(1) > BOGUS(0); max=1; got {result.get('Z')}"
