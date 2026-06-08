"""Item 686: class_severity_none() -- True if NO problem in class has a severity from the set.

Logical complement of class_severity_any (682): none may match (not any).
class_severity_none(problems, severities) -> dict[str, bool].
Zero-inclusive: ALL classes in input appear in result.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: ALL must be ABSENT (not just some).
     class A: HIGH,LOW; query {'HIGH'} -> False (HIGH is in set, NOT none-match).
     A class with one matching severity: any=True, none=False.
     Kills flipped-any-impl (which would be `not class_severity_any`... same result but confirms logic).
     Extra kill: class B: LOW,LOW; query {'HIGH'} -> True (none of B's severities in set).
  2. True when no problem matches.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Empty severity set -> all True (vacuous truth: nothing can match empty set).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_none


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_false_when_any_severity_matches_primary_discriminator() -> None:
    """PRIMARY DISC.: False when even ONE problem has the queried severity.

    class A: HIGH+LOW; class_severity_none(problems, {'HIGH'})['A'] = False.
    class B: LOW+LOW; class_severity_none(problems, {'HIGH'})['B'] = True.
    Distinguishes none from all: all-impl gives False for A (different reason), True for B.
    """
    problems = [_p("A", "HIGH"), _p("A", "LOW"), _p("B", "LOW"), _p("B", "LOW")]
    result = class_severity_none(problems, {"HIGH"})
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    assert result["A"] is False, (
        f"A has HIGH (in set) -> none=False; got {result['A']}"
    )
    assert isinstance(result["A"], bool), "Must be bool"
    assert result["B"] is True, (
        f"B has only LOW (not in set) -> none=True; got {result['B']}"
    )


def test_true_when_no_matching_severity() -> None:
    """True when class has problems but none match the queried set."""
    problems = [_p("C", "MEDIUM"), _p("C", "INFO"), _p("C", "LOW")]
    result = class_severity_none(problems, {"CRITICAL", "HIGH"})
    assert result["C"] is True, (
        f"C has MEDIUM/INFO/LOW, none in set -> True; got {result.get('C')}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_none([], {"HIGH"}) == {}


def test_multiple_classes_independent() -> None:
    """D (has CRITICAL in set) = False; E (only LOW) = True."""
    problems = [_p("D", "CRITICAL"), _p("D", "HIGH"), _p("E", "LOW")]
    result = class_severity_none(problems, {"CRITICAL"})
    assert result["D"] is False, f"D has CRITICAL -> False; got {result.get('D')}"
    assert result["E"] is True, f"E has only LOW -> True; got {result.get('E')}"


def test_empty_severity_set_all_true() -> None:
    """Empty severity set -> all True (vacuously none match an empty set)."""
    problems = [_p("F", "HIGH"), _p("G", "CRITICAL")]
    result = class_severity_none(problems, set())
    assert result["F"] is True, f"Empty set -> vacuous True; got {result.get('F')}"
    assert result["G"] is True, f"Empty set -> vacuous True; got {result.get('G')}"
