"""Unit tests for Kaggle Podium Course Correction Modules.
============================================================
Validates:
1. LeakFreeSplitter: Zero group leakage and balanced split distribution.
2. OOFValidationHarness: Empirical bootstrap 95% CIs and paired hypothesis testing.
3. PairwiseAUCRankingLoss: Metric-grounded ranking loss vs empirical ROC-AUC.
4. ErrorBucketAnalyzer: Pareto failure identification and actionable remedies.
"""

from __future__ import annotations

import numpy as np

from cohezion.kaggle.error_bucket_analyzer import ErrorBucketAnalyzer
from cohezion.kaggle.validation_product import LeakFreeSplitter, OOFValidationHarness
from cohezion.medical.rsna_pairwise_auc_loss import PairwiseAUCRankingLoss


def test_leak_free_splitter_zero_group_leakage() -> None:
    # 200 samples across 20 distinct patients
    n_samples = 200
    n_groups = 20
    groups = np.repeat(np.arange(n_groups), n_samples // n_groups)

    splitter = LeakFreeSplitter(n_splits=5, shuffle=True, seed=123)
    splits = splitter.split(groups)

    assert len(splits) == 5
    for train_idx, val_idx in splits:
        train_groups = set(groups[train_idx])
        val_groups = set(groups[val_idx])
        # Invariant: Disjoint group sets
        assert len(train_groups.intersection(val_groups)) == 0
        assert len(train_idx) + len(val_idx) == n_samples


def test_oof_validation_harness_bootstrap_and_significance() -> None:
    rng = np.random.default_rng(42)
    n_samples = 300
    groups = np.repeat(np.arange(30), 10)

    y_true = rng.integers(0, 2, size=n_samples)
    baseline_pred = rng.uniform(0.1, 0.9, size=n_samples)
    # Superior candidate with higher correlation to ground truth
    candidate_pred = baseline_pred * 0.4 + y_true * 0.6

    def accuracy_metric(t: np.ndarray, p: np.ndarray) -> float:
        return float(np.mean(t == (p > 0.5).astype(int)))

    splitter = LeakFreeSplitter(n_splits=5, seed=42)
    splits = splitter.split(groups)

    harness = OOFValidationHarness(metric_fn=accuracy_metric, metric_name="accuracy")
    result = harness.evaluate_oof(
        y_true=y_true,
        y_pred=candidate_pred,
        splits=splits,
        groups=groups,
        baseline_pred=baseline_pred,
        n_bootstraps=200,
    )

    assert result.mean_score > 0.70
    assert result.ci_lower <= result.mean_score <= result.ci_upper
    assert result.recommendation == "DEPLOY_RECOMMENDED"
    assert result.is_statistically_significant is True


def test_pairwise_auc_ranking_loss_monotonically_tracks_auc() -> None:
    loss_fn = PairwiseAUCRankingLoss(temperature=1.0)

    # 100 samples, 4 labels
    y_true = np.array([
        [1, 0, 1, 0],
        [1, 1, 0, 0],
        [0, 0, 1, 1],
        [0, 1, 0, 1],
    ] * 25)

    # Perfect predictions: high scores on positives, low on negatives
    perfect_preds = np.where(y_true == 1, 5.0, -5.0)
    # Inverted predictions: low scores on positives, high on negatives
    inverted_preds = np.where(y_true == 1, -5.0, 5.0)

    loss_perf, _ = loss_fn.compute_loss_numpy(y_true, perfect_preds)
    loss_inv, _ = loss_fn.compute_loss_numpy(y_true, inverted_preds)

    auc_perf = loss_fn.compute_macro_roc_auc_numpy(y_true, perfect_preds)
    auc_inv = loss_fn.compute_macro_roc_auc_numpy(y_true, inverted_preds)

    assert auc_perf == 1.0
    assert auc_inv == 0.0
    # Invariant: Perfect AUC yields near-zero ranking loss; inverted yields high loss
    assert loss_perf < 0.01
    assert loss_inv > 5.0


def test_error_bucket_analyzer_isolates_pareto_priorities() -> None:
    labels = ["ACL", "MCL", "Medial Meniscus", "Effusion", "Fracture"]
    analyzer = ErrorBucketAnalyzer(class_names=labels, competition_name="rsna_test")

    # Synthetic predictions where Fracture and Meniscus have low AUC
    y_true = np.array([
        [1, 0, 1, 0, 1],
        [1, 1, 0, 1, 0],
        [0, 0, 1, 1, 1],
        [0, 1, 0, 0, 0],
    ] * 20)

    y_pred = y_true.astype(float) * 2.0 - 1.0
    # Inject heavy noise into Fracture (index 4) and Meniscus (index 2)
    rng = np.random.default_rng(99)
    y_pred[:, 4] = rng.uniform(-1.0, 1.0, size=len(y_true))
    y_pred[:, 2] = rng.uniform(-1.0, 1.0, size=len(y_true))

    report = analyzer.analyze_rsna_knee_errors(y_true, y_pred)

    assert len(report.buckets) == 5
    # Fracture and Medial Meniscus must be identified as top failure priorities
    assert "Fracture" in report.top_priority_buckets
    assert "Medial Meniscus" in report.top_priority_buckets
    assert report.cumulative_penalty_addressed >= 0.50
    assert len(report.actionable_remedies) > 0
