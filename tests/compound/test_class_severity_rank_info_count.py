"""Item 804: class_severity_rank_info_count() -- count rank==0 (INFO only) per class.

class_severity_rank_info_count(problems) -> dict[str, int].
count = count(rank == 0) per class.
LOW (rank 1) NOT included; only INFO (rank 0).
Zero-inclusive: class with no INFO still appears.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: count not fraction, INFO only not INFO+LOW;
     [INFO*3,LOW*2,MED*1] -> info_count=3; low_count=5 wrong; info_fraction=0.5 wrong.
  2. LOW-only class -> 0 (not excluded).
  3. Multi-class independent.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_info_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_info_count_not_low_count_primary_discriminator() -> None:
    """PRIMARY DISC.: info_count=3 not low_count=5; [INFO*3,LOW*2,MED*1] -> 3; must be int."""
    problems = [_p("A", "INFO")] * 3 + [_p("A", "LOW")] * 2 + [_p("A", "MEDIUM")] * 1
    result = class_severity_rank_info_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 3, f"[INFO*3,LOW*2,MED*1] -> info_count=3; got {got}"
    assert isinstance(got, int), f"Must be int not float; got {type(got)}"
    assert got != 5, "Must be INFO only (3), not INFO+LOW (5)"


def test_low_only_gives_zero_not_excluded() -> None:
    """LOW-only class -> count=0 (class still present with zero)."""
    problems = [_p("B", "LOW")] * 4 + [_p("B", "MEDIUM")] * 2
    result = class_severity_rank_info_count(problems)
    assert "B" in result, "Class B must appear with count=0"
    assert result["B"] == 0, f"No INFO -> 0; got {result['B']}"


def test_multi_class_independent() -> None:
    """Two classes counted independently."""
    problems = (
        [_p("X", "INFO")] * 5 + [_p("X", "LOW")] * 1 +
        [_p("Y", "LOW")] * 3
    )
    result = class_severity_rank_info_count(problems)
    assert result.get("X") == 5, f"X -> 5; got {result.get('X')}"
    assert result.get("Y") == 0, f"Y -> 0 (no INFO); got {result.get('Y')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_info_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "INFO"), _p("D", "LOW")]
    result = class_severity_rank_info_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
