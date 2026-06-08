"""Item 281: top_severity_pairs() — top-N (class, severity) pairs by count (2026-06-08).

``top_severity_pairs(problems: list[Problem], n: int = 5) -> list[tuple[str, str, int]]``:
Returns the top-n (class_name, severity, count) tuples sorted by count descending,
ties broken by (class_name ascending, severity ascending). Labelled problems only.
Empty input or n=0 -> []. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: sorted by count DESCENDING, not count ascending.
     The pair with the highest count must appear first.
     Kills impl using ascending sort.
  2. Tie-break: (class_asc, severity_asc). When two pairs have the same count,
     the one with the smaller class name first.
     Kills impl with wrong tie-break direction.
  3. n limits the result length; n=0 returns [].
     Kills impl ignoring the limit parameter.
  4. Unlabelled problems (severity='') excluded.
     Kills impl including blank-severity entries.
  5. Return type is list of 3-tuples (str, str, int).
     Kills impl returning dicts or 2-tuples.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_severity_pairs,
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


def test_sorted_by_count_descending() -> None:
    """Top pair is the (class, severity) with the highest count.

    PRIMARY DISCRIMINATOR: kills impl sorting ascending.
    (alpha, HIGH) count=5 must be first; (beta, LOW) count=2 must be second.
    """
    problems = (
        [_ps("alpha", i, "HIGH") for i in range(5)]
        + [_ps("beta", i, "LOW") for i in range(2)]
    )
    result = top_severity_pairs(problems, n=5)
    assert result[0] == ("alpha", "HIGH", 5), (
        "Highest count must be first; got " + repr(result[0])
    )
    assert result[1] == ("beta", "LOW", 2), (
        "Second highest must be second; got " + repr(result[1])
    )


def test_tie_break_class_then_severity_ascending() -> None:
    """Tied counts: break by class ascending then severity ascending.

    Kills impl with wrong tie-break direction.
    (gamma, HIGH) count=2, (alpha, HIGH) count=2 -> alpha comes first.
    """
    problems = [
        _ps("gamma", 0, "HIGH"),
        _ps("gamma", 1, "HIGH"),
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
    ]
    result = top_severity_pairs(problems, n=5)
    assert result[0][0] == "alpha", (
        "alpha < gamma alphabetically -> alpha first on tie; got " + repr(result[0])
    )
    assert result[1][0] == "gamma", "gamma second; got " + repr(result[1])


def test_n_limits_result_and_zero_returns_empty() -> None:
    """n limits the result to at most n entries; n=0 -> [].

    Kills impl ignoring the n parameter.
    """
    problems = [
        _ps("alpha", i, "HIGH") for i in range(5)
    ] + [_ps("beta", i, "LOW") for i in range(3)]
    result_1 = top_severity_pairs(problems, n=1)
    assert len(result_1) == 1, "n=1 -> at most 1 pair; got " + str(len(result_1))
    result_0 = top_severity_pairs(problems, n=0)
    assert result_0 == [], "n=0 -> []; got " + repr(result_0)


def test_unlabelled_excluded() -> None:
    """Unlabelled problems (severity='') must not appear in results.

    Kills impl including blank-severity entries.
    """
    problems = (
        [_p("alpha", i) for i in range(10)]   # all unlabelled
        + [_ps("beta", 0, "LOW")]              # 1 labelled
    )
    result = top_severity_pairs(problems, n=5)
    assert len(result) == 1, "Only 1 labelled pair; got " + str(len(result))
    assert result[0] == ("beta", "LOW", 1), "Only labelled pair; got " + repr(result[0])


def test_return_type_is_list_of_3tuples() -> None:
    """Return type is list[tuple[str, str, int]].

    Kills impl returning dicts or 2-tuples.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = top_severity_pairs(problems, n=5)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(
        isinstance(t, tuple) and len(t) == 3
        and isinstance(t[0], str) and isinstance(t[1], str) and isinstance(t[2], int)
        for t in result
    ), "Elements must be (str, str, int) tuples; got " + repr(result)
