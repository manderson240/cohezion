"""Item 703: fid_severity_rank_range() -- severity rank range per fid (max_rank - min_rank).

Fid-axis complement of class_severity_rank_range (item 702).
fid_severity_rank_range(problems) -> dict[str, int].
Range = 0 when fid has one distinct severity.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; range = max-min (NOT spread count);
     fid 'f1': CRITICAL(4)+INFO(0) -> range=4; class-outer kills class-impl;
     spread-impl gives 2 distinct-count wrong.
  2. Single severity per fid -> range = 0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_range


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_max_minus_min_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND range = max-min.

    fid 'f1': CRITICAL(4)+INFO(0) -> range=4.
    class-outer impl wrong (key='A'); spread-impl wrong (2 distinct).
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "INFO")]
    result = fid_severity_rank_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 4, f"CRITICAL(4)-INFO(0)=4; got {result['f1']} (spread=2 wrong)"
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1'])}"


def test_single_severity_range_zero() -> None:
    """Fid with one distinct severity -> range = 0."""
    problems = [_p("f2", "HIGH"), _p("f2", "HIGH"), _p("f2", "HIGH")]
    result = fid_severity_rank_range(problems)
    assert result["f2"] == 0, f"All HIGH -> range=0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_range([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "INFO")]  # 4-0=4
    problems += [_p("f4", "HIGH"), _p("f4", "MEDIUM")]  # 3-2=1
    result = fid_severity_rank_range(problems)
    assert result["f3"] == 4, f"f3: CRIT-INFO=4; got {result.get('f3')}"
    assert result["f4"] == 1, f"f4: HIGH-MED=1; got {result.get('f4')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f5", "HIGH"), _p("f5", "LOW")]  # 3-1=2
    result = fid_severity_rank_range(problems)
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5'])}"
    assert result["f5"] == 2, f"HIGH(3)-LOW(1)=2; got {result['f5']}"
