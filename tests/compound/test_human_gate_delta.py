"""Item 81: human-gate decision delta (report-only, TDD red→green).

`human_gate_delta(before, after)` diffs two human_gate_report snapshots and returns
`{resolved, introduced, reason_changed}`.

Each test fails a plausible wrong impl:
  - reports every common target, even unchanged ones  -> test_unchanged_target_in_no_list
  - resolves targets that only shifted reason         -> test_reason_changed_not_resolved
  - misses reason_changed when both snapshots present -> test_reason_changed_detected
  - non-empty on identical snapshots                  -> test_identical_snapshots_all_empty
"""

from __future__ import annotations

from cohezion.compound.scope_frontier import (
    HumanGateDecision,
    HumanGateDelta,
    human_gate_delta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _d(target: str, reason: str = "see ledger", kind: str = "empty_task_slot") -> HumanGateDecision:
    return HumanGateDecision(target=target, kind=kind, gate_reason=reason)


# ---------------------------------------------------------------------------
# Core discrimination tests
# ---------------------------------------------------------------------------


class TestResolved:
    """A blocker present in before and absent in after → resolved."""

    def test_removed_blocker_is_resolved(self) -> None:
        before = [_d("X"), _d("Y")]
        after = [_d("Y")]
        delta = human_gate_delta(before, after)
        assert delta.resolved == ["X"]

    def test_stable_blocker_not_resolved(self) -> None:
        before = [_d("X"), _d("Y")]
        after = [_d("X"), _d("Y")]
        delta = human_gate_delta(before, after)
        assert delta.resolved == []

    def test_multiple_resolved_sorted(self) -> None:
        before = [_d("Z"), _d("A"), _d("M")]
        after: list[HumanGateDecision] = []
        delta = human_gate_delta(before, after)
        assert delta.resolved == ["A", "M", "Z"]


class TestIntroduced:
    """A blocker new in after but absent from before → introduced."""

    def test_new_blocker_is_introduced(self) -> None:
        before = [_d("A")]
        after = [_d("A"), _d("B")]
        delta = human_gate_delta(before, after)
        assert delta.introduced == ["B"]

    def test_stable_blocker_not_introduced(self) -> None:
        before = [_d("A"), _d("B")]
        after = [_d("A"), _d("B")]
        delta = human_gate_delta(before, after)
        assert delta.introduced == []

    def test_multiple_introduced_sorted(self) -> None:
        before: list[HumanGateDecision] = []
        after = [_d("C"), _d("A"), _d("B")]
        delta = human_gate_delta(before, after)
        assert delta.introduced == ["A", "B", "C"]


class TestReasonChanged:
    """A target in BOTH with a changed gate_reason → reason_changed (not resolved/introduced)."""

    def test_reason_changed_detected(self) -> None:
        """A shifted gate_reason goes into reason_changed, not resolved or introduced."""
        before = [_d("X", reason="blocked by LFM2.5 license")]
        after = [_d("X", reason="blocked by memory budget")]
        delta = human_gate_delta(before, after)
        assert delta.reason_changed == ["X"]
        assert delta.resolved == []
        assert delta.introduced == []

    def test_reason_changed_not_resolved(self) -> None:
        """Changing the reason does NOT count as resolving the blocker (still gated)."""
        before = [_d("X", reason="needs-human: ledger row 3")]
        after = [_d("X", reason="needs-human: updated rationale")]
        delta = human_gate_delta(before, after)
        assert "X" not in delta.resolved, "shifted reason ≠ resolved"

    def test_unchanged_reason_in_no_list(self) -> None:
        """A target present in both with the SAME reason appears in NO list (main discriminator)."""
        before = [_d("X", reason="same reason"), _d("Y")]
        after = [_d("X", reason="same reason"), _d("Y")]
        delta = human_gate_delta(before, after)
        assert "X" not in delta.resolved
        assert "X" not in delta.introduced
        assert "X" not in delta.reason_changed


class TestIdentical:
    """Identical snapshots → all lists empty."""

    def test_identical_snapshots_all_empty(self) -> None:
        snap = [_d("A", reason="r1"), _d("B", reason="r2")]
        delta = human_gate_delta(snap, snap)
        assert isinstance(delta, HumanGateDelta)
        assert delta.resolved == []
        assert delta.introduced == []
        assert delta.reason_changed == []

    def test_both_empty_all_empty(self) -> None:
        delta = human_gate_delta([], [])
        assert delta.resolved == []
        assert delta.introduced == []
        assert delta.reason_changed == []


class TestEdgeCases:
    """Empty and mixed inputs."""

    def test_empty_after_all_resolved(self) -> None:
        before = [_d("A"), _d("B")]
        delta = human_gate_delta(before, [])
        assert delta.resolved == ["A", "B"]
        assert delta.introduced == []

    def test_empty_before_all_introduced(self) -> None:
        after = [_d("A"), _d("B")]
        delta = human_gate_delta([], after)
        assert delta.resolved == []
        assert delta.introduced == ["A", "B"]

    def test_mixed_all_three_categories(self) -> None:
        """Resolved + introduced + reason_changed all populate in one call."""
        before = [
            _d("gone", reason="old"),  # will be resolved
            _d("shifted", reason="reason1"),  # will be reason_changed
            _d("stable", reason="same"),  # unchanged → in no list
        ]
        after = [
            _d("shifted", reason="reason2"),
            _d("stable", reason="same"),
            _d("new", reason="new-reason"),  # introduced
        ]
        delta = human_gate_delta(before, after)
        assert delta.resolved == ["gone"]
        assert delta.introduced == ["new"]
        assert delta.reason_changed == ["shifted"]
