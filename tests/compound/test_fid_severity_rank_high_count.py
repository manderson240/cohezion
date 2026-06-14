"""Item 801: fid_severity_rank_high_count() -- count rank>=3 (HIGH/CRITICAL) per fid.

fid_severity_rank_high_count(problems) -> dict[str, int].
Fid-axis complement of class_severity_rank_high_count (item 800).
count = count(rank >= 3) per fid.
HIGH (rank 3) and CRITICAL (rank 4) included; zero-inclusive.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key FID; fid f1: [HIGH*3,CRIT*2,MED*1] -> 5;
     class-outer wrong; fraction wrong; must be int.
  2. MEDIUM-only -> 0 (fid not excluded).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_high_count


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_high_count_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key FID; count=5; class-outer wrong; fraction wrong; int."""
    problems = [_p("f1", "HIGH")] * 3 + [_p("f1", "CRITICAL")] * 2 + [_p("f1", "MEDIUM")] * 1
    result = fid_severity_rank_high_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "X" not in result, f"Class 'X' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got == 5, f"[HIGH*3,CRIT*2,MED*1] -> 5; got {got}"
    assert isinstance(got, int), f"Must be int; got {type(got)}"


def test_medium_only_gives_zero_not_excluded() -> None:
    """MEDIUM-only fid -> count=0 (fid still present)."""
    problems = [_p("f2", "MEDIUM")] * 3
    result = fid_severity_rank_high_count(problems)
    assert "f2" in result, "fid f2 must appear with count=0"
    assert result["f2"] == 0, f"MEDIUM-only -> 0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_high_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "HIGH")] * 2
        + [_p("fA", "MEDIUM")]  # 2
        + [_p("fB", "CRITICAL")] * 4  # 4
    )
    result = fid_severity_rank_high_count(problems)
    assert result.get("fA") == 2, f"fA -> 2; got {result.get('fA')}"
    assert result.get("fB") == 4, f"fB -> 4; got {result.get('fB')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f3", "HIGH"), _p("f3", "INFO")]
    result = fid_severity_rank_high_count(problems)
    assert isinstance(result["f3"], int), f"Must be int; got {type(result['f3'])}"
