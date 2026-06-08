"""Item 796: class_severity_rank_low_count() -- count rank<=1 (INFO/LOW) per class.

class_severity_rank_low_count(problems) -> dict[str, int].
count = count(rank <= 1) per class.
Absolute count (not fraction): [INFO*2, LOW*1, MEDIUM*2] -> 3.
INFO (rank 0) and LOW (rank 1) included; MEDIUM+ excluded.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: count not fraction; class A: [INFO(0)*2, LOW(1)*1, MEDIUM(2)*2]
     -> low_count=3; low_fraction-impl gives 0.6 wrong; at_or_above(2)-impl gives 2 wrong.
  2. No INFO/LOW -> 0 (class still present, not excluded).
  3. All INFO+LOW -> full count.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_low_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_low_count_not_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: count=3 not fraction=0.6; [INFO*2,LOW*1,MEDIUM*2] -> 3."""
    problems = [_p("A", "INFO")] * 2 + [_p("A", "LOW")] * 1 + [_p("A", "MEDIUM")] * 2
    result = class_severity_rank_low_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 3, f"[INFO*2,LOW*1,MED*2] -> low_count=3; got {got}"
    assert isinstance(got, int), f"Must be int not float; got {type(got)}"


def test_no_low_gives_zero_not_excluded() -> None:
    """No INFO/LOW -> count=0 (class not excluded from result)."""
    problems = [_p("B", "CRITICAL")] * 3 + [_p("B", "HIGH")] * 2
    result = class_severity_rank_low_count(problems)
    assert "B" in result, "Class B must appear with count=0"
    assert result["B"] == 0, f"No INFO/LOW in [CRIT*3,HIGH*2] -> 0; got {result['B']}"


def test_all_info_and_low_gives_total() -> None:
    """All INFO+LOW -> count equals total n."""
    problems = [_p("C", "INFO")] * 2 + [_p("C", "LOW")] * 3
    result = class_severity_rank_low_count(problems)
    got = result.get("C")
    assert got is not None and got == 5, f"All INFO+LOW -> 5; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_low_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_low_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
