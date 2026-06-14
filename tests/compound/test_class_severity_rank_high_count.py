"""Item 800: class_severity_rank_high_count() -- count rank>=3 (HIGH/CRITICAL) per class.

class_severity_rank_high_count(problems) -> dict[str, int].
count = count(rank >= 3) per class.
HIGH (rank 3) and CRITICAL (rank 4) included; MEDIUM and below excluded.
Zero-inclusive: class with no HIGH/CRITICAL still appears.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: count not fraction; class A: [HIGH*3,CRIT*2,MEDIUM*1]
     -> high_count=5; high_fraction=5/6 wrong; at_or_above(3)=5 but must be int.
  2. No HIGH/CRITICAL -> 0 (class not excluded).
  3. Multi-class independent.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_high_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_high_count_not_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: count=5 not fraction=5/6; [HIGH*3,CRIT*2,MED*1] -> 5; must be int."""
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "CRITICAL")] * 2 + [_p("A", "MEDIUM")] * 1
    result = class_severity_rank_high_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 5, f"[HIGH*3,CRIT*2,MED*1] -> high_count=5; got {got}"
    assert isinstance(got, int), f"Must be int not float; got {type(got)}"


def test_medium_only_gives_zero_not_excluded() -> None:
    """MEDIUM-only class -> count=0 (class still present)."""
    problems = [_p("B", "MEDIUM")] * 3 + [_p("B", "LOW")] * 2
    result = class_severity_rank_high_count(problems)
    assert "B" in result, "Class B must appear with count=0"
    assert result["B"] == 0, f"No HIGH/CRIT -> 0; got {result['B']}"


def test_multi_class_independent() -> None:
    """Two classes counted independently."""
    problems = (
        [_p("X", "HIGH")] * 2
        + [_p("X", "MEDIUM")]  # 2
        + [_p("Y", "CRITICAL")] * 3  # 3
    )
    result = class_severity_rank_high_count(problems)
    assert result.get("X") == 2, f"X -> 2; got {result.get('X')}"
    assert result.get("Y") == 3, f"Y -> 3; got {result.get('Y')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_high_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "HIGH"), _p("D", "CRITICAL")]
    result = class_severity_rank_high_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
