"""Item 596: class_top_severity() -- dominant severity label per class (2026-06-08).

``class_top_severity(problems) -> dict[str, str]``:
Returns {class: dominant_severity_label} for each class.
Dominant = severity with the highest count.
Ties broken by alphabetically descending severity name (e.g. 'MEDIUM' beats 'LOW').
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns LABEL (str), not count or fraction.
     [A: HIGH x3, LOW x1] -> result['A'] == 'HIGH' (not 3 or 0.75).
     Kills impl returning the count or frequency.
  2. Most-frequent label selected (not least-frequent, not first-seen).
     [A: LOW x3, HIGH x1] -> result['A'] == 'LOW'.
     Kills impl returning the minority label.
  3. Tie broken by alphabetically DESCENDING label name.
     [A: HIGH x2, LOW x2] -> result['A'] == 'LOW' loses; 'HIGH' > 'LOW' alpha-desc -> 'HIGH'.
     Wait: alphabetically descending means 'M' > 'L' > 'H'; so 'MEDIUM' > 'LOW' > 'HIGH'.
     Tie [HIGH x2, LOW x2]: 'LOW' > 'HIGH' alphabetically desc -> result['A'] == 'LOW'.
     Kills impl using alpha-ascending (would pick 'HIGH' in a HIGH/LOW tie).
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Multiple independent classes — each gets its own dominant label.
     Kills impl returning a single value or computing across all classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_top_severity


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_returns_label_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: returns the severity LABEL (str), not a count or fraction.

    [A: HIGH x3, LOW x1] -> result['A'] == 'HIGH' (not 3 or 0.75).
    Kills impl returning the mode count or the proportion.
    """
    problems = [_p("A", "HIGH")] * 3 + [_p("A", "LOW")]
    result = class_top_severity(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {result}"
    assert result["A"] == "HIGH", (
        f"Dominant label is 'HIGH' (3 vs 1); got {result['A']!r} "
        f"(3 = returning count, 0.75 = returning fraction)"
    )
    assert isinstance(result["A"], str), (
        f"Value must be str label; got {type(result['A']).__name__}"
    )


def test_most_frequent_label_wins() -> None:
    """Most-frequent severity is selected (not least-frequent or first-seen).

    [A: LOW x3, HIGH x1] -> result['A'] == 'LOW'.
    Kills impl returning minority label or always returning same label.
    """
    problems = [_p("A", "LOW")] * 3 + [_p("A", "HIGH")]
    result = class_top_severity(problems)
    assert result["A"] == "LOW", f"'LOW' appears 3x (most frequent); got {result['A']!r}"


def test_ties_broken_by_alphabetically_descending_label() -> None:
    """Ties broken by alphabetically descending severity label name.

    Alphabetical descending order: 'Z' > 'A', so 'LOW' > 'HIGH' (L > H).
    [A: HIGH x2, LOW x2] -> tie -> 'LOW' > 'HIGH' (alpha desc) -> result['A'] == 'LOW'.
    [B: HIGH x1, MEDIUM x1] -> 'MEDIUM' > 'HIGH' (M > H) -> result['B'] == 'MEDIUM'.
    Kills impl using alpha-ascending (would give 'HIGH' for both).
    """
    # Case 1: HIGH vs LOW tie — 'LOW' wins (L > H alphabetically desc)
    problems_a = [_p("A", "HIGH")] * 2 + [_p("A", "LOW")] * 2
    result_a = class_top_severity(problems_a)
    assert result_a["A"] == "LOW", (
        f"Tie HIGH=2/LOW=2: 'LOW'>'HIGH' alpha-desc -> 'LOW'; got {result_a['A']!r} "
        f"('HIGH' = ascending order used)"
    )

    # Case 2: HIGH vs MEDIUM tie — 'MEDIUM' wins (M > H alphabetically desc)
    problems_b = [_p("B", "HIGH")] + [_p("B", "MEDIUM")]
    result_b = class_top_severity(problems_b)
    assert result_b["B"] == "MEDIUM", (
        f"Tie HIGH=1/MEDIUM=1: 'MEDIUM'>'HIGH' alpha-desc -> 'MEDIUM'; got {result_b['B']!r}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_top_severity([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_classes_independent() -> None:
    """Multiple classes each get their own dominant label independently.

    Kills impl computing across all classes or returning a single label.
    """
    problems = (
        [_p("A", "HIGH")] * 5 + [_p("A", "LOW")] + [_p("B", "CRITICAL")] * 2 + [_p("B", "HIGH")] * 4
    )
    result = class_top_severity(problems)
    assert "A" in result and "B" in result, f"Both classes must be present; got {list(result)}"
    assert result["A"] == "HIGH", f"Class A dominant is HIGH (5 vs 1); got {result['A']!r}"
    assert result["B"] == "HIGH", f"Class B dominant is HIGH (4 vs 2); got {result['B']!r}"
