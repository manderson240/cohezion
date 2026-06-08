"""Item 349: bottom_n_problem_classes() -- bottom N classes by problem count (2026-06-08).

``bottom_n_problem_classes(problems, n) -> list[str]``:
Returns up to N class names with the lowest problem count (total records),
ascending.  Ties broken by ascending class name.
n=0 -> [].  n > num_classes -> all classes.  Empty input -> [].
Pure; no I/O.  Complements top_n_problem_classes.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: lowest-count class is first (kills impl returning highest-count first).
  2. Returns class NAME strings not (name, count) tuples.
     Kills impl returning tuples.
  3. Tie-break by ascending class name.
     Kills arbitrary tie-breaking.
  4. n=0 returns [] without raising.
     Kills impl returning all classes.
  5. n > num_classes returns all classes without raising.
     Kills impl crashing on large n.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    bottom_n_problem_classes,
)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_lowest_count_class_is_first() -> None:
    """Class with fewest problems is ranked first.

    PRIMARY DISCRIMINATOR: kills impl returning highest-count first.
    alpha=3, beta=2, gamma=1 -> bottom 1 = ['gamma'].
    """
    problems = (
        [_p("alpha", i) for i in range(3)]
        + [_p("beta", i) for i in range(2)]
        + [_p("gamma", 0)]
    )
    result = bottom_n_problem_classes(problems, 1)
    assert result == ["gamma"], "gamma(1) is bottom; got " + repr(result)


def test_returns_class_name_strings_not_tuples() -> None:
    """Returns str names not (name, count) tuples.

    Kills impl returning list of tuples.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("beta", 1)]
    result = bottom_n_problem_classes(problems, 1)
    assert isinstance(result[0], str), "Must return str; got " + repr(type(result[0]))
    assert result[0] == "alpha", "alpha(1) < beta(2); got " + repr(result[0])


def test_tie_break_ascending_class_name() -> None:
    """Equal counts -> alphabetically first class name wins.

    Kills arbitrary tie-breaking.
    beta=2, alpha=2 -> bottom 2 = [alpha, beta] (ascending name).
    """
    problems = [_p("beta", 0), _p("beta", 1), _p("alpha", 0), _p("alpha", 1)]
    result = bottom_n_problem_classes(problems, 2)
    assert result == ["alpha", "beta"], "Tie -> ascending name; got " + repr(result)


def test_n_zero_returns_empty_list() -> None:
    """n=0 returns [] without raising."""
    assert bottom_n_problem_classes([_p("alpha", 0)], 0) == []


def test_n_exceeds_classes_returns_all() -> None:
    """n > num_classes returns all classes without raising or padding."""
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = bottom_n_problem_classes(problems, 50)
    assert set(result) == {"alpha", "beta"} and len(result) == 2, repr(result)
