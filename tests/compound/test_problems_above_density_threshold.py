"""Item 331: problems_above_density_threshold() — problems from high-density classes (2026-06-08).

``problems_above_density_threshold(problems, threshold) -> list[Problem]``:
Returns all Problem objects from classes whose density (class_count/total) >= threshold.
Delegates density computation to problem_density_by_class.
Preserves original order.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: threshold=0.0 returns ALL problems.
     Kills impl that returns empty list for zero threshold.
  2. Density exactly equal to threshold IS included (>= not >).
     Kills impl using strict > comparison.
  3. Empty input returns [].
     Kills impl raising on division by zero.
  4. threshold > 1.0 returns [] (no density can exceed 1.0).
     Kills impl returning all problems when threshold > 1.0.
  5. Only problems from qualifying classes are returned, in original order.
     Kills impl returning class names or counts instead of Problem objects.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_above_density_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_zero_threshold_returns_all_problems() -> None:
    """threshold=0.0 returns ALL problems.

    PRIMARY DISCRIMINATOR: kills impl that returns empty on threshold=0.0.
    Every class has density >= 0.0, so all problems must be returned.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("alpha", 1)]
    result = problems_above_density_threshold(problems, 0.0)
    assert set(p.finding_id for p in result) == {"alpha:0", "alpha:1", "beta:0"}, (
        "threshold=0.0 -> all problems returned; got " + repr(result)
    )


def test_exact_density_match_is_included() -> None:
    """Density exactly equal to threshold is included (>= not >).

    Kills impl using strict > comparison.
    3 problems: alpha has 2/3 density, beta has 1/3.
    threshold=2/3 -> alpha qualifies (density==threshold), beta does not.
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _p("beta", 0)]
    # alpha density = 2/3; use threshold = 2/3
    threshold = 2 / 3
    result = problems_above_density_threshold(problems, threshold)
    result_ids = {p.finding_id for p in result}
    assert "alpha:0" in result_ids and "alpha:1" in result_ids, (
        "alpha density == threshold -> alpha included; got " + repr(result)
    )
    assert "beta:0" not in result_ids, "beta density < threshold -> beta excluded; got " + repr(
        result
    )


def test_empty_input_returns_empty_list() -> None:
    """Empty input returns [].

    Kills impl raising on division by zero.
    """
    result = problems_above_density_threshold([], 0.5)
    assert result == [], "empty input -> []; got " + repr(result)


def test_threshold_above_one_returns_empty() -> None:
    """threshold > 1.0 returns [] since no density can exceed 1.0.

    Kills impl that returns all problems when threshold > 1.0.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problems_above_density_threshold(problems, 1.5)
    assert result == [], "threshold > 1.0 -> no class qualifies -> []; got " + repr(result)


def test_only_qualifying_class_problems_returned_in_order() -> None:
    """Only problems from qualifying classes returned, in original order.

    Kills impl returning class names or reordering results.
    5 problems: alpha×3 (density=3/5=0.6), beta×2 (density=2/5=0.4).
    threshold=0.5 -> only alpha qualifies.
    """
    problems = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("alpha", 1),
        _p("beta", 1),
        _p("alpha", 2),
    ]
    result = problems_above_density_threshold(problems, 0.5)
    assert all(p.problem_class == "alpha" for p in result), (
        "Only alpha problems returned; got " + repr(result)
    )
    assert [p.finding_id for p in result] == ["alpha:0", "alpha:1", "alpha:2"], (
        "Original insertion order preserved; got " + repr([p.finding_id for p in result])
    )


def test_return_type_is_list_of_problems() -> None:
    """Return type is list[Problem], not class names or counts.

    Kills impl returning string class names or integer counts.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]
    result = problems_above_density_threshold(problems, 0.5)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    for item in result:
        assert isinstance(item, Problem), "Each element must be Problem; got " + repr(type(item))
