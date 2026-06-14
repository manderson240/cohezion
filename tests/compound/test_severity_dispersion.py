"""Item 259: severity_dispersion() — count of distinct severity labels (2026-06-08).

``severity_dispersion(problems: list[Problem]) -> int``:
Returns the count of distinct non-empty severity strings present across all
problems.  Unlabelled problems (``severity=""``) are excluded from the count.
Empty input or all-unlabelled → ``0``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: excludes unlabelled ("") from the count.
     Kills impl that counts ALL distinct severity strings including "".
  2. Returns 0 when all problems are unlabelled.
     Kills impl that returns 1 (counting "" as a severity).
  3. Returns 0 when input is empty.
     Kills impl that raises on empty input.
  4. Counts distinct labels, not total problems.
     Kills impl that returns len(problems) or the total labelled count.
  5. Return type is int.
     Kills impl returning a frozenset or a dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_dispersion,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_excludes_unlabelled_from_count() -> None:
    """Unlabelled problems (severity='') are excluded from the dispersion count.

    PRIMARY DISCRIMINATOR: kills impl that counts '' as a distinct severity.
    2 labelled severities (HIGH + LOW) + unlabelled problems → dispersion = 2.
    If '' were counted: dispersion would be 3.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 0, "LOW"),
        Problem(problem_class="gamma", finding_id="gamma:0"),  # severity=""
    ]
    result = severity_dispersion(problems)
    assert result == 2, "HIGH + LOW = 2 distinct severities; '' excluded; got " + repr(result)


def test_zero_when_all_unlabelled() -> None:
    """Returns 0 when all problems have severity=''.

    Kills impl that returns 1 (treating '' as a severity label).
    """
    problems = [
        Problem(problem_class="alpha", finding_id="alpha:0"),
        Problem(problem_class="beta", finding_id="beta:0"),
    ]
    result = severity_dispersion(problems)
    assert result == 0, "All unlabelled → 0; got " + repr(result)


def test_zero_when_empty_input() -> None:
    """Returns 0 when problems list is empty.

    Kills impl that raises on empty input.
    """
    result = severity_dispersion([])
    assert result == 0, "Empty input → 0; got " + repr(result)


def test_counts_distinct_labels_not_problems() -> None:
    """Returns the count of distinct labels, not total labelled problems.

    Kills impl that returns len(labelled_problems) or sum(counts.values()).
    5 HIGH problems + 3 LOW problems = 2 distinct labels (not 8).
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)] + [
        _ps("beta", i, "LOW") for i in range(3)
    ]
    result = severity_dispersion(problems)
    assert result == 2, "HIGH + LOW = 2 distinct labels; got " + repr(result)


def test_return_type_is_int() -> None:
    """Return type is int.

    Kills impl returning frozenset or dict.
    """
    result = severity_dispersion([_ps("alpha", 0, "CRITICAL")])
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1
