"""Item 705: fid_severity_above_threshold() -- count per fid where rank > threshold.

Fid-axis complement of class_severity_above_threshold (item 704).
fid_severity_above_threshold(problems, threshold) -> dict[str, int].
Strictly above threshold.  Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID (not class); threshold strictly exclusive;
     fid 'f1': CRITICAL(4)+HIGH(3)+LOW(1), threshold=2 -> count=2 (CRITICAL+HIGH);
     class-outer gives wrong key; >=impl gives 3 wrong (includes LOW=1... wait threshold=2).
     Actually: fid 'f1': CRITICAL(4)+HIGH(3)+MEDIUM(2), threshold=2 -> count=2;
     >=impl gives 3 wrong (includes MEDIUM at rank 2 == threshold).
  2. Fid with nothing above threshold -> 0 (zero-inclusive).
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_above_threshold


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_strict_above_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND strictly above (not >=).

    fid 'f1': CRITICAL(4)+HIGH(3)+MEDIUM(2), threshold=2 -> count=2.
    class-outer gives key='A' wrong; >=impl gives 3 wrong (MEDIUM rank==threshold).
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "HIGH"), _p("f1", "MEDIUM")]
    result = fid_severity_above_threshold(problems, 2)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, (
        f"CRITICAL(4)>2 and HIGH(3)>2 but MEDIUM(2) NOT > 2 -> count=2; "
        f"got {result['f1']} (>=impl=3 wrong)"
    )
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1'])}"


def test_nothing_above_threshold_gives_zero() -> None:
    """Fid with nothing strictly above threshold -> 0 (zero-inclusive)."""
    problems = [_p("f2", "INFO"), _p("f2", "LOW")]
    result = fid_severity_above_threshold(problems, 2)
    assert "f2" in result, "'f2' must be present (zero-inclusive)"
    assert result["f2"] == 0, f"INFO(0)+LOW(1) both <=2 -> 0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_above_threshold([], 1) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "HIGH")]  # f3: both >1 -> 2
    problems += [_p("f4", "LOW"), _p("f4", "INFO")]  # f4: both <=1 -> 0
    result = fid_severity_above_threshold(problems, 1)
    assert result["f3"] == 2, f"f3: CRIT+HIGH both>1 -> 2; got {result.get('f3')}"
    assert "f4" in result, "'f4' must be present"
    assert result["f4"] == 0, f"f4: LOW(1)+INFO(0) both <=1 -> 0; got {result.get('f4')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f5", "CRITICAL")]
    result = fid_severity_above_threshold(problems, 0)
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5'])}"
    assert result["f5"] == 1, f"CRITICAL(4)>0 -> 1; got {result['f5']}"
