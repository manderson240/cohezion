"""Item 806: class_severity_rank_medium_count() -- count rank==2 (MEDIUM only) per class.

class_severity_rank_medium_count(problems) -> dict[str, int].
count = count(rank == 2) per class.
LOW (rank 1) and HIGH (rank 3) NOT included; only MEDIUM (rank 2).
Zero-inclusive: class with no MEDIUM still appears.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: MEDIUM only (rank==2); [MED*3,HIGH*2,LOW*1] -> 3; medium_fraction=0.5 wrong; high_count=2 wrong.
  2. HIGH-only class -> 0 (not excluded).
  3. Multi-class independent.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_medium_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_medium_count_not_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: medium_count=3 not fraction=0.5; [MED*3,HIGH*2,LOW*1] -> 3; must be int."""
    problems = [_p("A", "MEDIUM")] * 3 + [_p("A", "HIGH")] * 2 + [_p("A", "LOW")] * 1
    result = class_severity_rank_medium_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 3, f"[MED*3,HIGH*2,LOW*1] -> medium_count=3; got {got}"
    assert isinstance(got, int), f"Must be int not float; got {type(got)}"
    assert got != 2, "Must count MEDIUM (3) not HIGH (2)"


def test_high_only_gives_zero_not_excluded() -> None:
    """HIGH-only class -> count=0 (class still present with zero)."""
    problems = [_p("B", "HIGH")] * 3 + [_p("B", "CRITICAL")] * 2
    result = class_severity_rank_medium_count(problems)
    assert "B" in result, "Class B must appear with count=0"
    assert result["B"] == 0, f"No MEDIUM -> 0; got {result['B']}"


def test_multi_class_independent() -> None:
    """Two classes counted independently."""
    problems = (
        [_p("X", "MEDIUM")] * 4 + [_p("X", "HIGH")] * 1 +
        [_p("Y", "HIGH")] * 3 + [_p("Y", "LOW")] * 2
    )
    result = class_severity_rank_medium_count(problems)
    assert result.get("X") == 4, f"X -> 4; got {result.get('X')}"
    assert result.get("Y") == 0, f"Y -> 0 (no MEDIUM); got {result.get('Y')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_medium_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "MEDIUM"), _p("D", "HIGH")]
    result = class_severity_rank_medium_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
