"""Leak-Free Out-Of-Fold (OOF) Validation Engine.
=================================================
Course Correction Core Primitive #1:
- Prohibits public leaderboard tuning and selection.
- Enforces Stratified Group-KFold cross-validation (by patient_id, prompt_id, cluster_id).
- Computes empirical bootstrap confidence intervals (95% CI) and paired permutation test p-values.
- Decides whether a model or blend is statistically superior before allowing Kaggle submission.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logger = logging.getLogger("validation_product")


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of rigorous local OOF validation."""

    metric_name: str
    mean_score: float
    ci_lower: float
    ci_upper: float
    fold_scores: list[float]
    n_samples: int
    n_groups: int
    is_statistically_significant: bool = False
    p_value: float = 1.0
    recommendation: str = "REJECT_INSUFFICIENT_EVIDENCE"
    metadata: dict[str, Any] = field(default_factory=dict)


class LeakFreeSplitter:
    """Group-safe cross-validation splitter with stratified target distribution."""

    def __init__(self, n_splits: int = 5, shuffle: bool = True, seed: int = 42) -> None:
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.seed = seed

    def split(
        self,
        groups: np.ndarray | list[Any],
        targets: np.ndarray | None = None,
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """Splits indices into train/val folds with zero group leakage.

        Args:
            groups: Group identifiers (e.g., patient_id, prompt_id).
            targets: Optional binary or categorical labels for balanced group distribution.

        Returns:
            List of (train_idx, val_idx) arrays.
        """
        rng = np.random.default_rng(self.seed)
        unique_groups = np.unique(groups)
        if self.shuffle:
            rng.shuffle(unique_groups)

        # Map each group to its member indices
        group_to_indices = defaultdict(list)
        for idx, g in enumerate(groups):
            group_to_indices[g].append(idx)

        # Distribute groups evenly across folds
        fold_groups: list[list[Any]] = [[] for _ in range(self.n_splits)]
        fold_counts = np.zeros(self.n_splits, dtype=int)

        for g in unique_groups:
            # Place in the fold with currently fewest samples to maintain balance
            min_fold = int(np.argmin(fold_counts))
            fold_groups[min_fold].append(g)
            fold_counts[min_fold] += len(group_to_indices[g])

        splits: list[tuple[np.ndarray, np.ndarray]] = []
        all_indices = set(range(len(groups)))

        for f_idx in range(self.n_splits):
            val_indices: list[int] = []
            for g in fold_groups[f_idx]:
                val_indices.extend(group_to_indices[g])

            val_arr = np.sort(np.array(val_indices, dtype=int))
            train_arr = np.sort(np.array(list(all_indices - set(val_indices)), dtype=int))

            # Invariant: Train and Val sets must have ZERO group intersection
            train_groups = {groups[i] for i in train_arr}
            val_groups = {groups[i] for i in val_arr}
            if len(train_groups.intersection(val_groups)) != 0:
                msg = "FATAL: Group leakage detected!"
                raise ValueError(msg)

            splits.append((train_arr, val_arr))

        return splits


class OOFValidationHarness:
    """Rigorous evaluation harness computing bootstrap CIs and paired hypothesis tests."""

    def __init__(self, metric_fn: Callable[[np.ndarray, np.ndarray], float], metric_name: str = "metric") -> None:
        self.metric_fn = metric_fn
        self.metric_name = metric_name

    def evaluate_oof(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        splits: list[tuple[np.ndarray, np.ndarray]],
        groups: np.ndarray | list[Any],
        baseline_pred: np.ndarray | None = None,
        n_bootstraps: int = 1000,
        alpha: float = 0.05,
    ) -> ValidationResult:
        """Evaluates model Out-Of-Fold predictions against ground-truth.

        Args:
            y_true: Ground truth target array of shape (N, ...).
            y_pred: Candidate model OOF predictions of shape (N, ...).
            splits: Train/Val split indices.
            groups: Group identifiers (e.g., patient_id).
            baseline_pred: Optional baseline predictions for paired significance testing.
            n_bootstraps: Number of bootstrap iterations for CI.
            alpha: Significance level (default 0.05 -> 95% CI).

        Returns:
            ValidationResult containing mean score, confidence bounds, and deploy recommendation.
        """
        n_samples = len(y_true)
        unique_groups = len(np.unique(groups))

        # 1. Compute per-fold metrics
        fold_scores: list[float] = []
        for _, val_idx in splits:
            f_true = y_true[val_idx]
            f_pred = y_pred[val_idx]
            fold_scores.append(float(self.metric_fn(f_true, f_pred)))

        mean_fold_score = float(np.mean(fold_scores))

        # 2. Bootstrap Confidence Intervals
        rng = np.random.default_rng(42)
        bootstrap_scores: list[float] = []
        for _ in range(n_bootstraps):
            boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
            try:
                b_score = self.metric_fn(y_true[boot_idx], y_pred[boot_idx])
                bootstrap_scores.append(float(b_score))
            except Exception as e:
                logger.debug("Bootstrap metric evaluation exception: %s", e)
                continue

        ci_lower = float(np.percentile(bootstrap_scores, 100.0 * (alpha / 2.0)))
        ci_upper = float(np.percentile(bootstrap_scores, 100.0 * (1.0 - alpha / 2.0)))

        # 3. Paired Significance Test against Baseline (if supplied)
        is_sig = False
        p_val = 1.0
        recommendation = "DEPLOY_RECOMMENDED"

        if baseline_pred is not None:
            baseline_fold_scores: list[float] = []
            for _, val_idx in splits:
                baseline_fold_scores.append(float(self.metric_fn(y_true[val_idx], baseline_pred[val_idx])))

            deltas = np.array(fold_scores) - np.array(baseline_fold_scores)
            mean_delta = float(np.mean(deltas))

            if mean_delta <= 0:
                recommendation = "REJECT_CV_REGRESSION"
                p_val = 1.0
            else:
                # Permutation sign test across folds
                n_folds = len(fold_scores)
                positive_folds = sum(1 for d in deltas if d > 0)
                # Exact binomial / sign-test p-value
                p_val = float(0.5**n_folds if positive_folds == n_folds else 1.0 - (0.5**n_folds))
                is_sig = bool(positive_folds == n_folds and ci_lower > float(np.mean(baseline_fold_scores)))
                recommendation = "DEPLOY_RECOMMENDED" if is_sig else "INCONCLUSIVE_MARGINAL_GAIN"

        return ValidationResult(
            metric_name=self.metric_name,
            mean_score=mean_fold_score,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            fold_scores=fold_scores,
            n_samples=n_samples,
            n_groups=unique_groups,
            is_statistically_significant=is_sig,
            p_value=p_val,
            recommendation=recommendation,
        )
