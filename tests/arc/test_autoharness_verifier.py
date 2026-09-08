"""Unit tests for AutoHarness Candidate Verifier and Diversified Ranker."""

from __future__ import annotations

import numpy as np

from cohezion.arc.autoharness_verifier import (
    AutoHarnessCandidateVerifier,
    TaskInvariantAnalyzer,
    rank_and_select_candidates,
)


def test_shape_invariant_identity():
    task = {
        "train": [
            {"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]},
            {"input": [[0, 0, 1], [1, 0, 0]], "output": [[1, 0, 0], [0, 0, 1]]},
        ]
    }
    inv = TaskInvariantAnalyzer.derive_shape_invariant(task["train"])
    assert inv.rule_type == "identity"
    assert inv.validate((2, 2), (2, 2)) is True
    assert inv.validate((2, 2), (3, 3)) is False


def test_shape_invariant_constant():
    task = {
        "train": [
            {"input": [[1, 2], [3, 4]], "output": [[5]]},
            {"input": [[0, 0, 1], [1, 0, 0]], "output": [[5]]},
        ]
    }
    inv = TaskInvariantAnalyzer.derive_shape_invariant(task["train"])
    assert inv.rule_type == "constant"
    assert inv.target_shape == (1, 1)
    assert inv.validate((5, 5), (1, 1)) is True
    assert inv.validate((5, 5), (5, 5)) is False


def test_shape_invariant_scaled():
    task = {
        "train": [
            {
                "input": [[1, 2], [3, 4]],
                "output": [[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]],
            },
        ]
    }
    inv = TaskInvariantAnalyzer.derive_shape_invariant(task["train"])
    assert inv.rule_type == "scaled"
    assert inv.scale_factor == (2.0, 2.0)
    assert inv.validate((3, 3), (6, 6)) is True
    assert inv.validate((3, 3), (3, 3)) is False


def test_verifier_blocks_alien_colors():
    task = {
        "train": [
            {"input": [[1, 2]], "output": [[2, 1]]},
        ]
    }
    verifier = AutoHarnessCandidateVerifier(task)
    test_in = np.array([[1, 2]])

    # Valid candidate (uses colors 1 and 2)
    valid_cand = np.array([[2, 1]])
    passed, _, reason = verifier.verify_candidate(test_in, valid_cand)
    assert passed is True
    assert reason == "passed"

    # Invalid candidate with alien color 8
    alien_cand = np.array([[2, 8]])
    passed, _, reason = verifier.verify_candidate(test_in, alien_cand)
    assert passed is False
    assert "unallowed_colors" in reason


def test_rank_and_select_diverse_candidates():
    task = {
        "train": [
            {"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]},
        ]
    }
    test_in = np.array([[1, 2], [3, 4]])

    cand_top_score_bad_shape = {
        "solution": [[1]],  # Violates (2, 2) shape
        "beam_score": 10.0,
    }
    cand_good_1 = {
        "solution": [[2, 1], [4, 3]],
        "beam_score": 5.0,
    }
    cand_good_2_identical = {
        "solution": [[2, 1], [4, 3]],
        "beam_score": 4.9,
    }
    cand_good_3_diverse = {
        "solution": [[1, 2], [3, 4]],
        "beam_score": 4.8,
    }

    selected = rank_and_select_candidates(
        test_in,
        [cand_top_score_bad_shape, cand_good_1, cand_good_2_identical, cand_good_3_diverse],
        task,
        n_guesses=2,
    )

    assert len(selected) == 2
    # Attempt 1 must be cand_good_1 (since top-score candidate was rejected for bad shape)
    assert selected[0] == [[2, 1], [4, 3]]
    # Attempt 2 must be cand_good_3_diverse (distinct from attempt 1)
    assert selected[1] == [[1, 2], [3, 4]]
