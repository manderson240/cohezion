"""Item 683: fid_severity_any() -- True if fid has ANY problem matching given severity set.

Fid-axis complement of class_severity_any (item 682).
fid_severity_any(problems, severities) -> dict[str, bool].
Zero-inclusive: ALL fids in input appear in result.
Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_any


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_key_and_set_severities_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; accepts SET; fid 'f1': HIGH+LOW, query {CRIT,HIGH} -> True.

    Class-outer impl gives wrong key; single-severity impl fails with set.
    """
    problems = [_p("f1", "HIGH"), _p("f1", "LOW")]
    result = fid_severity_any(problems, {"CRITICAL", "HIGH"})
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"Fid 'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] is True, (
        f"f1 has HIGH in {{CRITICAL,HIGH}} -> True; got {result['f1']}"
    )
    assert isinstance(result["f1"], bool), "Must be bool"


def test_false_when_no_severity_in_set() -> None:
    """Fid with no severity from the queried set -> False."""
    problems = [_p("f2", "LOW"), _p("f2", "MEDIUM")]
    result = fid_severity_any(problems, {"CRITICAL", "HIGH"})
    assert result["f2"] is False, (
        f"f2 has only LOW+MEDIUM -> False; got {result.get('f2')}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_any([], {"HIGH"}) == {}


def test_empty_severity_set_all_false() -> None:
    """Empty severity set -> all False."""
    problems = [_p("f3", "HIGH"), _p("f4", "CRITICAL")]
    result = fid_severity_any(problems, set())
    assert result["f3"] is False
    assert result["f4"] is False


def test_multiple_fids_independent() -> None:
    """f5 has CRITICAL (True), f6 does not (False)."""
    problems = [_p("f5", "CRITICAL"), _p("f5", "HIGH"), _p("f6", "LOW")]
    result = fid_severity_any(problems, {"CRITICAL"})
    assert result["f5"] is True, f"f5 has CRITICAL -> True; got {result.get('f5')}"
    assert result["f6"] is False, f"f6 has no CRITICAL -> False; got {result.get('f6')}"
