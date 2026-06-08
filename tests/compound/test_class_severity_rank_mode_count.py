"""Item 778: class_severity_rank_mode_count() -- number of distinct modes per class.

class_severity_rank_mode_count(problems) -> dict[str, int].
Returns count of distinct ranks tied for max frequency per class.
Unimodal -> 1.  All-same -> 1.  Bimodal tie -> 2.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: mode_count != unique_count; class A: [INFO(0)*2, HIGH(3)*2, CRITICAL(4)]
     -> max_count=2, tied={0,3}, mode_count=2; unique_count=3 wrong; 1-impl wrong.
  2. Unimodal -> 1.
  3. All-same -> 1.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_mode_count


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_bimodal_tie_primary_discriminator() -> None:
    """PRIMARY DISC.: bimodal -> 2; unique_count=3 wrong; 1-impl wrong.

    class A: [INFO(0)*2, HIGH(3)*2, CRITICAL(4)] -> max_count=2, tied={0,3}, mode_count=2.
    unique_count=3 (wrong); single-mode impl would return 1 (wrong).
    """
    problems = [_p("A", "INFO")] * 2 + [_p("A", "HIGH")] * 2 + [_p("A", "CRITICAL")]
    result = class_severity_rank_mode_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert got == 2, f"[INFO*2,HIGH*2,CRITICAL] -> 2 modes; got {got}"
    assert got != 3, "Must be mode_count not unique_count (3)"
    assert got != 1, "Must count tied modes, not just 1"


def test_unimodal_gives_one() -> None:
    """Single dominant rank -> mode_count = 1."""
    problems = [_p("B", "CRITICAL")] * 3 + [_p("B", "INFO")] * 2
    result = class_severity_rank_mode_count(problems)
    got = result.get("B")
    assert got is not None and got == 1, f"CRITICAL*3+INFO*2 -> 1 mode; got {got}"


def test_all_same_gives_one() -> None:
    """All same -> mode_count = 1."""
    problems = [_p("C", "HIGH")] * 4
    result = class_severity_rank_mode_count(problems)
    got = result.get("C")
    assert got is not None and got == 1, f"All HIGH -> 1 mode; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_mode_count([]) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_mode_count(problems)
    assert isinstance(result["D"], int), f"Must be int; got {type(result['D'])}"
