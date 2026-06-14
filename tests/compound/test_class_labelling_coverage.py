"""Item 268: class_labelling_coverage() — per-class fraction of labelled problems (2026-06-08).

``class_labelling_coverage(problems: list[Problem]) -> dict[str, float]``:
Returns {class_name: fraction_labelled} for every class in the scan.
Denominator for each class is that class's total problem count.
Empty input -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator is per-class total, not global total.
     Kills impl that uses global labelling_coverage(problems).
  2. 0.0 for a class with all-unlabelled problems.
     Kills impl that skips unlabelled classes.
  3. 1.0 for a class where every problem is labelled.
     Verifies the fully-covered case.
  4. Empty input -> {}.
     Kills impl that raises on empty input.
  5. Return type is dict[str, float].
     Kills impl returning a global float or list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_labelling_coverage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_per_class_denominator_not_global() -> None:
    """Per-class denominator is class total, not global total.

    PRIMARY DISCRIMINATOR: kills impl using global labelling_coverage.
    alpha: 1 labelled + 1 unlabelled = 0.5.
    beta: 3 labelled + 0 unlabelled = 1.0.
    Global would be 4/5 = 0.8 for both (wrong).
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1),  # unlabelled
        _p("beta", 0, "LOW"),
        _p("beta", 1, "LOW"),
        _p("beta", 2, "HIGH"),
    ]
    result = class_labelling_coverage(problems)
    assert abs(result["alpha"] - 0.5) < 1e-9, "alpha: 1/2=0.5; got " + repr(result.get("alpha"))
    assert abs(result["beta"] - 1.0) < 1e-9, "beta: 3/3=1.0; got " + repr(result.get("beta"))


def test_zero_for_all_unlabelled_class() -> None:
    """0.0 for a class where all problems lack severity.

    Kills impl that skips unlabelled classes or returns None.
    """
    problems = [_p("alpha", i) for i in range(3)]
    result = class_labelling_coverage(problems)
    assert "alpha" in result, "alpha must appear even if all unlabelled"
    assert result["alpha"] == 0.0, "All unlabelled -> 0.0; got " + repr(result["alpha"])


def test_one_for_fully_labelled_class() -> None:
    """1.0 for a class where every problem has a severity.

    Verifies the fully-covered case.
    """
    problems = [_p("alpha", i, "HIGH") for i in range(4)]
    result = class_labelling_coverage(problems)
    assert abs(result["alpha"] - 1.0) < 1e-9, "All labelled -> 1.0; got " + repr(
        result.get("alpha")
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl that raises on empty input.
    """
    result = class_labelling_coverage([])
    assert result == {}, "Empty input -> {}; got " + repr(result)


def test_return_type_is_dict_of_floats() -> None:
    """Return type is dict[str, float].

    Kills impl returning a global float scalar or a list.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("beta", 0)]
    result = class_labelling_coverage(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for k, v in result.items():
        assert isinstance(k, str), "Keys must be str"
        assert isinstance(v, float), "Values must be float; got " + repr(type(v))
