"""Item 88: experiential-loop closure instrument (report-only, TDD red→green).

`experiential_closure_report(outcomes, neurons)` classifies ACCEPTED outcomes as
CLOSED (matching neuron found) or OPEN GAP (no matching neuron).  REJECTED outcomes
must appear in NEITHER list — the AUTODQA I6 spirit (no back-door deposits).

Each test fails a plausible wrong implementation:
  - one that counts ALL outcomes, ignoring rejected  → test_rejected_excluded_from_both
  - one that ignores the tag-match and always marks closed → test_accepted_no_neuron_is_gap
  - one that requires country-specific tags → test_tag_match_country_agnostic
  - one that returns unsorted or duplicates     → test_sorted_and_deduped
  - one that crashes or invents results on empty → test_empty_inputs
"""

from __future__ import annotations

from cohezion.governance.experiential_closure import (
    ClosureReport,
    Outcome,
    experiential_closure_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RERANK_NEURON = {
    "country": "cerebellum",
    "name": "n-rerank-1",
    "tags": ["cerebellum", "procedural", "RERANK", "igpu"],
}

_SKILL_NEURON = {
    "country": "skill",
    "name": "n-skill-1",
    "tags": ["skill", "my-skill"],
}


# ---------------------------------------------------------------------------
# T_closed: accepted + matching neuron → closed
# ---------------------------------------------------------------------------


def test_accepted_with_neuron_is_closed() -> None:
    """An accepted outcome whose key is in a neuron's tags → in closed, NOT open_gaps."""
    outcomes = [Outcome(key="RERANK", accepted=True)]
    result = experiential_closure_report(outcomes, [_RERANK_NEURON])
    assert "RERANK" in result.closed, "RERANK matched; must be closed"
    assert "RERANK" not in result.open_gaps


# ---------------------------------------------------------------------------
# T_gap: accepted + NO matching neuron → open_gaps
# Fails: an impl that always marks accepted as closed.
# ---------------------------------------------------------------------------


def test_accepted_no_neuron_is_gap() -> None:
    """An accepted outcome with no matching neuron → open_gaps, NOT closed."""
    outcomes = [Outcome(key="FIM", accepted=True)]
    result = experiential_closure_report(outcomes, [_RERANK_NEURON])
    assert "FIM" in result.open_gaps, "FIM has no neuron; must be an open gap"
    assert "FIM" not in result.closed


# ---------------------------------------------------------------------------
# T_rejected: REJECTED outcome → excluded from BOTH lists
# Fails: an impl that counts all outcomes regardless of accepted flag.
# ---------------------------------------------------------------------------


def test_rejected_excluded_from_both() -> None:
    """A rejected outcome must appear in neither closed nor open_gaps.

    A wrong impl that ignores the `accepted` flag would put the rejected outcome
    into open_gaps (no matching neuron) or closed (if a neuron exists).
    """
    outcomes = [
        Outcome(key="CODE", accepted=False),  # rejected — must be excluded
        Outcome(key="RERANK", accepted=True),  # accepted + neuron → closed
    ]
    result = experiential_closure_report(outcomes, [_RERANK_NEURON])
    assert "CODE" not in result.closed, "rejected KEY must not be in closed"
    assert "CODE" not in result.open_gaps, "rejected KEY must not be in open_gaps"
    assert "RERANK" in result.closed, "accepted+neuron must still be closed"


# ---------------------------------------------------------------------------
# T_agnostic: tag match is country-agnostic
# Fails: an impl that only checks a specific country (e.g. only 'inference').
# ---------------------------------------------------------------------------


def test_tag_match_country_agnostic() -> None:
    """Tag match must succeed regardless of the neuron's country field."""
    skill_outcome = Outcome(key="my-skill", accepted=True)
    # Only a skill-country neuron has this tag; not an inference/cerebellum one
    result = experiential_closure_report([skill_outcome], [_SKILL_NEURON])
    assert "my-skill" in result.closed, "skill tag found in skill-country neuron; must close"


# ---------------------------------------------------------------------------
# T_sorted: results are returned in sorted order
# Fails: an impl that returns insertion order.
# ---------------------------------------------------------------------------


def test_sorted_output() -> None:
    """Both closed and open_gaps lists are sorted for determinism."""
    outcomes = [
        Outcome(key="Z", accepted=True),
        Outcome(key="A", accepted=True),
    ]
    neurons = [{"tags": ["Z"]}]  # Z is closed; A is a gap
    result = experiential_closure_report(outcomes, neurons)
    assert result.closed == sorted(result.closed)
    assert result.open_gaps == sorted(result.open_gaps)


# ---------------------------------------------------------------------------
# T_dedup: a key appearing in multiple accepted outcomes is listed once
# ---------------------------------------------------------------------------


def test_deduplication_of_repeated_key() -> None:
    """A key submitted twice in outcomes appears at most once in each list."""
    outcomes = [Outcome(key="RERANK", accepted=True), Outcome(key="RERANK", accepted=True)]
    result = experiential_closure_report(outcomes, [_RERANK_NEURON])
    assert result.closed.count("RERANK") == 1, "duplicate key must be deduplicated"


# ---------------------------------------------------------------------------
# T_empty: empty inputs → empty report, no crash
# Fails: an impl that throws on empty iterables.
# ---------------------------------------------------------------------------


def test_empty_outcomes_returns_empty() -> None:
    result = experiential_closure_report([], [_RERANK_NEURON])
    assert isinstance(result, ClosureReport)
    assert result.closed == []
    assert result.open_gaps == []


def test_empty_neurons_all_open_gaps() -> None:
    """No neurons → every accepted outcome is an open gap."""
    outcomes = [Outcome(key="RERANK", accepted=True), Outcome(key="FIM", accepted=True)]
    result = experiential_closure_report(outcomes, [])
    assert result.closed == []
    assert set(result.open_gaps) == {"RERANK", "FIM"}


def test_both_empty_returns_empty() -> None:
    result = experiential_closure_report([], [])
    assert result.closed == [] and result.open_gaps == []
