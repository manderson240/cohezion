"""Item 707: fid_severity_at_threshold() -- count per fid at exact severity rank.

Fid-axis complement of class_severity_at_threshold (item 706).
fid_severity_at_threshold(problems, threshold) -> dict[str, int].
Counts problems whose rank == threshold exactly.
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND exactly-equal (not above);
     fid 'f1': HIGH(3)+MEDIUM(2)+HIGH(3), threshold=3 -> count=2;
     class-outer gives wrong key; above-impl gives 0.
  2. Nothing at threshold -> 0 (zero-inclusive).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_at_threshold


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_exactly_equal_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND exactly-equal threshold.

    fid 'f1': HIGH(3)+MEDIUM(2)+HIGH(3), threshold=3 -> count=2.
    class-outer gives key='A' wrong; above-impl gives 0 wrong.
    """
    problems = [_p("f1", "HIGH"), _p("f1", "MEDIUM"), _p("f1", "HIGH")]
    result = fid_severity_at_threshold(problems, 3)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, (
        f"Two HIGH(rank=3)==threshold(3) -> count=2; got {result['f1']} (above-impl=0 wrong)"
    )
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1'])}"


def test_nothing_at_threshold_gives_zero() -> None:
    """Fid with nothing at exactly threshold -> 0 (zero-inclusive)."""
    problems = [_p("f2", "CRITICAL"), _p("f2", "LOW")]
    result = fid_severity_at_threshold(problems, 2)  # MEDIUM=2; none present
    assert "f2" in result, "'f2' must be present (zero-inclusive)"
    assert result["f2"] == 0, f"No MEDIUM(rank=2) -> 0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_at_threshold([], 3) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [_p("f3", "HIGH"), _p("f3", "HIGH")]  # f3: 2 at rank 3
    problems += [_p("f4", "LOW"), _p("f4", "INFO")]  # f4: 0 at rank 3
    result = fid_severity_at_threshold(problems, 3)
    assert result["f3"] == 2, f"f3: two HIGH at rank 3 -> 2; got {result.get('f3')}"
    assert "f4" in result, "'f4' must be present"
    assert result["f4"] == 0, f"f4: no rank-3 -> 0; got {result.get('f4')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f5", "INFO")] * 4
    result = fid_severity_at_threshold(problems, 0)  # INFO=0
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5'])}"
    assert result["f5"] == 4, f"4 INFO at rank 0 -> 4; got {result['f5']}"
