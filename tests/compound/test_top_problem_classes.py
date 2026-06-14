"""Item 161: top_problem_classes — TDD red→green (2026-06-08).

``top_problem_classes(problems, *, n=5)`` → ``list[tuple[str, int]]``:
Extends item 160's ``problem_count_by_class`` with a ranked view.  Returns
the ``n`` highest-count ``(problem_class, count)`` pairs sorted descending
by count; ties broken alphabetically by class name for determinism.

Discriminating tests — each kills a plausible wrong implementation:

  1. 3 classes with counts 3/2/1, n=2 → top-2 in descending order.
     PRIMARY DISC.: kills impl that returns unsorted, returns all, or truncates wrong.
  2. Empty input → ``[]``.
     Kills impl that errors on empty input or returns default entries.
  3. n ≥ total class count → all classes returned (no truncation / no error).
     Kills impl that raises IndexError when n exceeds available classes.
  4. Tie in count → alphabetical order of class name (deterministic).
     Kills impl that uses arbitrary dict-insertion or sort-unstable tie-breaking.
  5. n=1 → only the single top class returned.
     Kills impl that always returns ≥2 entries or ignores n entirely.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, top_problem_classes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, suffix: str = "x") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{suffix}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_top_n_sorted_descending() -> None:
    """3-class input with counts 3/2/1, n=2 → [('class_a', 3), ('class_b', 2)].

    PRIMARY DISCRIMINATOR: kills an impl that:
      - returns all 3 classes (ignores n)
      - returns in wrong order (ascending or insertion order)
      - returns wrong counts
    """
    problems = (
        [_p("class_a", str(i)) for i in range(3)]  # count 3
        + [_p("class_b", str(i)) for i in range(2)]  # count 2
        + [_p("class_c", "0")]  # count 1
    )
    result = top_problem_classes(problems, n=2)
    assert result == [("class_a", 3), ("class_b", 2)], (
        f"top-2 must be [('class_a',3), ('class_b',2)]; got {result}"
    )


def test_empty_input_returns_empty_list() -> None:
    """Empty input → [] (no error, no default entries).

    Kills an impl that raises on empty input or pre-fills with known class names.
    """
    result = top_problem_classes([], n=5)
    assert result == [], f"empty input must → []; got {result!r}"


def test_n_exceeds_classes_returns_all() -> None:
    """n > number of distinct classes → all classes returned without error.

    Kills an impl that raises IndexError or slices past the end silently
    returning fewer items than available.
    """
    problems = [_p("only_class", "0")]
    result = top_problem_classes(problems, n=10)
    assert result == [("only_class", 1)], f"n > classes must return all available; got {result!r}"


def test_tie_broken_alphabetically() -> None:
    """Equal counts → alphabetical class name order (deterministic).

    Kills an impl that uses dict insertion order or arbitrary sort-stable
    coincidence (the input is shuffled to expose ordering assumptions).
    Both 'zebra_class' and 'alpha_class' have count 2 — 'alpha_class' must
    appear first.
    """
    problems = [
        _p("zebra_class", "1"),
        _p("alpha_class", "1"),
        _p("zebra_class", "2"),
        _p("alpha_class", "2"),
    ]
    result = top_problem_classes(problems, n=5)
    # Both have count 2; alphabetical → alpha_class first
    assert result[0] == ("alpha_class", 2), f"tie must be broken alphabetically; got {result}"
    assert result[1] == ("zebra_class", 2), f"second tie entry must be zebra_class; got {result}"


def test_n_one_returns_single_top() -> None:
    """n=1 → only the single highest-count class.

    Kills an impl that always returns ≥2 entries or ignores n.
    """
    problems = [_p("winner", "1"), _p("winner", "2"), _p("runner_up", "1")]
    result = top_problem_classes(problems, n=1)
    assert result == [("winner", 2)], f"n=1 must return only winner; got {result!r}"
