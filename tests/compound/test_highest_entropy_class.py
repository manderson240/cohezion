"""Item 261: highest_entropy_class() — class with the most diverse severity distribution (2026-06-08).

``highest_entropy_class(problems: list[Problem]) -> str | None``:
Returns the class name whose labelled severity distribution has the highest
Shannon entropy (as computed by ``class_severity_entropy``).  Ties broken
alphabetically ascending.  Returns ``None`` when no class has ≥2 distinct
labelled severities (i.e. all classes have H=0) or when input is empty.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: maximises Shannon entropy, not total problem count or
     severity count.  A class with equal HIGH/LOW (H=1.0) beats a class with
     many problems all at the same severity (H=0.0).
  2. None when all classes have H=0 (mono-severity or unlabelled only).
     Kills impl that returns the class with the most problems.
  3. Tie-break: alphabetically ascending class name.
     Kills impl with wrong tie-break direction.
  4. None on empty input.
     Kills impl that raises on empty input.
  5. Return type str | None.
     Kills impl returning a list or dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    highest_entropy_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_maximises_entropy_not_count() -> None:
    """Returns class with highest entropy, not most problems.

    PRIMARY DISCRIMINATOR: kills impl ranking by problem count.
    alpha: 100 CRITICAL (H=0). beta: 1 HIGH + 1 LOW (H=1.0).
    beta has fewer problems but higher entropy → beta wins.
    """
    problems = (
        [_ps("alpha", i, "CRITICAL") for i in range(100)]
        + [_ps("beta", 0, "HIGH"), _ps("beta", 1, "LOW")]
    )
    result = highest_entropy_class(problems)
    assert result == "beta", (
        "beta H=1.0 > alpha H=0.0; beta wins despite fewer problems; got " + repr(result)
    )


def test_none_when_all_classes_mono_severity() -> None:
    """None when no class has ≥2 distinct labelled severities (H=0 for all).

    Kills impl that returns the class with the most problems.
    """
    problems = [
        _ps("alpha", i, "CRITICAL") for i in range(5)
    ] + [
        _ps("beta", i, "HIGH") for i in range(3)
    ]
    result = highest_entropy_class(problems)
    assert result is None, (
        "All classes mono-severity → H=0 → None; got " + repr(result)
    )


def test_tie_break_alphabetically_ascending() -> None:
    """Tie-break: alphabetically ascending class name.

    gamma and alpha both have equal HIGH/LOW (H=1.0) → alpha wins.
    """
    problems = [
        _ps("gamma", 0, "HIGH"), _ps("gamma", 1, "LOW"),
        _ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW"),
    ]
    result = highest_entropy_class(problems)
    assert result == "alpha", "alpha < gamma → alpha wins on tie; got " + repr(result)


def test_none_on_empty_input() -> None:
    """Empty input → None.

    Kills impl that raises on empty input.
    """
    result = highest_entropy_class([])
    assert result is None, "Empty input → None; got " + repr(result)


def test_return_type_is_str_or_none() -> None:
    """Return type is str | None.

    Kills impl returning a list or dict.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = highest_entropy_class(problems)
    assert isinstance(result, str), "With match → str; got " + repr(type(result))
    result_none = highest_entropy_class([_ps("beta", 0, "CRITICAL")])
    assert result_none is None, "Mono-severity → None; got " + repr(result_none)
