"""Item 802: class_severity_rank_critical_count() -- count rank==4 (CRITICAL only) per class.

class_severity_rank_critical_count(problems) -> dict[str, int].
count = count(rank == 4) per class.
CRITICAL-only: HIGH (rank 3) is NOT included.
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: count not fraction; class A: [CRIT*2,HIGH*3]
     -> critical_count=2; high_count=5 wrong; fraction=2/5=0.4 wrong; must be int.
  2. HIGH-only -> 0 (class still present).
  3. All-CRITICAL -> full count.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_critical_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_critical_count_not_high_count_primary_discriminator() -> None:
    """PRIMARY DISC.: critical_count=2; high_count=5 wrong; fraction=0.4 wrong; must be int."""
    problems = [_p("A", "CRITICAL")] * 2 + [_p("A", "HIGH")] * 3
    result = class_severity_rank_critical_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 2, f"[CRIT*2,HIGH*3] -> critical_count=2; got {got}"
    assert got \!= 5, "Must be CRITICAL-only, not HIGH inclusive (5)"
    assert isinstance(got, int), f"Must be int not float; got {type(got)}"


def test_high_only_gives_zero_not_excluded() -> None:
    """HIGH-only -> count=0 (class still present)."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_critical_count(problems)
    assert "B" in result, "Class B must appear with count=0"
    assert result["B"] == 0, f"HIGH-only -> 0; got {result['B']}"


def test_all_critical_gives_total() -> None:
    """All-CRITICAL -> count equals n."""
    problems = [_p("C", "CRITICAL")] * 3
    result = class_severity_rank_critical_count(problems)
    got = result.get("C")
    assert got is not None and got == 3, f"All CRITICAL -> 3; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_critical_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "CRITICAL"), _p("D", "HIGH")]
    result = class_severity_rank_critical_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
