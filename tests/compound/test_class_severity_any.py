"""Item 682: class_severity_any() -- True if ANY problem in class has a severity from the set.

Generalizes class_has_severity (680) to a SET of severities.
class_severity_any(problems, severities) -> dict[str, bool].
Zero-inclusive (all classes present).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: takes a SET of severities (NOT a single string).
     class A: HIGH,LOW -> class_severity_any(problems, {'CRITICAL','HIGH'})['A'] = True.
     Single-severity impl (item 680 copy) would fail since it expects str not set.
  2. False for class whose problems are all outside the severity set.
  3. Empty -> {}.
  4. Multiple classes: independent True/False.
  5. Works with list input as well as set (flexible container).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_any


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_set_of_severities_primary_discriminator() -> None:
    """PRIMARY DISC.: accepts a SET of severities; class A: HIGH,LOW in set -> True.

    class A: 3 HIGH + 2 LOW. Query set = {'CRITICAL','HIGH'}.
    HIGH is in set -> True (LOW not in set is irrelevant; any match suffices).
    Single-string impl (item 680 copy expecting str) would TypeError or be wrong.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")] * 2
    result = class_severity_any(problems, {"CRITICAL", "HIGH"})
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    assert result["A"] is True, f"HIGH in {{'CRITICAL','HIGH'}} -> True; got {result['A']}"
    assert isinstance(result["A"], bool), "Must be bool"


def test_false_for_class_with_no_matching_severity() -> None:
    """False for class whose problems are all outside the severity set."""
    problems = [_p("B", "LOW")] * 4 + [_p("B", "INFO")]
    result = class_severity_any(problems, {"CRITICAL", "HIGH", "MEDIUM"})
    assert "B" in result, "B must be present (zero-inclusive)"
    assert result["B"] is False, (
        f"LOW,INFO not in {{CRITICAL,HIGH,MEDIUM}} -> False; got {result.get('B')}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_any([], {"HIGH"}) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes get independent results.

    class A: CRITICAL -> True (in set {'CRITICAL','HIGH'}).
    class B: LOW,INFO -> False (neither in set).
    """
    problems = [_p("A", "CRITICAL")] * 2 + [_p("B", "LOW")] * 3 + [_p("B", "INFO")]
    result = class_severity_any(problems, {"CRITICAL", "HIGH"})
    assert result["A"] is True, f"A has CRITICAL -> True; got {result.get('A')}"
    assert "B" in result, "B must be present (zero-inclusive)"
    assert result["B"] is False, f"B has no CRIT/HIGH -> False; got {result.get('B')}"


def test_list_input_accepted() -> None:
    """List of severities (not just set) must work."""
    problems = [_p("X", "MEDIUM")] * 2 + [_p("Y", "LOW")]
    result = class_severity_any(problems, ["HIGH", "MEDIUM"])  # list, not set
    assert result["X"] is True, f"MEDIUM in ['HIGH','MEDIUM'] -> True; got {result.get('X')}"
    assert result["Y"] is False, f"LOW not in ['HIGH','MEDIUM'] -> False; got {result.get('Y')}"
