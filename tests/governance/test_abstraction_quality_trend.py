"""Item 154: abstraction_quality_trend — TDD red→green (2026-06-08).

``abstraction_quality_trend(deltas)`` → ``{"net_improved": int, "net_degraded": int,
"trend": "improving" | "degrading" | "stable"}``:
extends item-152 ``abstraction_quality_delta``'s single-pair snapshot into a
multi-tick time-series; the loop's self-assessment of whether neuron quality
evolution is net-positive over N ticks.

Input: a ``list[dict]`` — each dict is the output of ``abstraction_quality_delta``
(keys ``"improved"`` and ``"degraded"``, each a ``list[AbstractionFlag]``).

Discriminating tests — each kills a plausible wrong implementation:

  1. Single tick with 1 improved, 0 degraded → net_improved=1, trend="improving"
     PRIMARY DISC.: kills impl that ignores ticks / always returns zeros.
  2. Multi-tick with more degraded overall → trend="degrading"
     Kills impl that only counts ticks, not per-flag counts.
  3. Equal improved and degraded totals → trend="stable"
     Kills impl that defaults to "improving" on a tie.
  4. Empty list → all-zeros + trend="stable"
     Kills impl that errors on empty input.
  5. Same neuron improves in tick 1 and degrades in tick 2 → both count
     (net_improved=1, net_degraded=1, trend="stable").
     Kills impl that deduplicates by neuron name across ticks.
"""

from __future__ import annotations

from cohezion.governance.abstraction_quality import AbstractionFlag, abstraction_quality_trend


def _flag(name: str, *, volatile: bool) -> AbstractionFlag:
    return AbstractionFlag(
        name=name,
        instance_specific=volatile,
        reasons=["test-pattern"] if volatile else [],
    )


def _delta(
    improved: list[AbstractionFlag],
    degraded: list[AbstractionFlag],
) -> dict:
    return {"improved": improved, "degraded": degraded}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_tick_one_improved_is_improving() -> None:
    """Single tick with 1 improved flag → net_improved=1, trend='improving'.

    PRIMARY DISCRIMINATOR: kills an impl that ignores individual flags (e.g.
    counts ticks instead of flags, or always returns zeros).
    """
    deltas = [_delta(improved=[_flag("n1", volatile=False)], degraded=[])]
    result = abstraction_quality_trend(deltas)
    assert result["net_improved"] == 1, f"expected 1; got {result}"
    assert result["net_degraded"] == 0, f"expected 0; got {result}"
    assert result["trend"] == "improving", f"expected 'improving'; got {result['trend']!r}"


def test_multi_tick_more_degraded_is_degrading() -> None:
    """Multiple ticks with 3 degraded total across ticks → trend='degrading'.

    Kills an impl that counts only ticks (not per-flag), which would see
    2 'degrading' ticks vs 1 'improving' tick and might compute wrong totals.
    """
    deltas = [
        _delta(improved=[_flag("a", volatile=False)], degraded=[]),
        _delta(
            improved=[],
            degraded=[_flag("b", volatile=True), _flag("c", volatile=True)],
        ),
        _delta(
            improved=[],
            degraded=[_flag("d", volatile=True)],
        ),
    ]
    result = abstraction_quality_trend(deltas)
    assert result["net_improved"] == 1, f"net_improved should be 1; got {result}"
    assert result["net_degraded"] == 3, f"net_degraded should be 3; got {result}"
    assert result["trend"] == "degrading", f"expected 'degrading'; got {result['trend']!r}"


def test_equal_improved_and_degraded_is_stable() -> None:
    """Equal net_improved and net_degraded → trend='stable'.

    Kills an impl that defaults to 'improving' when counts tie, or that
    uses > instead of >= for the equality check.
    """
    deltas = [
        _delta(improved=[_flag("x", volatile=False)], degraded=[]),
        _delta(improved=[], degraded=[_flag("y", volatile=True)]),
    ]
    result = abstraction_quality_trend(deltas)
    assert result["net_improved"] == 1
    assert result["net_degraded"] == 1
    assert result["trend"] == "stable", f"equal counts must → 'stable'; got {result['trend']!r}"


def test_empty_list_returns_stable_zeros() -> None:
    """Empty delta list → all-zero counts + trend='stable' (no error).

    Kills an impl that raises on empty input or returns None.
    """
    result = abstraction_quality_trend([])
    assert result["net_improved"] == 0, f"expected 0; got {result}"
    assert result["net_degraded"] == 0, f"expected 0; got {result}"
    assert result["trend"] == "stable", f"empty input must → 'stable'; got {result['trend']!r}"


def test_same_neuron_both_ticks_counts_separately() -> None:
    """Same neuron improves tick 1 and degrades tick 2 → both count (no dedup).

    Kills an impl that deduplicates by neuron name across ticks.
    net_improved=1, net_degraded=1 → trend='stable'.
    """
    n_improved = _flag("n_flip", volatile=False)
    n_degraded = _flag("n_flip", volatile=True)
    deltas = [
        _delta(improved=[n_improved], degraded=[]),
        _delta(improved=[], degraded=[n_degraded]),
    ]
    result = abstraction_quality_trend(deltas)
    assert result["net_improved"] == 1, f"n_flip improved in tick 1 must be counted; got {result}"
    assert result["net_degraded"] == 1, f"n_flip degraded in tick 2 must be counted; got {result}"
    assert result["trend"] == "stable", (
        f"1 improved vs 1 degraded must → 'stable'; got {result['trend']!r}"
    )
