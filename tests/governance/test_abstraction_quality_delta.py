"""Item 152: abstraction_quality_delta — TDD red→green (2026-06-08).

``abstraction_quality_delta(before_flags, after_flags)`` → ``{improved, degraded}``:
the delta twin of item-92 ``abstraction_quality``, mirroring item-127
``discovered_problem_delta``. Makes abstraction audits ITERATIVE: the loop tick
sees whether self-evolution is improving or degrading neuron quality.

Discriminating tests — each kills a plausible wrong implementation:

  1. volatile→abstract → improved only  (PRIMARY DISC.: kills "report all changes")
  2. abstract→volatile → degraded only  (kills impl that can't detect degradation)
  3. Stable on either side → in NEITHER list (kills "surface every changed neuron")
  4. Identical snapshots → both-empty   (kills impl that surfaces stable flags)
  5. Compared by ``name``, not position  (kills impl that zips by index)
"""

from __future__ import annotations

from cohezion.governance.abstraction_quality import AbstractionFlag, abstraction_quality_delta


def _flag(name: str, *, volatile: bool) -> AbstractionFlag:
    return AbstractionFlag(
        name=name,
        instance_specific=volatile,
        reasons=["test-pattern"] if volatile else [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_volatile_to_abstract_is_improved() -> None:
    """A neuron volatile in before + abstract in after → appears in improved.

    PRIMARY DISCRIMINATOR: kills an impl that surfaces ALL changed neurons or
    that puts the improvement in the degraded list.
    """
    before = [_flag("n1", volatile=True)]
    after = [_flag("n1", volatile=False)]
    delta = abstraction_quality_delta(before, after)
    names_improved = [f.name for f in delta["improved"]]
    names_degraded = [f.name for f in delta["degraded"]]
    assert "n1" in names_improved, f"n1 must be in improved; got improved={names_improved}"
    assert "n1" not in names_degraded, f"n1 must NOT be in degraded; got degraded={names_degraded}"


def test_abstract_to_volatile_is_degraded() -> None:
    """A neuron abstract in before + volatile in after → appears in degraded.

    Kills an impl that can only detect improvement (never detects degradation).
    """
    before = [_flag("n2", volatile=False)]
    after = [_flag("n2", volatile=True)]
    delta = abstraction_quality_delta(before, after)
    names_improved = [f.name for f in delta["improved"]]
    names_degraded = [f.name for f in delta["degraded"]]
    assert "n2" in names_degraded, f"n2 must be in degraded; got degraded={names_degraded}"
    assert "n2" not in names_improved, f"n2 must NOT be in improved; got improved={names_improved}"


def test_stable_volatile_in_neither_list() -> None:
    """A neuron volatile in BOTH before and after → in neither improved nor degraded.

    Kills an impl that surfaces every neuron that appears volatile in either snapshot.
    """
    before = [_flag("n3", volatile=True)]
    after = [_flag("n3", volatile=True)]
    delta = abstraction_quality_delta(before, after)
    names_all = [f.name for f in delta["improved"]] + [f.name for f in delta["degraded"]]
    assert "n3" not in names_all, f"stable-volatile n3 must be in neither list; got {delta}"


def test_identical_snapshots_both_empty() -> None:
    """Identical before/after → improved=[] and degraded=[] (no spurious output).

    Kills an impl that always outputs all flags regardless of change.
    """
    flags = [_flag("a", volatile=False), _flag("b", volatile=True)]
    delta = abstraction_quality_delta(flags, flags)
    assert delta["improved"] == [], (
        f"identical snapshots must → improved=[]; got {delta['improved']}"
    )
    assert delta["degraded"] == [], (
        f"identical snapshots must → degraded=[]; got {delta['degraded']}"
    )


def test_compared_by_name_not_position() -> None:
    """Delta is matched by AbstractionFlag.name, NOT by list position.

    Kills an impl that zips by index (n-th flag in before vs n-th in after),
    which would mismatch when flags are reordered between snapshots.
    """
    # before: n_a volatile, n_b abstract
    # after:  n_b abstract, n_a abstract  (reordered AND n_a improved)
    before = [_flag("n_a", volatile=True), _flag("n_b", volatile=False)]
    after = [_flag("n_b", volatile=False), _flag("n_a", volatile=False)]
    delta = abstraction_quality_delta(before, after)
    names_improved = [f.name for f in delta["improved"]]
    assert "n_a" in names_improved, (
        f"n_a (volatile→abstract) must be in improved regardless of position; got {names_improved}"
    )
    assert "n_b" not in names_improved, (
        f"n_b (stable abstract) must NOT be in improved; got {names_improved}"
    )
