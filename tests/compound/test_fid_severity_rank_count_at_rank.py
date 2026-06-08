"""Item 785: fid_severity_rank_count_at_rank() -- count at exact rank per fid.

fid_severity_rank_count_at_rank(problems, rank) -> dict[str, int].
Fid-axis complement of class_severity_rank_count_at_rank (item 784).
Returns {fid: count}; count=0 if none at rank.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [CRIT*3,HIGH*2] count_at_rank(3)=2;
     class-outer wrong; at-or-above(3)-impl=5 wrong.
  2. Zero for fid with none at rank (fid not excluded).
  3. Multi-fid: each fid independently counted.
  4. Empty -> {}.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_count_at_rank


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_key_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; count_at_rank(3)=2 for fid f1.

    fid f1: [CRITICAL(4)*3, HIGH(3)*2].
    count_at_rank(3)=2; at-or-above(3)-impl=5 wrong.
    """
    problems = [_p("f1", "CRITICAL")] * 3 + [_p("f1", "HIGH")] * 2
    result = fid_severity_rank_count_at_rank(problems, 3)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    got = result["f1"]
    assert got == 2, f"count_at_rank(3) for [CRIT*3,HIGH*2] = 2; got {got}"
    assert got != 5, "Must be exact count not at-or-above"


def test_zero_for_fid_with_no_matching_rank() -> None:
    """Fid present but no problems at target rank -> count=0 (fid not excluded)."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_count_at_rank(problems, 1)  # LOW=1, none present
    assert "f2" in result, "fid f2 must still appear with count=0"
    assert result["f2"] == 0, f"No LOW in [CRIT*3] -> 0; got {result['f2']}"


def test_multi_fid_independent_counts() -> None:
    """Each fid's count is independent."""
    problems = [_p("f3", "HIGH")] * 2 + [_p("f4", "HIGH")] + [_p("f4", "CRITICAL")]
    result = fid_severity_rank_count_at_rank(problems, 3)  # HIGH=3
    assert result.get("f3") == 2, f"f3: [HIGH*2] -> 2; got {result.get('f3')}"
    assert result.get("f4") == 1, f"f4: [HIGH, CRIT] -> 1; got {result.get('f4')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_count_at_rank([], 0) == {}


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f5", "INFO"), _p("f5", "HIGH")]
    result = fid_severity_rank_count_at_rank(problems, 0)
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5'])}"
