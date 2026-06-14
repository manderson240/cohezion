"""Item 360: class_name_contains() -- substring filter on problem_class (2026-06-08).

class_name_contains(problems, substring) -> list[Problem]:
Returns all Problem objects whose problem_class contains the given substring
anywhere (not just at the start).  Empty substring matches ALL.
Case-sensitive.  Preserves order.  Empty problems -> [].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: uses substring containment, not startswith.
     Match in the MIDDLE of a class name qualifies.
     Kills impl using startswith or endswith only.
  2. Empty substring matches ALL problems.
     Kills impl returning [] for empty substring.
  3. Case-sensitive matching.
     Kills impl doing case-insensitive match.
  4. Substring at the END of class name matches.
     Kills impl only matching at the start.
  5. Empty problems returns [].
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_name_contains,
)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_middle_substring_matches() -> None:
    problems = [_p("security_auth_check", 0), _p("perf_query", 0)]
    result = class_name_contains(problems, "auth")
    assert len(result) == 1 and result[0].problem_class == "security_auth_check", (
        f"Middle match; got {result}"
    )


def test_empty_substring_matches_all() -> None:
    problems = [_p("a", 0), _p("b", 0), _p("c", 0)]
    result = class_name_contains(problems, "")
    assert len(result) == 3


def test_case_sensitive() -> None:
    problems = [_p("Security", 0), _p("security", 0)]
    result = class_name_contains(problems, "sec")
    assert len(result) == 1 and result[0].problem_class == "security"


def test_end_substring_matches() -> None:
    problems = [_p("query_timeout", 0), _p("connection_timeout", 0), _p("query_slow", 0)]
    result = class_name_contains(problems, "timeout")
    assert len(result) == 2
    assert all("timeout" in p.problem_class for p in result)


def test_empty_problems_returns_empty() -> None:
    assert class_name_contains([], "auth") == []
