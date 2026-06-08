"""Item 358: problems_with_class_prefix() -- filter by class name prefix (2026-06-08).

``problems_with_class_prefix(problems, prefix) -> list[Problem]``:
Returns all Problem objects whose problem_class.startswith(prefix).
Empty prefix matches all problems (Python semantics).
Case-sensitive.  Preserves insertion order.  Empty problems -> [].
Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: uses startswith not exact equality.
     Kills impl filtering by exact class name match.
  2. Empty prefix matches ALL problems.
     Kills impl returning [] for empty prefix.
  3. Non-matching prefix returns [].
     Kills impl returning all problems on unknown prefix.
  4. Case-sensitive (prefix 'security' does not match 'Security').
     Kills impl doing case-insensitive comparison.
  5. Original insertion order preserved.
     Kills impl that reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_with_class_prefix,
)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_uses_startswith_not_exact_match() -> None:
    """Returns problems whose class starts with prefix, not exact matches only.

    PRIMARY DISCRIMINATOR: kills exact-equality filter.
    prefix='sec' matches 'security/a' and 'security/b', not 'other'.
    """
    problems = [_p("security/a", 0), _p("security/b", 0), _p("other", 0)]
    result = problems_with_class_prefix(problems, "security/")
    assert len(result) == 2, "2 matches; got " + repr(len(result))
    assert all(p.problem_class.startswith("security/") for p in result)
    assert all(isinstance(p, Problem) for p in result)


def test_empty_prefix_matches_all_problems() -> None:
    """Empty prefix returns ALL problems.

    Kills impl returning [] for empty prefix.
    Python: 'anything'.startswith('') == True.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("gamma", 0)]
    result = problems_with_class_prefix(problems, "")
    assert len(result) == 3, "Empty prefix -> all; got " + repr(len(result))


def test_non_matching_prefix_returns_empty() -> None:
    """No matches returns []."""
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = problems_with_class_prefix(problems, "zzz")
    assert result == [], "No match -> []; got " + repr(result)


def test_case_sensitive() -> None:
    """Prefix matching is case-sensitive.

    Kills impl doing case-insensitive comparison.
    'sec' does not match 'Security'.
    """
    problems = [_p("Security/a", 0), _p("security/b", 0)]
    result = problems_with_class_prefix(problems, "security/")
    assert len(result) == 1, "Only lowercase match; got " + repr(result)
    assert result[0].problem_class == "security/b"


def test_original_order_preserved() -> None:
    """Returned problems preserve original insertion order."""
    problems = [_p("sec/c", 0), _p("other", 0), _p("sec/a", 0), _p("sec/b", 0)]
    result = problems_with_class_prefix(problems, "sec/")
    assert [p.problem_class for p in result] == ["sec/c", "sec/a", "sec/b"], (
        "Order preserved; got " + repr([p.problem_class for p in result])
    )
