"""Item 160: problem_count_by_class — TDD red→green (2026-06-08).

``problem_count_by_class(problems)`` → ``dict[str, int]``:
TIDE telemetry companion for ``discover_problems()``.  Given a
``list[Problem]``, counts findings by ``problem_class`` and returns
``{class: count}``.  A class absent from the input is absent from the
dict (not present with zero).  Pure fold; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. Two problems same class + one of another → ``{"class_a": 2, "class_b": 1}``.
     PRIMARY DISC.: kills impl that caps each class at 1 (set instead of counter).
  2. Empty list → ``{}``.
     Kills impl that errors on empty input or returns default-class counts.
  3. Classes absent from input are absent from dict (not zero-filled).
     Kills impl that pre-populates from ``default_template_classes()`` with zeros.
  4. Single-problem input → ``{class: 1}`` (boundary; also guards type safety).
     Kills impl that requires ≥2 problems to work correctly.
  5. All problems same class → single key with count == len(problems).
     Kills impl that fails to aggregate when only one class is present.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, problem_count_by_class


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, suffix: str = "x") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{suffix}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_two_classes_counted_correctly() -> None:
    """Two problems of class_a + one of class_b → {"class_a": 2, "class_b": 1}.

    PRIMARY DISCRIMINATOR: kills an impl that uses a set (each class capped at 1)
    instead of a counter, or that returns count=1 for every class regardless of
    how many findings share the same class.
    """
    problems = [_p("class_a", "1"), _p("class_a", "2"), _p("class_b", "1")]
    result = problem_count_by_class(problems)
    assert result.get("class_a") == 2, f"class_a must have count 2; got {result}"
    assert result.get("class_b") == 1, f"class_b must have count 1; got {result}"
    assert len(result) == 2, f"exactly 2 keys expected; got {result}"


def test_empty_list_returns_empty_dict() -> None:
    """Empty input → empty dict (no error, no default-class entries).

    Kills an impl that raises on empty input, or that pre-fills from
    default_template_classes() returning non-empty for an empty input.
    """
    result = problem_count_by_class([])
    assert result == {}, f"empty input must → empty dict; got {result!r}"


def test_absent_class_not_in_dict() -> None:
    """Only the classes present in the input appear in the output.

    Kills an impl that initialises from default_template_classes() (would include
    e.g. 'long_function' even though no long_function problem was in the input).
    """
    problems = [_p("complexity_outlier", "foo")]
    result = problem_count_by_class(problems)
    assert "complexity_outlier" in result, f"input class must be present; got {result}"
    # A class that's in default_template_classes() but NOT in the input must be absent.
    assert "long_function" not in result, (
        f"'long_function' absent from input must be absent from result; got {result}"
    )


def test_single_problem_returns_count_one() -> None:
    """Single problem → {class: 1} — boundary / type-safety guard.

    Kills an impl that requires at least 2 problems to initialise correctly,
    or that returns a non-int (e.g. a boolean True for singleton counts).
    """
    result = problem_count_by_class([_p("nesting_outlier")])
    assert result == {"nesting_outlier": 1}, f"single problem must → count 1; got {result!r}"
    assert isinstance(result["nesting_outlier"], int), "count must be int, not bool or float"


def test_all_same_class_aggregates_to_total() -> None:
    """N problems all in the same class → single key with count == N.

    Kills an impl that uses deduplication logic (e.g. frozenset) on problem ids
    instead of a plain count, which would cap the output at 1 per unique id.
    (Each problem created here has a distinct finding_id — so dedup would return N.)
    The discriminating case: creates 5 distinct problems of the same class.
    """
    n = 5
    problems = [_p("production_assert", str(i)) for i in range(n)]
    result = problem_count_by_class(problems)
    assert result == {"production_assert": n}, (
        f"all-same-class must aggregate to {n}; got {result!r}"
    )
