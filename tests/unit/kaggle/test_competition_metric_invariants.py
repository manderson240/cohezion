"""Unit Tests for Competition Metric Invariants, Data Structures, and Algorithms."""

import numpy as np
import pytest

from cohezion.kaggle.competition_metric_invariants import (
    CompetitionDomain,
    compute_arc_exact_match_top2,
    compute_balanced_accuracy,
    compute_macro_roc_auc,
    compute_topk_canonical_inchikey_accuracy,
    copula_rank_transform,
    get_metric_spec,
    sinkhorn_uniform_marginal_balance,
)


def test_get_metric_spec_all_active_competitions():
    """All 7 active competitions must have complete metric and data structure specs."""
    for dom in CompetitionDomain:
        spec = get_metric_spec(dom)
        assert spec.domain == dom
        assert spec.direction in ("higher", "lower")
        assert len(spec.primary_data_structures) > 0
        assert len(spec.optimal_algorithms) > 0
        assert len(spec.invariant_rules) > 0


def test_compute_balanced_accuracy():
    """Balanced accuracy must compute true macro-averaged recall across classes."""
    # Imbalanced classes: Class 0 has 10 samples, Class 1 has 2 samples
    y_true = np.array([0] * 10 + [1] * 2)
    # Model gets 10/10 on Class 0 (recall=1.0), 1/2 on Class 1 (recall=0.5)
    y_pred = np.array([0] * 10 + [1, 0])
    
    score = compute_balanced_accuracy(y_true, y_pred)
    # Macro-average = (1.0 + 0.5) / 2 = 0.75
    assert np.isclose(score, 0.75)


def test_sinkhorn_uniform_marginal_balance():
    """Sinkhorn balancing must force column sums to be uniform (N / K)."""
    np.random.seed(42)
    N, K = 100, 18
    # Skewed raw model predictions (heavily biased toward class 0)
    raw_probs = np.random.exponential(scale=1.0, size=(N, K))
    raw_probs[:, 0] *= 5.0
    raw_probs /= raw_probs.sum(axis=1, keepdims=True)

    balanced = sinkhorn_uniform_marginal_balance(raw_probs, max_iter=200, tol=1e-5)
    
    # Each row must still be a valid probability distribution
    assert np.allclose(balanced.sum(axis=1), 1.0, atol=1e-4)
    # The marginal column sum must equal N / K
    col_sums = balanced.sum(axis=0)
    expected_col_sum = N / K
    assert np.allclose(col_sums, expected_col_sum, atol=1e-3)


def test_compute_macro_roc_auc_and_copula_rank():
    """ROC-AUC must be invariant under monotonic rank transform."""
    y_true = np.array([[1, 0], [1, 1], [0, 0], [0, 1]])
    y_pred = np.array([[0.8, 0.2], [0.9, 0.7], [0.1, 0.3], [0.4, 0.9]])

    auc_raw = compute_macro_roc_auc(y_true, y_pred)
    
    # Apply copula rank transform
    ranked_pred = copula_rank_transform(y_pred)
    auc_ranked = compute_macro_roc_auc(y_true, ranked_pred)

    # Monotonic copula transformation preserves individual column ROC-AUC exactly
    assert np.isclose(auc_raw, auc_ranked, atol=1e-5)
    assert auc_ranked > 0.75


def test_compute_topk_canonical_inchikey_accuracy():
    """Top-k accuracy must match on 14-character molecular skeleton."""
    true_keys = ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"]
    
    # Candidate lists where first skeleton matches
    pred_lists = [
        ["BSYNRYMUTXBXSQ-XYZ1234567-N", "ANOTHERMOL1234-UHFFFAOYSA-N"],
        ["WRONGMOL123456-UHFFFAOYSA-N", "LFQSCWFLJHTTHZ-DIFFERENT12-N"],
    ]

    top1 = compute_topk_canonical_inchikey_accuracy(true_keys, pred_lists, k=1)
    assert np.isclose(top1, 0.5)

    top2 = compute_topk_canonical_inchikey_accuracy(true_keys, pred_lists, k=2)
    assert np.isclose(top2, 1.0)


def test_compute_arc_exact_match_top2():
    """ARC exact match must succeed if either attempt 1 or attempt 2 matches ground truth."""
    gt_1 = np.array([[1, 2], [3, 4]])
    gt_2 = np.array([[5, 6], [7, 8]])
    
    # Task 1: attempt 1 matches. Task 2: attempt 2 matches.
    pred_1 = [gt_1, np.zeros_like(gt_1)]
    pred_2 = [np.ones_like(gt_2), gt_2]

    score = compute_arc_exact_match_top2([gt_1, gt_2], [pred_1, pred_2])
    assert np.isclose(score, 1.0)

    # Task 1: neither attempt matches.
    pred_1_wrong = [np.zeros_like(gt_1), np.ones_like(gt_1)]
    score_half = compute_arc_exact_match_top2([gt_1, gt_2], [pred_1_wrong, pred_2])
    assert np.isclose(score_half, 0.5)
