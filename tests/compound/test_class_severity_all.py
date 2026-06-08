"""Item 684: class_severity_all() -- True if ALL problems in class match given severity set.

Complement of class_severity_any (682): all must match, not just any.
class_severity_all(problems, severities) -> dict[str, bool].
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: ALL must match (NOT any); class A: HIGH,HIGH,LOW -> False.
     any-impl (item 682) would return True; kills it.
  2. True when every problem matches a severity in the set.
  3. Empty -> {}.
  4. Multiple classes: independent True/False.
  5. Empty severity set -> all False (no problem can match the empty set).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_all


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_all_not_any_primary_discriminator() -> None:
    """PRIMARY DISC.: ALL must match (not just any).

    class A: HIGH,HIGH,LOW -> class_severity_all(problems, {'HIGH'}) = False.
    any-impl (class_severity_any) would give True because one HIGH matches;
    kills any-impl.
    """
    problems = [_p("A", "HIGH"), _p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_all(problems, {"HIGH"})
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    assert result["A"] is False, (
        f"HIGH,HIGH,LOW -> False when querying {{'HIGH'}} (LOW fails); "
        f"got {result['A']} (True = any-impl mistake)"
    )
    assert isinstance(result["A"], bool), "Must be bool"


def test_true_when_all_match() -> None:
    """All problems in class have severity in set -> True."""
    problems = [_p("B", "HIGH"), _p("B", "HIGH"), _p("B", "HIGH")]
    result = class_severity_all(problems, {"HIGH", "CRITICAL"})
    assert result["B"] is True, f"All HIGH, query {{HIGH,CRITICAL}} -> True; got {result['B']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_all([], {"HIGH"}) == {}


def test_multiple_classes_independent() -> None:
    """class A: all CRITICAL -> True; class B: MEDIUM,LOW -> False."""
    problems = (
        [_p("A", "CRITICAL")] * 3
        + [_p("B", "MEDIUM"), _p("B", "LOW")]
    )
    result = class_severity_all(problems, {"CRITICAL", "HIGH"})
    assert result["A"] is True, f"A: all CRITICAL -> True; got {result.get('A')}"
    assert "B" in result, "B must be present"
    assert result["B"] is False, (
        f"B: MEDIUM+LOW, neither in {{CRITICAL,HIGH}} -> False; got {result.get('B')}"
    )


def test_empty_severity_set_all_false() -> None:
    """Empty severity set -> every class False (nothing can match frozenset())."""
    problems = [_p("X", "HIGH"), _p("Y", "CRITICAL")]
    result = class_severity_all(problems, set())
    assert result["X"] is False, f"Empty set -> False; got {result.get('X')}"
    assert result["Y"] is False, f"Empty set -> False; got {result.get('Y')}"
