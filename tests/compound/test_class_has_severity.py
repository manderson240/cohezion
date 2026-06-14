"""Item 680: class_has_severity() -- boolean flag: does each class have given severity?

class_has_severity(problems, severity) -> dict[str, bool].
Zero-inclusive: ALL classes present in input appear in result.
Classes without the queried severity get False (NOT absent).
Empty problems -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_has_severity


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_false_for_present_class_without_severity_primary_discriminator() -> None:
    """PRIMARY DISC.: class present in input but without queried severity -> False (not absent).

    class A: 3 HIGH + 0 CRITICAL -> class_has_severity(problems, 'CRITICAL')['A'] = False.
    Sparse impl would omit 'A'; this kills it.
    """
    problems = [_p("A", "HIGH")] * 3
    result = class_has_severity(problems, "CRITICAL")
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present (zero-inclusive); got {list(result)}"
    assert result["A"] is False, f"A has no CRITICAL -> False; got {result['A']} (absent=wrong)"
    assert isinstance(result["A"], bool), "Must be bool"


def test_true_for_class_with_matching_severity() -> None:
    """Class with the queried severity -> True."""
    problems = [_p("B", "CRITICAL")] * 2 + [_p("B", "HIGH")]
    result = class_has_severity(problems, "CRITICAL")
    assert result["B"] is True, f"B has CRITICAL -> True; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_has_severity([], "HIGH") == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes: A has HIGH, B does not."""
    problems = [_p("A", "HIGH"), _p("A", "LOW"), _p("B", "LOW"), _p("B", "LOW")]
    result = class_has_severity(problems, "HIGH")
    assert result["A"] is True, f"A has HIGH -> True; got {result.get('A')}"
    assert result["B"] is False, f"B has no HIGH -> False; got {result.get('B')}"


def test_case_sensitive_severity_match() -> None:
    """Severity match is case-sensitive (per existing convention uppercase)."""
    problems = [_p("A", "HIGH")]
    result = class_has_severity(problems, "HIGH")
    assert result["A"] is True, f"'HIGH' matches; got {result.get('A')}"
