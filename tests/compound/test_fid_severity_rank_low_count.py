"""Item 797: fid_severity_rank_low_count() -- count rank<=1 (INFO/LOW) per fid.

fid_severity_rank_low_count(problems) -> dict[str, int].
Fid-axis complement of class_severity_rank_low_count (item 796).
count = count(rank <= 1) per fid.
INFO (rank 0) and LOW (rank 1) included; MEDIUM+ excluded.
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key FID; fid f1: [INFO*2,LOW*1,MEDIUM*2] -> 3;
     class-outer wrong; fraction-impl=0.6 wrong; at_or_above(2)=2 wrong.
  2. No INFO/LOW -> 0 (fid still present).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_low_count


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_low_count_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key FID; count=3; fraction-impl=0.6 wrong; at_or_above(2)=2 wrong."""
    problems = [_p("f1", "INFO")] * 2 + [_p("f1", "LOW")] * 1 + [_p("f1", "MEDIUM")] * 2
    result = fid_severity_rank_low_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "X" not in result, f"Class 'X' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got == 3, f"[INFO*2,LOW*1,MED*2] -> low_count=3; got {got}"
    assert isinstance(got, int), f"Must be int; got {type(got)}"


def test_no_low_gives_zero_not_excluded() -> None:
    """No INFO/LOW -> count=0 (fid not excluded)."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_low_count(problems)
    assert "f2" in result, "fid f2 must appear with count=0"
    assert result["f2"] == 0, f"No INFO/LOW -> 0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_low_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "INFO")] * 2 + [_p("fA", "LOW")] + [_p("fA", "MEDIUM")] * 2 +  # 3
        [_p("fB", "HIGH")] * 4                                                      # 0
    )
    result = fid_severity_rank_low_count(problems)
    assert result.get("fA") == 3, f"fA -> 3; got {result.get('fA')}"
    assert result.get("fB") == 0, f"fB -> 0; got {result.get('fB')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f3", "INFO"), _p("f3", "HIGH")]
    result = fid_severity_rank_low_count(problems)
    assert isinstance(result["f3"], int), f"Must be int; got {type(result['f3'])}"
