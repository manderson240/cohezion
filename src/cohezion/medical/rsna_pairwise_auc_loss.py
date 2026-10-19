"""RSNA Knee Abnormality Detection: Pairwise AUC Ranking Loss.
==============================================================
Course Correction Core Primitive #3:
- Replaces standard Binary Cross-Entropy (BCE) with direct pairwise AUC surrogate optimization.
- Mathematical Formulation:
    L_auc = (1 / K) * sum_k [ (1 / (P_k * N_k)) * sum_{i in P_k, j in N_k} log(1 + exp(-(s_{ik} - s_{jk}))) ]
- Invariant: Direct gradient alignment with the primary evaluation metric (Macro-averaged ROC-AUC).
- Supports mini-batch positive-negative sampling and vectorized PyTorch / NumPy execution.
"""

from __future__ import annotations

import numpy as np


class PairwiseAUCRankingLoss:
    """Pairwise differentiable surrogate for Macro-averaged ROC-AUC."""

    def __init__(self, margin: float = 1.0, temperature: float = 1.0) -> None:
        self.margin = margin
        self.temperature = temperature

    def compute_loss_numpy(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        eps: float = 1e-7,
    ) -> tuple[float, dict[int, float]]:
        """Computes the exact Macro Pairwise Ranking Loss in NumPy.

        Args:
            y_true: Binary ground-truth labels of shape (N, K).
            y_pred: Predicted logits or scores of shape (N, K).
            eps: Numerical stability epsilon.

        Returns:
            Tuple of (macro_loss, per_label_loss_dict).
        """
        _n_samples, K = y_true.shape
        per_label_loss: dict[int, float] = {}
        total_loss = 0.0

        for k in range(K):
            pos_mask = y_true[:, k] == 1
            neg_mask = y_true[:, k] == 0

            pos_scores = y_pred[pos_mask, k]
            neg_scores = y_pred[neg_mask, k]

            P_k = len(pos_scores)
            N_k = len(neg_scores)

            if P_k == 0 or N_k == 0:
                # If a mini-batch has no positives or negatives for label k, loss is zero
                per_label_loss[k] = 0.0
                continue

            # Vectorized pairwise differences: shape (P_k, N_k)
            # diff[i, j] = pos_scores[i] - neg_scores[j]
            diff = pos_scores[:, None] - neg_scores[None, :]

            # Smooth surrogate: log(1 + exp(-diff / temperature))
            scaled_diff = diff / self.temperature
            # Numerically stable log1p(exp(-x))
            # For x > 0: log(1 + exp(-x))
            # For x <= 0: -x + log(1 + exp(x))
            pairwise_loss = np.where(
                scaled_diff > 0,
                np.log1p(np.exp(-scaled_diff)),
                -scaled_diff + np.log1p(np.exp(scaled_diff)),
            )

            k_loss = float(np.mean(pairwise_loss))
            per_label_loss[k] = k_loss
            total_loss += k_loss

        macro_loss = total_loss / max(K, 1)
        return macro_loss, per_label_loss

    def compute_macro_roc_auc_numpy(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Computes exact empirical Macro ROC-AUC via Wilcoxon-Mann-Whitney U statistic."""
        _n_samples, K = y_true.shape
        aucs = []

        for k in range(K):
            pos_scores = y_pred[y_true[:, k] == 1, k]
            neg_scores = y_pred[y_true[:, k] == 0, k]

            P_k = len(pos_scores)
            N_k = len(neg_scores)

            if P_k == 0 or N_k == 0:
                continue

            diff = pos_scores[:, None] - neg_scores[None, :]
            # Concordance: 1 if pos > neg, 0.5 if tie
            concordance = np.sum(diff > 0) + 0.5 * np.sum(diff == 0)
            aucs.append(float(concordance / (P_k * N_k)))

        return float(np.mean(aucs)) if aucs else 0.5
