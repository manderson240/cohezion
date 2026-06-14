"""Item 252: severity_report() — one-call severity analytics summary (2026-06-08).

``severity_report(problems: list[Problem]) -> dict[str, object]``:
Returns a single dict with four keys that consolidate the full severity picture::

    {
        "counts":        dict[str, int],   # count_by_severity
        "dominant":      str | None,       # dominant_severity
        "fractions":     dict[str, float], # {sev: fraction for sev in counts}
        "labelled_total": int,             # sum of counts values
    }

Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: dominant is None when no labelled problems.
     Kills impl that always returns first count key instead of None.
  2. fractions sum to 1.0 when labelled_total > 0.
     Kills impl that uses len(problems) as denominator.
  3. labelled_total equals sum(counts.values()).
     Kills impl that returns len(problems) (includes unlabelled).
  4. Return type is dict with exactly four keys.
     Kills impl returning a tuple or using wrong key names.
  5. Empty input → counts={}, dominant=None, fractions={}, labelled_total=0.
     Kills impl that raises on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dominant_none_when_no_labelled_problems() -> None:
    """dominant is None when no problem has a non-empty severity.

    PRIMARY DISCRIMINATOR: kills impl that always assigns dominant to the
    first count key, which would blow up or return something non-None when
    there are actually zero labelled problems.
    """
    problems = [
        Problem(problem_class="alpha", finding_id="alpha:0"),
        Problem(problem_class="beta", finding_id="beta:0"),
    ]
    result = severity_report(problems)
    assert result["dominant"] is None, "No labelled problems → dominant must be None; got " + repr(
        result["dominant"]
    )


def test_fractions_sum_to_one_when_labelled_exist() -> None:
    """fractions sum to 1.0 when there are labelled problems.

    Kills impl that divides by len(problems) instead of total_labelled
    (would make fractions sum to < 1 when unlabelled problems exist).
    3 HIGH, 1 LOW, 2 unlabelled.  labelled=4.  3/4+1/4=1.0.
    """
    problems = [
        _ps("a", 0, "HIGH"),
        _ps("a", 1, "HIGH"),
        _ps("a", 2, "HIGH"),
        _ps("b", 0, "LOW"),
        Problem(problem_class="c", finding_id="c:0"),  # unlabelled
        Problem(problem_class="c", finding_id="c:1"),  # unlabelled
    ]
    result = severity_report(problems)
    total_fraction = sum(result["fractions"].values())
    assert abs(total_fraction - 1.0) < 1e-9, "fractions must sum to 1.0; got " + repr(
        total_fraction
    )


def test_labelled_total_excludes_unlabelled() -> None:
    """labelled_total equals sum(counts.values()), not len(problems).

    Kills impl that uses len(problems) as labelled_total.
    2 labelled + 3 unlabelled = len=5; labelled_total must be 2.
    """
    problems = [
        _ps("a", 0, "CRITICAL"),
        _ps("a", 1, "CRITICAL"),
        Problem(problem_class="b", finding_id="b:0"),
        Problem(problem_class="b", finding_id="b:1"),
        Problem(problem_class="b", finding_id="b:2"),
    ]
    result = severity_report(problems)
    assert result["labelled_total"] == 2, (
        "labelled_total must be 2 (only labelled problems); got " + repr(result["labelled_total"])
    )


def test_return_type_is_dict_with_four_keys() -> None:
    """Return is a dict with exactly four keys.

    Kills impl returning a tuple or using different key names.
    """
    result = severity_report([])
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert set(result.keys()) == {"counts", "dominant", "fractions", "labelled_total"}, (
        "Must have exactly four keys; got " + repr(set(result.keys()))
    )


def test_empty_input_returns_zero_state() -> None:
    """Empty input → counts={}, dominant=None, fractions={}, labelled_total=0.

    Kills impl that raises on empty input.
    """
    result = severity_report([])
    assert result["counts"] == {}, "Empty → counts={}; got " + repr(result["counts"])
    assert result["dominant"] is None, "Empty → dominant=None; got " + repr(result["dominant"])
    assert result["fractions"] == {}, "Empty → fractions={}; got " + repr(result["fractions"])
    assert result["labelled_total"] == 0, "Empty → labelled_total=0; got " + repr(
        result["labelled_total"]
    )
