"""Item 701: fid_severity_rank_min() -- minimum severity rank per fid (int).

Fid-axis complement of class_severity_rank_min (700).
fid_severity_rank_min(problems) -> dict[str, int].
CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1, INFO=0.  Unknown=0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: key is FID; value is MIN (not max) rank int;
     fid 'f1': CRITICAL(4)+INFO(0) -> min_rank=0;
     class-outer wrong (key); max-impl gives 4 wrong.
  2. Single LOW -> min_rank = 1.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Unknown severity gets 0 (lowest possible rank).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_min


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_int_min_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID, value is MIN int rank.

    fid 'f1': CRITICAL(4)+INFO(0) -> min_rank=0.
    class-outer gives key='A' wrong; max-impl gives 4 wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "INFO")]
    result = fid_severity_rank_min(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert result["f1"] == 0, f"INFO=0 is min; got {result['f1']} (max=4 wrong)"
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1'])}"


def test_single_low_gives_one() -> None:
    """Single LOW -> min_rank = 1."""
    problems = [_p("f2", "LOW")]
    result = fid_severity_rank_min(problems)
    assert result["f2"] == 1, f"LOW=1; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_min([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid uses its own minimum."""
    problems = [_p("f3", "HIGH"), _p("f3", "CRITICAL")]  # min=3
    problems += [_p("f4", "LOW"), _p("f4", "MEDIUM")]  # min=1
    result = fid_severity_rank_min(problems)
    assert result["f3"] == 3, f"f3: HIGH=3 is min; got {result.get('f3')}"
    assert result["f4"] == 1, f"f4: LOW=1 is min; got {result.get('f4')}"


def test_unknown_severity_gives_zero_min() -> None:
    """Unknown gets rank 0; it IS the minimum."""
    problems = [_p("f5", "BOGUS"), _p("f5", "CRITICAL")]
    result = fid_severity_rank_min(problems)
    assert result["f5"] == 0, f"BOGUS(0) < CRITICAL(4); min=0; got {result.get('f5')}"
