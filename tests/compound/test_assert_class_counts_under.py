"""Item 181: assert_class_counts_under() — CI ratchet guard (2026-06-08).

``assert_class_counts_under(problems: list[Problem], thresholds: dict[str, int])``
→ ``None``:
Raises ``AssertionError`` listing all violations for every class whose
finding count exceeds its threshold.  Empty *thresholds* → no-op.  Classes
not in *thresholds* are ignored.  Pure; no I/O.

Enables ratcheting: once a class is driven below a threshold, the guard
locks the improvement in:
    assert_class_counts_under(findings, {"complexity_outlier": 5})

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: one class over its threshold → AssertionError naming the class.
     Kills a no-op impl that always passes silently.
  2. Multiple violations → ALL listed in one message.
     Kills an impl that reports only the first violation.
  3. All classes under their thresholds → no-op.
     Kills an impl that always raises.
  4. Empty *thresholds* → no-op.
     Kills an impl that raises on empty thresholds (e.g. misreads as "check all").
  5. Class not in *thresholds* ignored even if very high count.
     Kills an impl that checks every class regardless of whether it has a threshold.
"""

from __future__ import annotations

import pytest

from cohezion.compound.problem_discovery import (
    Problem,
    assert_class_counts_under,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_over_threshold_raises() -> None:
    """One class exceeds its threshold → AssertionError naming the class.

    PRIMARY DISCRIMINATOR: kills a no-op impl that always passes silently.
    'complexity_outlier' has 3 findings but threshold is 2.
    """
    problems = [_p("complexity_outlier", i) for i in range(3)]

    with pytest.raises(AssertionError) as exc_info:
        assert_class_counts_under(problems, {"complexity_outlier": 2})

    msg = str(exc_info.value)
    assert "complexity_outlier" in msg, f"AssertionError must name the violating class; got {msg!r}"


def test_multiple_violations_all_listed() -> None:
    """Two classes both over their thresholds → AssertionError listing BOTH.

    Kills an impl that raises immediately on the first violation (fail-fast),
    leaving the second violation unreported until the first is fixed.
    """
    problems = [_p("complexity_outlier", i) for i in range(4)] + [
        _p("nesting_outlier", i) for i in range(3)
    ]

    with pytest.raises(AssertionError) as exc_info:
        assert_class_counts_under(problems, {"complexity_outlier": 2, "nesting_outlier": 1})

    msg = str(exc_info.value)
    assert "complexity_outlier" in msg, f"'complexity_outlier' must be in error; got {msg!r}"
    assert "nesting_outlier" in msg, f"'nesting_outlier' must be in error; got {msg!r}"


def test_all_under_threshold_no_raises() -> None:
    """All monitored classes are at or below their thresholds → no raises.

    Kills an impl that always raises regardless of whether counts are over.
    """
    problems = [_p("complexity_outlier", i) for i in range(3)]

    # threshold = 5 > 3 actual; must pass silently
    assert_class_counts_under(problems, {"complexity_outlier": 5})


def test_empty_thresholds_no_raises() -> None:
    """Empty *thresholds* dict → no-op (no raises, nothing to check).

    Kills an impl that raises on empty input or interprets empty thresholds
    as "flag everything".
    """
    problems = [_p("complexity_outlier", i) for i in range(10)]

    assert_class_counts_under(problems, {})


def test_unmonitored_class_ignored() -> None:
    """Class not in *thresholds* is ignored even if count is very high.

    Kills an impl that checks every class regardless of whether it appears
    in *thresholds* (e.g. uses a global max check instead of per-key lookup).
    """
    # 'nesting_outlier' has 100 findings but is NOT in thresholds
    problems = [_p("nesting_outlier", i) for i in range(100)]

    # Only 'complexity_outlier' is in thresholds, but it has 0 findings
    assert_class_counts_under(problems, {"complexity_outlier": 5})
