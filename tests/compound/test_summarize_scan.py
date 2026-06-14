"""Item 224: summarize_scan() — single-call scan summary dict (2026-06-08).

``summarize_scan(problems: list[Problem], thresholds: dict[str, int]) -> dict``
Composes the TIDE function set into a one-call summary.  Returns a ``dict``
with exactly 7 keys, all values derived from existing pure TIDE functions:

  ``total``              -- len(problems)
  ``violations_count``   -- len(threshold_violations(problems, thresholds))
  ``worst_violation``    -- worst_violation(problems, thresholds)  (tuple or None)
  ``most_critical_class``-- most_critical_class(problems, thresholds)  (str or None)
  ``violation_summary``  -- violation_summary(problems, thresholds)  (int)
  ``classes_over``       -- frozenset of over-threshold monitored classes
  ``classes_under``      -- frozenset of at-or-under monitored classes

Pure; no I/O.  Zero reimplementation: every value is obtained by calling an
existing TIDE function.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: dict has exactly the 7 required keys (no missing, no extra).
     Kills an impl that omits keys or adds undocumented keys.
  2. violations_count == len(threshold_violations(...)).
     Kills an impl that counts something other than violations.
  3. worst_violation is a tuple or None (not a str or int).
     Kills an impl that returns just the class name.
  4. Partition invariant: classes_over | classes_under == frozenset(thresholds.keys()).
     Kills an impl where the two sets overlap or are incomplete.
  5. violation_summary == sum of excesses (delegates correctly to violation_summary()).
     Kills an impl that reimplements using raw count instead of excess.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    summarize_scan,
    threshold_violations,
)


REQUIRED_KEYS = frozenset(
    {
        "total",
        "violations_count",
        "worst_violation",
        "most_critical_class",
        "violation_summary",
        "classes_over",
        "classes_under",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_required_keys_present() -> None:
    """summarize_scan returns a dict with exactly the 7 required keys.

    PRIMARY DISCRIMINATOR: kills an impl with missing or renamed keys.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta")]
    thresholds = {"alpha": 2, "beta": 5}

    result = summarize_scan(problems, thresholds)

    missing = REQUIRED_KEYS - set(result.keys())
    extra = set(result.keys()) - REQUIRED_KEYS
    assert not missing, "Missing keys: " + repr(missing)
    assert not extra, "Extra unexpected keys: " + repr(extra)


def test_violations_count_matches_threshold_violations() -> None:
    """violations_count == len(threshold_violations(problems, thresholds)).

    Kills an impl that counts total problems or violating problems differently.
    """
    problems = [_p("alpha", i) for i in range(4)] + [_p("beta")]
    thresholds = {"alpha": 2, "beta": 5}

    result = summarize_scan(problems, thresholds)
    expected = len(threshold_violations(problems, thresholds))

    assert result["violations_count"] == expected, (
        "violations_count must equal len(threshold_violations); got "
        + repr(result["violations_count"])
    )


def test_worst_violation_is_tuple_or_none() -> None:
    """worst_violation is a (str, int) tuple or None, not a plain str.

    Kills an impl that returns just the class name string.
    """
    problems = [_p("alpha", i) for i in range(5)]
    thresholds = {"alpha": 2}

    result = summarize_scan(problems, thresholds)

    wv = result["worst_violation"]
    assert wv is not None, "worst_violation must not be None when violations exist"
    assert isinstance(wv, tuple) and len(wv) == 2, (
        "worst_violation must be a (class, excess) tuple; got " + repr(wv)
    )
    assert isinstance(wv[0], str) and isinstance(wv[1], int), (
        "worst_violation must be (str, int); got " + repr(wv)
    )


def test_partition_invariant_holds() -> None:
    """classes_over | classes_under == frozenset(thresholds.keys()).

    Kills an impl where the two sets overlap or are incomplete.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta")]
    thresholds = {"alpha": 2, "beta": 5, "gamma": 1}  # gamma has 0 findings

    result = summarize_scan(problems, thresholds)

    over = result["classes_over"]
    under = result["classes_under"]
    assert over | under == frozenset(thresholds.keys()), (
        "Partition must cover all monitored classes; got over="
        + repr(over)
        + " under="
        + repr(under)
    )
    assert over & under == frozenset(), "Partition must be disjoint; intersection=" + repr(
        over & under
    )


def test_violation_summary_is_sum_of_excesses() -> None:
    """violation_summary is the sum of per-class excesses (not raw counts).

    Kills an impl that sums raw counts instead of excesses.
    alpha: 5 findings, threshold=2 -> excess=3.
    beta: 3 findings, threshold=1 -> excess=2.
    violation_summary must be 5 (not 8 = raw counts).
    """
    problems = [_p("alpha", i) for i in range(5)] + [_p("beta", i) for i in range(3)]
    thresholds = {"alpha": 2, "beta": 1}

    result = summarize_scan(problems, thresholds)

    assert result["violation_summary"] == 5, (
        "violation_summary must be sum of excesses (3+2=5); got "
        + repr(result["violation_summary"])
    )
