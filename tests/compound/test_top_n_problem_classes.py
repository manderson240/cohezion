"""Item 348: top_n_problem_classes() — top N classes by problem count (2026-06-08).

``top_n_problem_classes(problems, n) -> list[str]``:
Returns up to N class names with the highest problem count (total records),
descending.  Ties broken by ascending class name.
n=0 -> [].  n > num_classes -> all classes ranked.  Empty input -> [].
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class NAMES not (name, count) tuples.
     Kills impl returning tuples or counts.
  2. Highest-count class is first (descending order).
     Kills impl returning ascending count.
  3. Tie-break by ascending class name.
     Kills impl with arbitrary or descending tie-break.
  4. n=0 returns [] without error.
     Kills impl returning all classes for n=0.
  5. n > number of classes returns all classes (no padding / no error).
     Kills impl crashing or padding with None.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_problem_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_names_not_tuples() -> None:
    """Returns class names (str), not (name, count) tuples.

    PRIMARY DISCRIMINATOR: kills impl returning [('alpha', 2), ('beta', 1)].
    """
    problems = [_p("alpha", 0), _p("alpha", 1), _p("beta", 0)]
    result = top_n_problem_classes(problems, 2)
    assert isinstance(result[0], str), "Must return str; got " + repr(type(result[0]))
    assert result[0] == "alpha", "alpha has highest count; got " + repr(result[0])


def test_descending_order_by_count() -> None:
    """Classes ordered by count descending.

    Kills impl returning ascending count order.
    3 classes: alpha=3, beta=2, gamma=1 -> [alpha, beta, gamma].
    """
    problems = (
        [_p("alpha", i) for i in range(3)]
        + [_p("beta", i) for i in range(2)]
        + [_p("gamma", 0)]
    )
    result = top_n_problem_classes(problems, 3)
    assert result == ["alpha", "beta", "gamma"], (
        "Descending count; got " + repr(result)
    )


def test_tie_break_ascending_class_name() -> None:
    """Ties broken by ascending class name.

    Kills impl with arbitrary or descending tie-break.
    alpha=2, beta=2 -> [alpha, beta] (ascending).
    """
    problems = [_p("beta", 0), _p("beta", 1), _p("alpha", 0), _p("alpha", 1)]
    result = top_n_problem_classes(problems, 2)
    assert result == ["alpha", "beta"], "Tie -> ascending name; got " + repr(result)


def test_n_zero_returns_empty() -> None:
    """n=0 returns [] without error.

    Kills impl returning all classes for n=0.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    assert top_n_problem_classes(problems, 0) == []


def test_n_exceeds_classes_returns_all() -> None:
    """n > num classes returns all classes (no crash, no padding).

    Kills impl crashing on large n or padding result with None.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = top_n_problem_classes(problems, 10)
    assert set(result) == {"alpha", "beta"}, (
        "All classes returned; got " + repr(result)
    )
    assert len(result) == 2, "No padding; got " + repr(len(result))
