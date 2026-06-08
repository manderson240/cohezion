"""Item 779: fid_severity_rank_mode_count() -- number of distinct modes per fid.

fid_severity_rank_mode_count(problems) -> dict[str, int].
Fid-axis complement of class_severity_rank_mode_count (item 778).
Count of distinct ranks tied for max frequency per fid; unimodal -> 1; empty -> {}.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND bimodal -> 2;
     fid f1: [INFO(0)*2, HIGH(3)*2] -> mode_count=2; class-outer wrong; unique_count=2 same
     BUT discriminated by single-mode case: fid f2: [CRITICAL*3, INFO*2] -> mode_count=1.
  2. Unimodal -> 1.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_mode_count


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_mode_count_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; bimodal -> 2; class-outer wrong.

    fid f1: [INFO(0)*2, HIGH(3)*2] -> max_count=2, tied={0,3}, mode_count=2.
    """
    problems = [_p("f1", "INFO")] * 2 + [_p("f1", "HIGH")] * 2
    result = fid_severity_rank_mode_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got == 2, f"[INFO*2,HIGH*2] -> 2 modes; got {got}"


def test_unimodal_gives_one() -> None:
    """Single dominant rank -> mode_count = 1."""
    problems = [_p("f2", "CRITICAL")] * 3 + [_p("f2", "INFO")] * 2
    result = fid_severity_rank_mode_count(problems)
    got = result.get("f2")
    assert got is not None and got == 1, f"CRITICAL*3 -> 1 mode; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_mode_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = (
        [_p("fA", "INFO")] * 2 + [_p("fA", "HIGH")] * 2  # 2 modes
        + [_p("fB", "CRITICAL")] * 3  # all-same -> 1 mode
    )
    result = fid_severity_rank_mode_count(problems)
    assert result["fA"] == 2, f"fA -> 2 modes; got {result['fA']}"
    assert result["fB"] == 1, f"fB -> 1 mode; got {result['fB']}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f3", "INFO"), _p("f3", "CRITICAL")]
    result = fid_severity_rank_mode_count(problems)
    assert isinstance(result["f3"], int), f"Must be int; got {type(result['f3'])}"
