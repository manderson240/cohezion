"""Item 813: fid_severity_rank_low_only_count() -- count rank==1 (LOW only) per fid.

fid_severity_rank_low_only_count(problems) -> dict[str, int].
Fid-axis complement of class_severity_rank_low_only_count (item 812).
count = count(rank == 1) per fid.
LOW-only: INFO (rank 0) NOT included.  Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key FID; fid f1: [LOW*3,INFO*2]
     -> low_only_count=3; class-outer wrong; info_count=2 wrong; fraction wrong; must be int.
  2. INFO-only -> 0 (fid not excluded).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_low_only_count


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_low_only_count_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key FID; count=3; class-outer wrong; info_count=2 wrong; int."""
    problems = [_p("f1", "LOW")] * 3 + [_p("f1", "INFO")] * 2
    result = fid_severity_rank_low_only_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "X" not in result, f"Class 'X' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got == 3, f"[LOW*3,INFO*2] -> low_only_count=3; got {got}"
    assert got != 2, "Must count LOW not INFO (would give 2)"
    assert isinstance(got, int), f"Must be int; got {type(got)}"


def test_info_only_gives_zero_not_excluded() -> None:
    """INFO-only fid -> count=0 (fid still present)."""
    problems = [_p("f2", "INFO")] * 3
    result = fid_severity_rank_low_only_count(problems)
    assert "f2" in result, "fid f2 must appear with count=0"
    assert result["f2"] == 0, f"INFO-only -> 0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_low_only_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "LOW")] * 3 + [_p("fA", "INFO")] * 2 +  # 3
        [_p("fB", "INFO")] * 4                               # 0
    )
    result = fid_severity_rank_low_only_count(problems)
    assert result.get("fA") == 3, f"fA -> 3; got {result.get('fA')}"
    assert result.get("fB") == 0, f"fB -> 0; got {result.get('fB')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f3", "LOW"), _p("f3", "HIGH")]
    result = fid_severity_rank_low_only_count(problems)
    assert isinstance(result["f3"], int), f"Must be int; got {type(result['f3'])}"
