"""Item 709: fid_severity_below_threshold() -- count per fid where rank < threshold.

Fid-axis complement of class_severity_below_threshold (item 708).
fid_severity_below_threshold(problems, threshold) -> dict[str, int].
Strictly below (rank < threshold).  Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, STRICTLY below (not <=);
     fid 'f1': INFO(0)+LOW(1)+HIGH(3), threshold=2 -> count=2;
     class-outer wrong; <=impl wrong.
  2. Threshold 0 -> all counts = 0 (zero-inclusive; nothing below floor).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_below_threshold


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_strictly_below_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND strictly below threshold.

    fid 'f1': INFO(0)+LOW(1)+HIGH(3), threshold=2 -> count=2 (INFO+LOW below 2).
    class-outer wrong (key='A'); <=impl wrong; HIGH(3) not below 2.
    """
    problems = [_p("f1", "INFO"), _p("f1", "LOW"), _p("f1", "HIGH")]
    result = fid_severity_below_threshold(problems, 2)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert result["f1"] == 2, (
        f"INFO(0)<2 and LOW(1)<2; HIGH(3) NOT below 2 -> count=2; got {result['f1']}"
    )
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1'])}"


def test_threshold_zero_nothing_below() -> None:
    """Threshold 0: all counts = 0 (zero-inclusive; nothing below rank 0)."""
    problems = [_p("f2", "INFO"), _p("f2", "LOW")]
    result = fid_severity_below_threshold(problems, 0)
    assert "f2" in result, "'f2' must be zero-inclusive present"
    assert result["f2"] == 0, f"Nothing below rank 0 -> 0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_below_threshold([], 2) == {}


def test_multiple_fids_independent() -> None:
    """Each fid counted independently."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "HIGH")]  # f3: nothing below rank 3
    problems += [_p("f4", "INFO"), _p("f4", "LOW")]  # f4: both below rank 2
    result = fid_severity_below_threshold(problems, 2)
    assert "f3" in result, "'f3' must be zero-inclusive present"
    assert result["f3"] == 0, f"f3: nothing below 2 -> 0; got {result.get('f3')}"
    assert result["f4"] == 2, f"f4: INFO+LOW both below 2 -> 2; got {result.get('f4')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f5", "INFO")] * 4
    result = fid_severity_below_threshold(problems, 1)  # INFO(0) < 1
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5'])}"
    assert result["f5"] == 4, f"4 INFO below threshold=1 -> 4; got {result['f5']}"
