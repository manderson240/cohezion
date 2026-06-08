"""Item 290: problem_count_by_severity_in_class() — severity breakdown for one class (2026-06-08).

``problem_count_by_severity_in_class(problems: list[Problem], cls: str) -> dict[str, int]``:
Returns {severity: count} for LABELLED problems in the given class only.
Unlabelled (severity="") problems excluded.  Absent class -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: unlabelled (severity="") problems in the class are excluded.
     Kills impl that includes unlabelled problems in the returned counts.
  2. Problems from other classes are excluded.
     Kills impl that counts across all classes.
  3. Absent class -> {} (no KeyError).
     Kills impl raising on absent class.
  4. Empty input -> {}.
     Kills impl raising on empty.
  5. Return type is dict[str, int] with int values.
     Kills impl returning Problem lists or floats.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_count_by_severity_in_class,
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


def test_unlabelled_problems_excluded() -> None:
    """Unlabelled (severity='') problems in the target class are excluded.

    PRIMARY DISCRIMINATOR: kills impl that counts all problems including unlabelled.
    alpha has 2 HIGH, 1 LOW, 1 unlabelled.
    Result must NOT include '' as a key, and total count must be 3, not 4.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _p("alpha", 3),  # unlabelled, severity=""
    ]
    result = problem_count_by_severity_in_class(problems, "alpha")
    assert "" not in result, (
        "Unlabelled (severity='') excluded from result; got keys: " + repr(list(result.keys()))
    )
    assert result.get("HIGH") == 2, "2 HIGH problems; got " + repr(result.get("HIGH"))
    assert result.get("LOW") == 1, "1 LOW problem; got " + repr(result.get("LOW"))


def test_other_class_problems_excluded() -> None:
    """Problems from other classes are not counted.

    Kills impl that counts across all classes.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),  # different class
        _ps("beta", 2, "HIGH"),  # different class
    ]
    result = problem_count_by_severity_in_class(problems, "alpha")
    assert result == {"HIGH": 1}, (
        "Only alpha's 1 HIGH problem counted; got " + repr(result)
    )


def test_absent_class_returns_empty_dict() -> None:
    """Absent class -> {}, not an exception.

    Kills impl raising KeyError or returning None.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = problem_count_by_severity_in_class(problems, "missing")
    assert result == {}, "Absent class -> {}; got " + repr(result)


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising.

    Kills impl raising on empty list.
    """
    result = problem_count_by_severity_in_class([], "alpha")
    assert result == {}, "Empty input -> {}; got " + repr(result)


def test_return_type_is_dict_of_int() -> None:
    """Return type is dict[str, int] with integer values.

    Kills impl returning Problem lists or float counts.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    result = problem_count_by_severity_in_class(problems, "alpha")
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for sev, count in result.items():
        assert isinstance(sev, str) and isinstance(count, int), (
            "Values must be int; got " + repr((sev, count, type(count)))
        )
    assert result == {"HIGH": 2}, "2 HIGH -> {'HIGH': 2}; got " + repr(result)
