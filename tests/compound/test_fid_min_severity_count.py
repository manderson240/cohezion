"""Item 611: fid_min_severity_count() -- minimum per-severity count per fid.

``fid_min_severity_count(problems) -> dict[str, int]``:
Returns {fid: min_per_severity_count} (count of the least frequent severity).
FID-axis complement of class_min_severity_count.
Returns INTEGER COUNT, not a severity label.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid (not class); returns min count not max or label.
     fid 'f1' HIGH=5, LOW=1 -> result['f1']==1 (not result['A'], not 5=max, not 'LOW').
     Kills wrong-axis and max-returning impls.
  2. Single-severity fid -> its total count (only bucket = both min and max).
     fid 'fy' CRITICAL x4 -> result['fy']==4.
  3. Uniform distribution -> tied count (min==max==each).
     fid 'fz' HIGH=3, LOW=3 -> result['fz']==3 (not 0=range).
  4. Empty -> {}.
  5. Returns int not float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_min_severity_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_returns_min_count_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid AND returns min count (not max, not label).

    fid 'f1' HIGH=5, LOW=1 -> result['f1']==1.
    class_min_severity_count keys by class 'A'.
    fid_max_severity_count returns 5 (not min).
    fid_top_severity returns 'HIGH' (label, not count).
    """
    problems = [_p("A", "f1", "HIGH")] * 5 + [_p("A", "f1", "LOW")]
    result = fid_min_severity_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert result["f1"] == 1, (
        f"HIGH=5, LOW=1: min_count=1; got {result['f1']} "
        f"(5=max_count wrong, 'LOW'=label wrong, 'A'=wrong axis)"
    )


def test_single_severity_returns_total_count() -> None:
    """Single severity per fid -> min_count equals total (only bucket).

    fid 'fy' CRITICAL x4 -> min_count=4.
    """
    problems = [_p("A", "fy", "CRITICAL")] * 4
    result = fid_min_severity_count(problems)
    assert result["fy"] == 4, f"4 CRITICAL -> min_count=4; got {result['fy']}"


def test_uniform_distribution_returns_tied_count() -> None:
    """Uniform 2-severity fid -> min_count = either count (not range=0).

    fid 'fz' HIGH=3, LOW=3 -> min_count=3.
    Kills impl computing range (max-min=0) instead of min (=3).
    """
    problems = [_p("A", "fz", "HIGH")] * 3 + [_p("B", "fz", "LOW")] * 3
    result = fid_min_severity_count(problems)
    assert result["fz"] == 3, f"Uniform [3,3]: min_count=3; got {result['fz']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_min_severity_count([]) == {}


def test_returns_int_not_float() -> None:
    """Return type per fid is int (not float)."""
    problems = [_p("A", "fx", "HIGH")] * 7 + [_p("A", "fx", "LOW")] * 2
    result = fid_min_severity_count(problems)
    assert isinstance(result["fx"], int), (
        "Value must be int; got " + type(result["fx"]).__name__
    )
    assert result["fx"] == 2, f"HIGH=7, LOW=2: min_count=2; got {result['fx']}"
