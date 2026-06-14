"""Item 609: fid_max_severity_count() -- maximum per-severity count per fid.

``fid_max_severity_count(problems) -> dict[str, int]``:
Returns {fid: max_per_severity_count} (the count of the most frequent severity).
FID-axis complement of class_max_severity_count.
Returns the INTEGER COUNT, not the severity label.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid (not class); returns count not label.
     fid 'f1' with HIGH=5, LOW=1 -> result['f1']==5, not 'HIGH', not result['A'].
     Kills impl on wrong axis or returning the label.
  2. Single-severity fid -> its total count.
     fid 'fy' CRITICAL x4 -> result['fy']==4.
     Kills impl returning 0 or 1 for single bucket.
  3. Tie broken by max count (both equal -> max==either count).
     fid 'fz' HIGH=3, LOW=3 -> result['fz']==3.
  4. Empty -> {}.
     Kills impl without empty guard.
  5. Returns int (not float).
     Kills impl applying float division or variance formula.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_max_severity_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_returns_count_not_label_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid AND returns integer count, not severity label.

    fid 'f1' with HIGH=5, LOW=1 -> result['f1']==5.
    class_max_severity_count would key by 'A'.
    class_top_severity returns 'HIGH' (the label), not 5 (the count).
    Kills both wrong-axis and label-returning impls.
    """
    problems = [_p("A", "f1", "HIGH")] * 5 + [_p("A", "f1", "LOW")]
    result = fid_max_severity_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert result["f1"] == 5, (
        f"HIGH=5, LOW=1: max_count=5; got {result['f1']} "
        f"('HIGH' = label, not count; 'A' = wrong axis)"
    )


def test_single_severity_returns_total_count() -> None:
    """Single severity per fid -> max_count equals its total count.

    fid 'fy' CRITICAL x4 -> max_count=4.
    Kills impl returning 1 (treating single bucket as trivial).
    """
    problems = [_p("A", "fy", "CRITICAL")] * 4
    result = fid_max_severity_count(problems)
    assert result["fy"] == 4, f"4 CRITICAL -> max_count=4; got {result['fy']}"


def test_uniform_distribution_returns_tied_count() -> None:
    """Uniform 2-severity fid -> max_count = either count (both equal).

    fid 'fz' HIGH=3, LOW=3 -> max_count=3.
    Kills impl computing max-min (range) instead of max.
    """
    problems = [_p("A", "fz", "HIGH")] * 3 + [_p("B", "fz", "LOW")] * 3
    result = fid_max_severity_count(problems)
    assert result["fz"] == 3, f"Uniform [3,3]: max_count=3; got {result['fz']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_max_severity_count([]) == {}


def test_returns_int_not_float() -> None:
    """Return type per fid is int (not float).

    Kills impl using float division or returning a float.
    """
    problems = [_p("A", "fx", "HIGH")] * 7 + [_p("A", "fx", "LOW")] * 2
    result = fid_max_severity_count(problems)
    assert isinstance(result["fx"], int), "Value must be int; got " + type(result["fx"]).__name__
    assert result["fx"] == 7, f"HIGH=7, LOW=2: max_count=7; got {result['fx']}"
