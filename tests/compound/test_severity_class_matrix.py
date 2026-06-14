"""Item 342: severity_class_matrix() — 2D count matrix severity x class (2026-06-08).

``severity_class_matrix(problems) -> dict[str, dict[str, int]]``:
Transpose of severity_heatmap.  Outer key = severity, inner key = class, value = count.
Unlabelled problems (severity='') excluded.  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer key is SEVERITY not class (axes correctly transposed).
     Kills impl returning severity_heatmap (which has class as outer key).
  2. Inner dict has correct per-class count at a severity.
     Kills impl transposing but getting counts wrong.
  3. Unlabelled problems excluded (no '' outer key).
     Kills impl including unlabelled as a severity.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Severity with 1 class has inner dict of size 1.
     Kills impl aggregating all classes into the same inner count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_class_matrix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_outer_key_is_severity_not_class() -> None:
    """Outer key must be severity, not class name.

    PRIMARY DISCRIMINATOR: kills impl returning severity_heatmap (transposed axes).
    alpha: 2 HIGH. beta: 1 HIGH. Outer key 'HIGH' -> inner {'alpha': 2, 'beta': 1}.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("beta", 0, "HIGH"),
    ]
    result = severity_class_matrix(problems)
    assert "HIGH" in result, "Outer key must be severity 'HIGH'; got keys " + repr(
        set(result.keys())
    )
    assert "alpha" not in result, (
        "Outer key must NOT be class 'alpha' (would mean axes are transposed wrong)"
    )


def test_inner_dict_has_correct_per_class_counts() -> None:
    """Inner dict correctly counts records per class at that severity.

    Kills impl that transposes but gets counts wrong.
    alpha: 2 HIGH, beta: 3 HIGH. HIGH -> {alpha: 2, beta: 3}.
    LOW -> {alpha: 1}.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
        _ps("beta", 2, "HIGH"),
        _ps("alpha", 2, "LOW"),
    ]
    result = severity_class_matrix(problems)
    assert result.get("HIGH", {}).get("alpha") == 2, "HIGH.alpha=2; got " + repr(result.get("HIGH"))
    assert result.get("HIGH", {}).get("beta") == 3, "HIGH.beta=3; got " + repr(result.get("HIGH"))
    assert result.get("LOW", {}).get("alpha") == 1, "LOW.alpha=1; got " + repr(result.get("LOW"))


def test_unlabelled_excluded_no_empty_string_key() -> None:
    """Unlabelled problems (severity='') are excluded from result.

    Kills impl including '' as an outer severity key.
    """
    problems = [_ps("alpha", 0, "HIGH"), _p("beta", 0)]
    result = severity_class_matrix(problems)
    assert "" not in result, "'' must not be an outer key; got " + repr(result)


def test_empty_input_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert severity_class_matrix([]) == {}, "empty -> {}; got " + repr(severity_class_matrix([]))


def test_severity_with_one_class_has_inner_dict_size_one() -> None:
    """Severity with only one class has inner dict with exactly one entry.

    Kills impl aggregating all classes into one count.
    LOW has only alpha: 1 record -> LOW -> {alpha: 1} (size 1).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
    ]
    result = severity_class_matrix(problems)
    low_inner = result.get("LOW", {})
    assert len(low_inner) == 1, "LOW has 1 class -> inner dict size 1; got " + repr(low_inner)
    assert low_inner.get("alpha") == 1, "LOW.alpha=1; got " + repr(low_inner)
