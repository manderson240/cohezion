"""Item 260: class_severity_entropy() — Shannon entropy of severity distribution (2026-06-08).

``class_severity_entropy(problems: list[Problem], cls: str) -> float``:
Returns the Shannon entropy (base-2 bits) of the non-empty severity distribution
for problems in *cls*::

    H = -sum(p * log2(p))   over all non-empty severity labels for class cls

Unlabelled problems (``severity=""``) are excluded from the distribution.
Returns ``0.0`` when the class has only one non-empty severity, when no labelled
problems exist, or when the class is missing.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: distribution is over labelled problems ONLY.
     Kills impl that includes unlabelled (severity="") in the denominator,
     which would make p(HIGH) = 1/3 instead of 1/2 for 1 HIGH + 1 unlabelled.
  2. Returns 0.0 when all labelled problems have the same severity.
     Kills impl that returns a non-zero value for a single-category distribution.
  3. Returns 1.0 for a two-severity uniform distribution (H = log2(2) = 1.0).
     Kills impl using natural log instead of log2.
  4. Returns 0.0 for an unknown class or empty input.
     Kills impl that raises KeyError or ZeroDivisionError.
  5. Return type is float.
     Kills impl returning int or None.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_entropy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unlabelled_excluded_from_distribution() -> None:
    """Distribution is over labelled problems only; unlabelled excluded.

    PRIMARY DISCRIMINATOR: kills impl that includes unlabelled in denominator.
    alpha: 1 HIGH + 1 LOW + 2 unlabelled.  Labelled only: p(HIGH)=0.5, p(LOW)=0.5.
    H = 1.0.  If unlabelled included: p(HIGH)=0.25, p(LOW)=0.25 → H ≈ 1.0 still
    BUT we verify the exact value matches labelled-only calculation.
    We use a 2:1 ratio to make the two calculations diverge:
    1 HIGH + 0 LOW + 1 unlabelled → labelled-only: H=0 (single sev HIGH).
    If unlabelled counted: p(HIGH)=0.5, p(NONE)=0.5 → H=1.0.  Must return 0.0.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        Problem(problem_class="alpha", finding_id="alpha:1"),  # severity=""
    ]
    result = class_severity_entropy(problems, "alpha")
    assert result == 0.0, (
        "1 HIGH + 1 unlabelled: only HIGH labelled → single severity → H=0.0; "
        "if unlabelled counted H=1.0; got " + repr(result)
    )


def test_zero_for_single_severity() -> None:
    """Returns 0.0 when all labelled problems have the same severity.

    Kills impl that returns non-zero for a single-category distribution.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = class_severity_entropy(problems, "alpha")
    assert result == 0.0, "Single severity → entropy 0.0; got " + repr(result)


def test_one_bit_for_two_equal_severity_classes() -> None:
    """Returns 1.0 for a two-severity uniform distribution.

    Kills impl using natural log (ln) instead of log2.
    1 HIGH + 1 LOW → p=0.5 each → H = -2*(0.5*log2(0.5)) = 1.0 bit.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = class_severity_entropy(problems, "alpha")
    assert abs(result - 1.0) < 1e-9, (
        "Uniform 2-class → H=1.0 bit; got " + repr(result)
    )


def test_zero_for_unknown_class_or_empty() -> None:
    """Returns 0.0 for unknown class or empty input.

    Kills impl that raises KeyError or ZeroDivisionError.
    """
    assert class_severity_entropy([], "alpha") == 0.0, "Empty input → 0.0"
    problems = [_ps("alpha", 0, "HIGH")]
    assert class_severity_entropy(problems, "unknown") == 0.0, "Unknown class → 0.0"


def test_return_type_is_float() -> None:
    """Return type is float.

    Kills impl returning int or None.
    """
    result = class_severity_entropy([_ps("alpha", 0, "HIGH")], "alpha")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
