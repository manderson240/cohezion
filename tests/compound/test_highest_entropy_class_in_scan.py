"""Item 319: highest_entropy_class_in_scan() — class with most uncertain severity distribution (2026-06-08).

``highest_entropy_class_in_scan(problems) -> str | None``:
Returns the class name whose severity distribution has the highest Shannon
entropy (from severity_entropy_by_class).  Tie-break: alphabetically
ascending class name.  Returns None when all classes have entropy 0.0 or
when problems is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class with HIGHEST H, not lowest.
     Kills impl with reversed comparator (min instead of max).
  2. Tie-break: alphabetically ascending class name.
     Kills impl with wrong tie-break direction (descending).
  3. Returns None when all classes have H=0.0 (no labelled diversity).
     Kills impl returning a class even when all entropies are zero.
  4. Empty input returns None.
     Kills impl that crashes or returns '' on empty list.
  5. Return type is str | None.
     Kills impl returning float or raising exception.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    highest_entropy_class_in_scan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_with_highest_entropy_not_lowest() -> None:
    """Returns class with the HIGHEST Shannon entropy.

    PRIMARY DISCRIMINATOR: kills impl using min instead of max.
    alpha: 1 HIGH (H=0.0 — single severity, no spread).
    beta: 1 HIGH + 1 LOW (H=1.0 — maximum spread for 2 labels).
    Must return 'beta'.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("beta", 0, "HIGH"),
        _p("beta", 1, "LOW"),
    ]
    result = highest_entropy_class_in_scan(problems)
    assert result == "beta", f"beta has H=1.0 > alpha H=0.0 -> 'beta'; got {result!r}"


def test_tie_break_ascending_alphabetically() -> None:
    """Tie in entropy broken by ascending class name (alphabetically smallest first).

    Kills impl with descending tie-break.
    alpha and beta both have equal 2-severity distributions (H=1.0 each).
    alpha < beta alphabetically -> must return 'alpha'.
    """
    problems = [
        _p("beta", 0, "HIGH"),
        _p("beta", 1, "LOW"),
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "LOW"),
    ]
    result = highest_entropy_class_in_scan(problems)
    assert result == "alpha", f"alpha=beta=H=1.0, alpha<beta alphabetically -> 'alpha'; got {result!r}"


def test_returns_none_when_all_entropy_zero() -> None:
    """Returns None when every class has entropy 0.0 (no labelled diversity).

    Kills impl returning a class even when all entropies are zero.
    alpha: all HIGH (H=0.0); beta: all LOW (H=0.0).
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "HIGH"),
        _p("beta", 0, "LOW"),
        _p("beta", 1, "LOW"),
    ]
    result = highest_entropy_class_in_scan(problems)
    assert result is None, f"all classes H=0.0 -> None; got {result!r}"


def test_empty_input_returns_none() -> None:
    """Empty input returns None.

    Kills impl that crashes or returns '' on empty list.
    """
    result = highest_entropy_class_in_scan([])
    assert result is None, f"empty -> None; got {result!r}"


def test_return_type_is_str_or_none() -> None:
    """Return type is str (when found) or None (when not found).

    Kills impl returning float or raising exception.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("alpha", 1, "LOW")]
    result = highest_entropy_class_in_scan(problems)
    assert isinstance(result, str), f"Must return str when found; got {type(result)!r}"

    none_result = highest_entropy_class_in_scan([])
    assert none_result is None, f"Must return None on empty; got {none_result!r}"
