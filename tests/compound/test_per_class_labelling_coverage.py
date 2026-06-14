"""Item 294: per_class_labelling_coverage() — per-class labelling coverage fraction (2026-06-08).

``per_class_labelling_coverage(problems: list[Problem]) -> dict[str, float]``:
Returns {class: labelled_fraction} for every class. Each class's denominator is
its OWN problem count (not global total). 1.0 = all labelled; 0.0 = none labelled.
Empty -> {}. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: each class uses its OWN total as denominator, not global total.
     alpha has 2 problems (1 labelled) -> 0.5; beta has 4 problems (1 labelled) -> 0.25.
     If global total (6) is used as denominator: alpha would be 1/6≈0.167, beta 1/6≈0.167.
     Kills impl dividing by global total.
  2. Class with all labelled problems -> 1.0.
     Kills impl capping at < 1.0.
  3. Class with all unlabelled problems -> 0.0.
     Kills impl that counts unlabelled as labelled.
  4. Empty input -> {}.
     Kills impl raising on empty.
  5. Return type is dict[str, float].
     Kills impl returning dict[str, int] or list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    per_class_labelling_coverage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    """Unlabelled problem (severity='')."""
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_per_class_denominator_not_global() -> None:
    """Each class divides by its OWN problem count, not the global total.

    PRIMARY DISCRIMINATOR: kills impl using global total as denominator.
    alpha: 1 labelled / 2 total = 0.5.
    beta: 1 labelled / 4 total = 0.25.
    Global total = 6; if global used: both = 1/6 ≈ 0.167 (WRONG).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),  # labelled
        _p("alpha", 1),  # unlabelled
        _ps("beta", 0, "HIGH"),  # labelled
        _p("beta", 1),  # unlabelled
        _p("beta", 2),  # unlabelled
        _p("beta", 3),  # unlabelled
    ]
    result = per_class_labelling_coverage(problems)
    assert abs(result.get("alpha", -1) - 0.5) < 1e-9, "alpha: 1/2 = 0.5; got " + repr(
        result.get("alpha")
    )
    assert abs(result.get("beta", -1) - 0.25) < 1e-9, "beta: 1/4 = 0.25; got " + repr(
        result.get("beta")
    )


def test_all_labelled_class_is_1_0() -> None:
    """A class with all labelled problems -> 1.0.

    Kills impl capping below 1.0.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
    ]
    result = per_class_labelling_coverage(problems)
    assert result.get("alpha") == 1.0, "alpha all labelled -> 1.0; got " + repr(result.get("alpha"))


def test_all_unlabelled_class_is_0_0() -> None:
    """A class with all unlabelled problems -> 0.0.

    Kills impl that counts unlabelled as labelled.
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
    ]
    result = per_class_labelling_coverage(problems)
    assert result.get("alpha") == 0.0, "alpha all unlabelled -> 0.0; got " + repr(
        result.get("alpha")
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl raising on empty.
    """
    result = per_class_labelling_coverage([])
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_return_type_is_dict_str_float() -> None:
    """Return type is dict[str, float].

    Kills impl returning int values or a list.
    """
    problems = [_ps("alpha", 0, "HIGH"), _p("alpha", 1)]
    result = per_class_labelling_coverage(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, frac in result.items():
        assert isinstance(cls, str) and isinstance(frac, float), (
            "Keys str, values float; got " + repr((type(cls), type(frac)))
        )
