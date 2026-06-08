"""Item 812: class_severity_rank_low_only_count() -- count rank==1 (LOW only) per class.

class_severity_rank_low_only_count(problems) -> dict[str, int].
count = count(rank == 1) per class.
LOW-only: INFO (rank 0) is NOT included.
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: count not fraction; class A: [LOW*3, INFO*2]
     -> low_only_count=3; info_count=2 wrong; fraction=3/5=0.6 wrong; must be int.
  2. INFO-only -> 0 (class still present).
  3. All-LOW -> full count.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_low_only_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_low_only_count_not_info_count_primary_discriminator() -> None:
    """PRIMARY DISC.: count=3; info_count=2 wrong; fraction=0.6 wrong; [LOW*3,INFO*2] -> 3."""
    problems = [_p("A", "LOW")] * 3 + [_p("A", "INFO")] * 2
    result = class_severity_rank_low_only_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 3, f"[LOW*3,INFO*2] -> low_only_count=3; got {got}"
    assert got != 2, "Must count LOW not INFO (would give 2)"
    assert isinstance(got, int), f"Must be int not float; got {type(got)}"


def test_info_only_gives_zero_not_excluded() -> None:
    """INFO-only -> count=0 (class still present)."""
    problems = [_p("B", "INFO")] * 4
    result = class_severity_rank_low_only_count(problems)
    assert "B" in result, "Class B must appear with count=0"
    assert result["B"] == 0, f"INFO-only -> 0; got {result['B']}"


def test_all_low_gives_total() -> None:
    """All-LOW -> count equals n."""
    problems = [_p("C", "LOW")] * 3
    result = class_severity_rank_low_only_count(problems)
    got = result.get("C")
    assert got is not None and got == 3, f"All LOW -> 3; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_low_only_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "LOW"), _p("D", "CRITICAL")]
    result = class_severity_rank_low_only_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
