"""Item 650: fid_severity_critical_rate() -- CRITICAL/total fraction per fid.

FID-axis complement of class_severity_critical_rate (item 649).
Returns {fid: count(CRITICAL) / total_fid_problems}.
float in [0, 1].  0.0 = no CRITICAL.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_critical_rate


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class.

    fid 'f1': 2 CRITICAL + 3 HIGH -> rate=0.4.
    Class-axis would key on class name, not fid.
    """
    problems = [_p("A", "f1", "CRITICAL")] * 2 + [_p("A", "f1", "HIGH")] * 3
    result = fid_severity_critical_rate(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 0.4) < 1e-9, (
        f"2 CRIT+3 HIGH -> CRIT/total=0.4; got {result['f1']}"
    )


def test_no_critical_rate_zero_fid_present() -> None:
    """No CRITICAL for fid -> rate=0.0 (fid present, not omitted)."""
    problems = [_p("A", "f2", "HIGH")] * 5 + [_p("B", "f2", "LOW")] * 3
    result = fid_severity_critical_rate(problems)
    assert "f2" in result, f"Fid with no CRITICAL must still be present; got {list(result)}"
    assert abs(result["f2"]) < 1e-9, f"No CRITICAL -> rate=0.0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_critical_rate([]) == {}


def test_all_critical_rate_one() -> None:
    """All problems CRITICAL -> rate=1.0."""
    problems = [_p("A", "f3", "CRITICAL")] * 4
    result = fid_severity_critical_rate(problems)
    assert abs(result["f3"] - 1.0) < 1e-9, f"All CRIT -> 1.0; got {result.get('f3')}"


def test_multiple_fids_independent_rates() -> None:
    """Multiple fids each get independent critical rates."""
    problems = (
        [_p("A", "f4", "CRITICAL")] + [_p("A", "f4", "HIGH")] * 4
        + [_p("B", "f5", "CRITICAL")] * 3 + [_p("B", "f5", "LOW")] * 3
    )
    result = fid_severity_critical_rate(problems)
    assert abs(result["f4"] - 0.2) < 1e-9, f"f4: 1/5 -> 0.2; got {result.get('f4')}"
    assert abs(result["f5"] - 0.5) < 1e-9, f"f5: 3/6 -> 0.5; got {result.get('f5')}"
