"""Item 681: fid_has_severity() -- boolean per fid: does this fid have the given severity?

Fid-axis complement of class_has_severity (item 680).
fid_has_severity(problems, severity) -> dict[str, bool].
Zero-inclusive: ALL fids present in input appear in result.
Fids without the queried severity get False (NOT absent).
Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_has_severity


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_false_for_present_fid_without_severity_primary_discriminator() -> None:
    """PRIMARY DISC.: fid in input but without queried severity -> False (not absent).

    fid 'f1': 3 HIGH + 0 CRITICAL -> fid_has_severity(problems, 'CRITICAL')['f1'] = False.
    Sparse impl would omit 'f1'; outer key is FID (kills class-outer impl).
    """
    problems = [_p("f1", "HIGH")] * 3
    result = fid_has_severity(problems, "CRITICAL")
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"Fid 'f1' must be present (zero-inclusive); got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] is False, f"f1 has no CRITICAL -> False; got {result['f1']} (absent=wrong)"
    assert isinstance(result["f1"], bool), "Must be bool"


def test_true_for_fid_with_matching_severity() -> None:
    """Fid with the queried severity -> True."""
    problems = [_p("f2", "CRITICAL")] * 2 + [_p("f2", "HIGH")]
    result = fid_has_severity(problems, "CRITICAL")
    assert result["f2"] is True, f"f2 has CRITICAL -> True; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_has_severity([], "HIGH") == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids: f3 has HIGH, f4 does not."""
    problems = [_p("f3", "HIGH"), _p("f3", "LOW"), _p("f4", "LOW"), _p("f4", "LOW")]
    result = fid_has_severity(problems, "HIGH")
    assert result["f3"] is True, f"f3 has HIGH -> True; got {result.get('f3')}"
    assert result["f4"] is False, f"f4 has no HIGH -> False; got {result.get('f4')}"


def test_same_fid_in_multiple_classes() -> None:
    """Same fid across multiple classes is aggregated into one entry."""
    problems = [
        Problem(problem_class="A", finding_id="f5", severity="HIGH"),
        Problem(problem_class="B", finding_id="f5", severity="LOW"),
    ]
    result = fid_has_severity(problems, "HIGH")
    assert result["f5"] is True, f"f5 has HIGH (via class A) -> True; got {result.get('f5')}"
