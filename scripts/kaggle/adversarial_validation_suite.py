#!/usr/bin/env python3
"""
Cohezion Adversarial Validation & Worst-Slice Cross-Validation Suite
====================================================================
Implements Meta-Aspect 2 (Learning 533): Guards against Kaggle private test set shakeup.

1. Adversarial Validation:
   Tests for covariate shift between train and test distributions by training a domain
   classifier (Train=0, Test=1). If ROC-AUC > 0.55, drift is detected.

2. Worst-Slice Cross-Validation:
   Computes distribution-robust CV metrics:
   Score_robust = mean(scores) - 0.5 * std(scores) - 0.5 * (mean(scores) - min(scores))
"""

from __future__ import annotations

import logging
from typing import Any
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [ADVERSARIAL-VAL] - %(levelname)s - %(message)s")
logger = logging.getLogger("adversarial_val")


class AdversarialValidationSuite:
    """Detects train/test covariate shift and evaluates worst-slice stability."""

    @classmethod
    def compute_adversarial_drift(
        cls,
        x_train: np.ndarray,
        x_test: np.ndarray,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Calculates covariate shift AUC between train and test feature distributions."""
        rng = np.random.default_rng(seed)
        n_train = len(x_train)
        n_test = len(x_test)

        x_comb = np.vstack([x_train, x_test])
        y_comb = np.concatenate([np.zeros(n_train), np.ones(n_test)])

        # Shuffle
        idx = rng.permutation(len(x_comb))
        x_comb = x_comb[idx]
        y_comb = y_comb[idx]

        # Standardize
        # 5-fold Out-Of-Fold (OOF) cross-validation to eliminate in-sample overfitting
        n_folds = 5
        oof_preds = np.zeros(len(x_comb))
        fold_size = len(x_comb) // n_folds
        alpha = 10.0

        for f in range(n_folds):
            val_idx = np.arange(f * fold_size, (f + 1) * fold_size if f < n_folds - 1 else len(x_comb))
            train_mask = np.ones(len(x_comb), dtype=bool)
            train_mask[val_idx] = False
            
            x_tr, y_tr = x_comb[train_mask], y_comb[train_mask]
            x_va = x_comb[val_idx]
            
            # Standardize based on training fold
            m_tr = np.mean(x_tr, axis=0)
            s_tr = np.std(x_tr, axis=0) + 1e-8
            x_tr_norm = (x_tr - m_tr) / s_tr
            x_va_norm = (x_va - m_tr) / s_tr
            
            xtx = x_tr_norm.T @ x_tr_norm + alpha * np.eye(x_tr_norm.shape[1])
            xty = x_tr_norm.T @ y_tr
            weights = np.linalg.solve(xtx, xty)
            oof_preds[val_idx] = x_va_norm @ weights

        # Compute empirical ROC-AUC on Out-Of-Fold predictions via Wilcoxon-Mann-Whitney
        pos_preds = oof_preds[y_comb == 1]
        neg_preds = oof_preds[y_comb == 0]

        # Fast exact / bounded sample comparison
        if len(pos_preds) * len(neg_preds) > 1_000_000:
            pos_sample = rng.choice(pos_preds, size=min(1000, len(pos_preds)), replace=False)
            neg_sample = rng.choice(neg_preds, size=min(1000, len(neg_preds)), replace=False)
        else:
            pos_sample = pos_preds
            neg_sample = neg_preds

        pairs = np.sum(pos_sample[:, None] > neg_sample[None, :]) + 0.5 * np.sum(pos_sample[:, None] == neg_sample[None, :])
        auc = float(pairs / (len(pos_sample) * len(neg_sample)))

        drift_detected = auc > 0.55
        risk_level = "LOW"
        if auc > 0.70:
            risk_level = "CRITICAL (Severe Shakeup Risk)"
        elif auc > 0.58:
            risk_level = "MODERATE (Noticeable Drift)"

        return {
            "roc_auc": round(auc, 4),
            "drift_detected": drift_detected,
            "risk_level": risk_level,
            "train_samples": n_train,
            "test_samples": n_test,
            "num_features": x_train.shape[1],
            "recommendation": (
                "Feature distributions match closely. Public LB reliable."
                if not drift_detected else
                "Covariate shift detected! Prioritize worst-slice CV over public LB."
            ),
        }

    @classmethod
    def evaluate_worst_slice_cv(
        cls,
        fold_scores: list[float] | np.ndarray,
        metric_higher_is_better: bool = True,
    ) -> dict[str, Any]:
        """Calculates robust cross-validation metrics penalizing high-variance folds."""
        arr = np.array(fold_scores, dtype=float)
        mean_sc = float(np.mean(arr))
        std_sc = float(np.std(arr))
        min_sc = float(np.min(arr))
        max_sc = float(np.max(arr))

        if metric_higher_is_better:
            worst_fold = min_sc
            gap_to_worst = mean_sc - min_sc
            robust_score = mean_sc - 0.5 * std_sc - 0.5 * gap_to_worst
        else:
            worst_fold = max_sc
            gap_to_worst = max_sc - mean_sc
            robust_score = mean_sc + 0.5 * std_sc + 0.5 * gap_to_worst

        return {
            "mean_score": round(mean_sc, 4),
            "std_score": round(std_sc, 4),
            "worst_fold_score": round(worst_fold, 4),
            "best_fold_score": round(max_sc if metric_higher_is_better else min_sc, 4),
            "robust_score": round(robust_score, 4),
            "shakeup_vulnerability": "HIGH" if std_sc > 0.02 or gap_to_worst > 0.03 else "LOW",
        }


def run_smoke_test():
    logger.info("=== Running Adversarial Validation & Worst-Slice CV Smoke Test ===")

    # Test 1: Synthetic identical distributions
    rng = np.random.default_rng(42)
    train_x = rng.normal(0, 1, size=(500, 10))
    test_x = rng.normal(0, 1, size=(200, 10))
    res_clean = AdversarialValidationSuite.compute_adversarial_drift(train_x, test_x)
    logger.info("Identical Distribution Test: AUC=%.4f (Risk: %s)", res_clean["roc_auc"], res_clean["risk_level"])
    assert res_clean["roc_auc"] < 0.60, f"False drift detected on identical data: {res_clean['roc_auc']}"

    # Test 2: Synthetic shifted distribution
    test_drifted = rng.normal(0.6, 1.2, size=(200, 10))
    res_drift = AdversarialValidationSuite.compute_adversarial_drift(train_x, test_drifted)
    logger.info("Shifted Distribution Test:   AUC=%.4f (Risk: %s)", res_drift["roc_auc"], res_drift["risk_level"])
    assert res_drift["drift_detected"], "Failed to detect covariate shift!"

    # Test 3: Worst-slice CV evaluation
    scores = [0.962, 0.958, 0.961, 0.940, 0.963]  # Fold 4 dropped to 0.940
    res_cv = AdversarialValidationSuite.evaluate_worst_slice_cv(scores)
    logger.info("Worst-Slice CV Test: Mean=%.4f, Worst=%.4f, Robust=%.4f (Vulnerability: %s)",
                res_cv["mean_score"], res_cv["worst_fold_score"], res_cv["robust_score"], res_cv["shakeup_vulnerability"])

    logger.info("✓ Adversarial Validation Suite smoke test PASSED cleanly!")


if __name__ == "__main__":
    run_smoke_test()
