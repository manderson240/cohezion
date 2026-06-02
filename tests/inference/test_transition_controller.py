"""Tests for the Markov/MDP TransitionController + path analysis (SGLang-free)."""

from __future__ import annotations

from cohezion.inference.transition_controller import (
    TransitionController,
    detect_stuck_loops,
    first_passage,
    time_in_states,
)


_MATRIX = {
    "init": ["flux", "diag"],
    "flux": ["converge", "error"],
    "error": ["init"],
    "converge": ["log"],
    "log": ["init"],
}


def test_valid_next_and_is_valid() -> None:
    tc = TransitionController(_MATRIX)
    assert tc.valid_next("flux") == ["converge", "error"]
    assert tc.is_valid("flux", "converge") is True
    assert tc.is_valid("flux", "log") is False
    assert tc.valid_next("terminal-unknown") == []


def test_enum_schema_is_constrained_response_format() -> None:
    """enum_schema is the lemonade response_format that = SGLang select(choices=...)."""
    tc = TransitionController(_MATRIX)
    rf = tc.enum_schema("flux")
    assert rf["type"] == "json_schema"
    enum = rf["json_schema"]["schema"]["properties"]["next_state"]["enum"]
    assert enum == ["converge", "error"]
    assert rf["json_schema"]["strict"] is True


def test_record_transition_decays_bad_edges_and_raises_good() -> None:
    tc = TransitionController(_MATRIX)
    tc.record_transition("flux", "error", -0.8)
    tc.record_transition("flux", "converge", 0.9)
    ranked = tc.ranked_next("flux")
    assert ranked[0][0] == "converge", "good transition should rank first"
    assert ranked[-1][0] == "error"
    assert tc.weights[("flux", "error")] < 1.0 < tc.weights[("flux", "converge")]


def test_weight_clamped_to_bounds() -> None:
    tc = TransitionController(_MATRIX)
    for _ in range(50):
        tc.record_transition("flux", "error", -1.0)  # relentless punishment
    assert tc.weights[("flux", "error")] >= 0.01  # floor holds


def test_first_passage_finds_first_arrival() -> None:
    seq = ["init", "flux", "error", "error", "init", "flux", "converge", "log"]
    assert first_passage(seq, "converge") == 6
    assert first_passage(seq, "never") is None


def test_time_in_states_counts_occupancy() -> None:
    seq = ["init", "flux", "error", "error", "error", "init"]
    assert time_in_states(seq) == {"init": 2, "flux": 1, "error": 3}


def test_detect_stuck_loops_flags_consecutive_runs() -> None:
    # 3 consecutive 'error' = stuck; the two non-consecutive 'init' do not count.
    seq = ["init", "flux", "error", "error", "error", "init", "flux", "converge"]
    assert detect_stuck_loops(seq, threshold=3) == ["error"]
    # below threshold -> nothing
    assert detect_stuck_loops(["a", "a", "b"], threshold=3) == []
