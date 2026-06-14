"""Item 316: problem_density_by_class() — class problem count as fraction of total (2026-06-08).

``problem_density_by_class(problems) -> dict[str, float]``:
Returns {class: count(class)/total_problems} for every class in the scan.
Density = class_count / total_count_of_all_problems (NOT class_count / class_count).
Values sum to 1.0 (within float precision).  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: density = class_count / total_problems (not class_count/class_count).
     Kills impl dividing by class size (would give 1.0 for every class).
  2. All densities sum to 1.0 (within float precision 1e-9).
     Kills impl that produces inconsistent fractions.
  3. Class with all problems has density 1.0 (only 1 class present).
     Kills impl with off-by-one in total count.
  4. Empty input -> {}.
     Kills impl that crashes or divides by zero.
  5. Return type is dict[str, float] with float values in [0.0, 1.0].
     Kills impl returning int counts or values outside valid range.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_density_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_density_is_class_count_divided_by_total() -> None:
    """Density = class_count / total_problems (not class_count / class_count).

    PRIMARY DISCRIMINATOR: kills impl dividing by class size (gives 1.0 everywhere).
    alpha: 3 problems out of 5 total -> density = 3/5 = 0.6.
    beta: 2 problems out of 5 total -> density = 2/5 = 0.4.
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),
        _p("beta", 0),
        _p("beta", 1),
    ]
    result = problem_density_by_class(problems)
    assert abs(result["alpha"] - 0.6) < 1e-9, "alpha: 3/5=0.6; got " + repr(result.get("alpha"))
    assert abs(result["beta"] - 0.4) < 1e-9, "beta: 2/5=0.4; got " + repr(result.get("beta"))


def test_densities_sum_to_one() -> None:
    """All density values sum to 1.0 (within float precision).

    Kills impl with inconsistent fractions.
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("beta", 0),
        _p("gamma", 0),
        _p("gamma", 1),
        _p("gamma", 2),
    ]
    result = problem_density_by_class(problems)
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-9, "All densities must sum to 1.0; got sum=" + repr(total)


def test_single_class_has_density_one() -> None:
    """Only one class present -> its density = 1.0 (it has all problems).

    Kills impl with off-by-one in total count.
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _p("alpha", 2)]
    result = problem_density_by_class(problems)
    assert abs(result.get("alpha", -1) - 1.0) < 1e-9, (
        "alpha only class -> density=1.0; got " + repr(result.get("alpha"))
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl that crashes or divides by zero.
    """
    result = problem_density_by_class([])
    assert result == {}, "empty -> {}; got " + repr(result)


def test_return_type_is_dict_of_floats_in_valid_range() -> None:
    """Return type is dict[str, float] with values in [0.0, 1.0].

    Kills impl returning int counts or out-of-range values.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problem_density_by_class(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, density in result.items():
        assert isinstance(density, float), (
            "Value for " + repr(cls) + " must be float; got " + repr(type(density))
        )
        assert 0.0 <= density <= 1.0, (
            "Density for " + repr(cls) + " must be in [0,1]; got " + repr(density)
        )
