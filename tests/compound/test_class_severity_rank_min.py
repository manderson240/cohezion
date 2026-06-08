"""Item 700: class_severity_rank_min() -- min severity rank per class as int.

Floor severity by rank.  class_severity_rank_min(problems) -> dict[str, int].
Unknown severities rank as 0 (so unknown = INFO floor).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns MIN rank NOT max; class A: CRITICAL(4),HIGH(3),INFO(0) -> min=0;
     max-impl gives 4 wrong; count-impl gives 3 wrong.
  2. Single problem -> min = its rank.
  3. Empty -> {}.
  4. Multiple classes, independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_min


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_min_not_max_primary_discriminator() -> None:
    """PRIMARY DISC.: MIN rank NOT max.

    class A: CRITICAL(4),HIGH(3),INFO(0) -> min_rank=0.
    max-impl gives 4 wrong; count-impl gives 3 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "INFO")]
    result = class_severity_rank_min(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    assert result["A"] == 0, (
        f"INFO=0 is min; got {result['A']} (max=4 wrong, count=3 wrong)"
    )
    assert isinstance(result["A"], int), f"Must be int; got {type(result['A'])}"


def test_single_problem_min_is_its_rank() -> None:
    """Single problem -> min = its rank."""
    problems = [_p("B", "MEDIUM")]
    result = class_severity_rank_min(problems)
    assert result["B"] == 2, f"MEDIUM rank=2; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_min([]) == {}


def test_multiple_classes_independent() -> None:
    """Different classes computed independently."""
    problems = [_p("C", "CRITICAL"), _p("C", "HIGH")]  # C: min(4,3)=3
    problems += [_p("D", "LOW"), _p("D", "MEDIUM"), _p("D", "INFO")]  # D: min(1,2,0)=0
    result = class_severity_rank_min(problems)
    assert result["C"] == 3, f"C: min(CRIT=4,HIGH=3)=3; got {result.get('C')}"
    assert result["D"] == 0, f"D: min(LOW=1,MED=2,INFO=0)=0; got {result.get('D')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    result = class_severity_rank_min([_p("E", "HIGH"), _p("E", "LOW")])
    assert isinstance(result["E"], int), f"Must be int; got {type(result['E'])}"
