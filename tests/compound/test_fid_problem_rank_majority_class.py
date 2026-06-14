"""Item 747: fid_problem_rank_majority_class() -- majority severity rank per fid.

fid_problem_rank_majority_class(problems) -> dict[str, int].
Fid-axis complement of class_problem_rank_majority_class (item 746).
Returns the rank (int) with highest count per fid; ties -> min rank.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND returns rank INT;
     fid 'f1': INFO(0)*3+HIGH(3)*2 -> majority_rank=0; class-outer wrong; label-impl wrong.
  2. Tie -> min rank.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_rank_majority_class


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_majority_rank_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND majority_rank=0 for INFO(0)*3+HIGH(3)*2.

    fid 'f1': INFO(0)*3+HIGH(3)*2 -> rank=0; class-outer gives key='A' wrong.
    """
    problems = [
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "HIGH"),
        _p("f1", "HIGH"),
    ]
    result = fid_problem_rank_majority_class(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got == 0, f"INFO(0)*3 -> rank=0; got {got}"
    assert isinstance(got, int), f"Must be int; got {type(got)}"


def test_tie_broken_by_min_rank() -> None:
    """Tie: min rank; HIGH(3)*2+MEDIUM(2)*2 -> rank=2."""
    problems = [_p("f2", "HIGH"), _p("f2", "HIGH"), _p("f2", "MEDIUM"), _p("f2", "MEDIUM")]
    result = fid_problem_rank_majority_class(problems)
    got = result.get("f2")
    assert got == 2, f"HIGH(3) tie MEDIUM(2) -> min rank=2; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_problem_rank_majority_class([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids computed independently."""
    problems = (
        [_p("fa", "INFO"), _p("fa", "INFO"), _p("fa", "HIGH")]  # fa: INFO(0)*2>HIGH(3)*1 -> 0
        + [_p("fb", "CRITICAL"), _p("fb", "CRITICAL")]  # fb: CRITICAL(4)*2 -> 4
    )
    result = fid_problem_rank_majority_class(problems)
    assert result["fa"] == 0, f"fa: INFO*2>HIGH*1 -> rank=0; got {result['fa']}"
    assert result["fb"] == 4, f"fb: CRITICAL*2 -> rank=4; got {result['fb']}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f3", "MEDIUM")] * 3
    result = fid_problem_rank_majority_class(problems)
    assert isinstance(result["f3"], int), f"Must be int; got {type(result['f3'])}"
