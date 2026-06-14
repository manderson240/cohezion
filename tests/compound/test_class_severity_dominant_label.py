"""Item 718: class_severity_dominant_label() -- single most-common severity per class.

class_severity_dominant_label(problems) -> dict[str, str].
Returns label with highest count per class; ties broken by min(label) alphabetically.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns single LABEL str with alphabetical tie-break
     (not frozenset like class_severity_mode at item 598; not count);
     class A: LOW×3+HIGH×2 -> 'LOW' (most-common); frozenset-impl wrong; count-impl wrong.
  2. Tie broken alphabetically (min): class B: HIGH×2+LOW×2 -> 'HIGH' (alpha min of tied).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is str.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_dominant_label


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_most_common_label_primary_discriminator() -> None:
    """PRIMARY DISC.: returns most-common LABEL str not frozenset or count.

    class A: LOW×3 + HIGH×2 -> 'LOW' (3 > 2 so LOW wins).
    frozenset-impl gives {'LOW'} wrong; count-impl gives 3 wrong.
    """
    problems = [_p("A", "LOW"), _p("A", "LOW"), _p("A", "LOW"), _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_severity_dominant_label(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert result["A"] == "LOW", (
        f"LOW×3 > HIGH×2 -> 'LOW'; got {result['A']!r} "
        f"(frozenset-impl gives {{'LOW'}} wrong; count-impl gives 3 wrong)"
    )
    assert isinstance(result["A"], str), f"Must be str; got {type(result['A'])}"


def test_tie_broken_alphabetically() -> None:
    """Tie: min(tied_labels) alphabetically.

    class B: HIGH×2 + LOW×2 (tie) -> 'HIGH' (H < L alphabetically).
    """
    problems = [_p("B", "HIGH"), _p("B", "HIGH"), _p("B", "LOW"), _p("B", "LOW")]
    result = class_severity_dominant_label(problems)
    assert result["B"] == "HIGH", f"HIGH×2 tie LOW×2 -> 'HIGH' (H < L); got {result.get('B')!r}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_dominant_label([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computes independently."""
    problems = [_p("X", "CRITICAL"), _p("X", "CRITICAL"), _p("X", "HIGH")]  # X -> CRITICAL
    problems += [_p("Y", "INFO"), _p("Y", "LOW"), _p("Y", "LOW")]  # Y -> LOW
    result = class_severity_dominant_label(problems)
    assert result["X"] == "CRITICAL", f"X: CRIT×2 > HIGH×1 -> 'CRITICAL'; got {result.get('X')!r}"
    assert result["Y"] == "LOW", f"Y: LOW×2 > INFO×1 -> 'LOW'; got {result.get('Y')!r}"


def test_return_type_is_str() -> None:
    """Result values must be str."""
    problems = [_p("Z", "HIGH"), _p("Z", "HIGH")]
    result = class_severity_dominant_label(problems)
    assert isinstance(result["Z"], str), f"Must be str; got {type(result['Z'])}"
    assert result["Z"] == "HIGH", f"Only HIGH -> 'HIGH'; got {result.get('Z')!r}"
