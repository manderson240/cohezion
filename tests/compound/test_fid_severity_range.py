"""Item 607: fid_severity_range() -- range of severity counts per fid.

``fid_severity_range(problems) -> dict[str, int]``:
Returns {fid: max_sev_count - min_sev_count}.
Range=0 means all severities equally loaded or single severity.
Returns int, not float.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid (not class).
     fid 'f1' HIGH=5, LOW=1 -> range=4 (int, fid axis).
     Kills impl reusing class_severity_range on wrong axis.
  2. Single-severity fid -> 0.
     Kills impl that errors or returns non-zero.
  3. Uniform k-severity -> 0 (all counts equal -> range=0).
     Kills impl returning non-zero for balanced dist.
  4. Empty -> {}.
     Kills impl without empty guard.
  5. Returns int (not float).
     Kills impl returning float range or variance.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_range


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: result keyed by fid, NOT class name.

    fid 'f1' with HIGH=5, LOW=1 -> range=4 (int).
    class_severity_range would key by class 'A' instead.
    Kills impl delegating to class_severity_range on wrong axis.
    """
    problems = [_p("A", "f1", "HIGH")] * 5 + [_p("A", "f1", "LOW")]
    result = fid_severity_range(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert result["f1"] == 4, (
        f"HIGH=5, LOW=1: range=5-1=4; got {result['f1']}"
    )


def test_single_severity_range_zero() -> None:
    """Single severity per fid -> range=0.

    Kills impl that errors or returns non-zero for single bucket.
    """
    problems = [_p("A", "fy", "CRITICAL")] * 6
    result = fid_severity_range(problems)
    assert result["fy"] == 0, f"Single-severity -> range=0; got {result['fy']}"


def test_uniform_distribution_range_zero() -> None:
    """Uniform severity distribution -> range=0 (max==min).

    HIGH=3, LOW=3: max=3, min=3, range=0.
    Kills impl returning non-zero for balanced data.
    """
    problems = [_p("A", "fz", "HIGH")] * 3 + [_p("B", "fz", "LOW")] * 3
    result = fid_severity_range(problems)
    assert result["fz"] == 0, f"Uniform [3,3] -> range=0; got {result['fz']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_range([]) == {}


def test_returns_int_not_float() -> None:
    """Return type per fid is int (not float).

    Kills impl returning variance (float) or float subtraction.
    """
    problems = [_p("A", "fx", "HIGH")] * 4 + [_p("A", "fx", "LOW")]
    result = fid_severity_range(problems)
    assert isinstance(result["fx"], int), (
        "Value must be int; got " + type(result["fx"]).__name__
    )
    assert result["fx"] == 3, f"HIGH=4, LOW=1: range=3; got {result['fx']}"
