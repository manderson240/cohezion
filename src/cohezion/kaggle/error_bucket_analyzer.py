"""Systematic Error Bucketing and Failure Mode Decomposition Engine.
=====================================================================
Course Correction Core Primitive #4:
- Decomposes Out-Of-Fold (OOF) predictions into class-wise and slice-wise error buckets.
- Identifies the Pareto 20% of failure categories accounting for >75% of lost metric performance.
- Directs engineering effort away from generic model tuning toward the highest-leverage error sources.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger("error_bucket_analyzer")


@dataclass(frozen=True)
class ErrorBucket:
    """Detailed diagnosis of a specific failure category."""

    bucket_name: str
    class_index: int
    n_positives: int
    n_negatives: int
    observed_metric: float
    ideal_metric: float
    lost_metric_delta: float
    relative_penalty_share: float
    remedy_recommendation: str


@dataclass(frozen=True)
class ErrorAnalysisReport:
    """Comprehensive failure mode scorecard."""

    competition: str
    overall_metric: float
    buckets: list[ErrorBucket]
    top_priority_buckets: list[str]
    cumulative_penalty_addressed: float
    actionable_remedies: list[str]


class ErrorBucketAnalyzer:
    """Analyzes multi-label and multi-class predictions to isolate critical error sources."""

    def __init__(self, class_names: list[str], competition_name: str = "generic") -> None:
        self.class_names = class_names
        self.competition_name = competition_name

    def analyze_rsna_knee_errors(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> ErrorAnalysisReport:
        """Decomposes RSNA Knee Abnormality OOF predictions across the 12 pathologies.

        Computes per-label ROC-AUC, lost AUC gap, and relative share of total penalty.
        """
        _n_samples, k_classes = y_true.shape
        if len(self.class_names) != k_classes:
            msg = f"Class names count {len(self.class_names)} != K {k_classes}"
            raise ValueError(msg)

        bucket_data = []
        total_lost_auc = 0.0

        for k in range(k_classes):
            pos_scores = y_pred[y_true[:, k] == 1, k]
            neg_scores = y_pred[y_true[:, k] == 0, k]

            P_k = len(pos_scores)
            N_k = len(neg_scores)

            if P_k == 0 or N_k == 0:
                auc_k = 0.5
            else:
                diff = pos_scores[:, None] - neg_scores[None, :]
                concordance = np.sum(diff > 0) + 0.5 * np.sum(diff == 0)
                auc_k = float(concordance / (P_k * N_k))

            lost_auc = max(0.0, 1.0 - auc_k)
            total_lost_auc += lost_auc

            # Remedial prescription based on anatomical pathology characteristics
            name = self.class_names[k]
            if "Fracture" in name or "Contusion" in name:
                remedy = "Inject high-resolution bone-window presets & hard-negative contusion mining."
            elif "Meniscus" in name:
                remedy = "Sagittal slice thickness interpolation & multi-scale localized attention."
            elif "OA" in name:
                remedy = "Joint Space Narrowing (JSN) compartment affinity loss & bilateral symmetry ratio."
            elif "ACL" in name or "MCL" in name:
                remedy = "Coronal/Sagittal dual-view cross-attention & pivot-shift co-occurrence prior."
            else:
                remedy = "Volumetric fluid segmentation mask guidance."

            bucket_data.append({
                "name": name,
                "index": k,
                "p_k": P_k,
                "n_k": N_k,
                "auc": auc_k,
                "lost": lost_auc,
                "remedy": remedy,
            })

        # Sort by lost AUC descending (largest error sources first)
        bucket_data.sort(key=lambda b: b["lost"], reverse=True)

        buckets: list[ErrorBucket] = []
        cum_penalty = 0.0
        top_priorities: list[str] = []
        remedies: list[str] = []

        for b in bucket_data:
            share = (b["lost"] / total_lost_auc) if total_lost_auc > 0 else 0.0
            eb = ErrorBucket(
                bucket_name=b["name"],
                class_index=b["index"],
                n_positives=b["p_k"],
                n_negatives=b["n_k"],
                observed_metric=round(b["auc"], 4),
                ideal_metric=1.0,
                lost_metric_delta=round(b["lost"], 4),
                relative_penalty_share=round(share, 4),
                remedy_recommendation=b["remedy"],
            )
            buckets.append(eb)

            if cum_penalty < 0.75:
                top_priorities.append(b["name"])
                remedies.append(f"[{b['name']} - AUC {b['auc']:.3f}]: {b['remedy']}")
                cum_penalty += share

        overall_auc = float(np.mean([b.observed_metric for b in buckets]))

        return ErrorAnalysisReport(
            competition=self.competition_name,
            overall_metric=round(overall_auc, 4),
            buckets=buckets,
            top_priority_buckets=top_priorities,
            cumulative_penalty_addressed=round(cum_penalty, 4),
            actionable_remedies=remedies,
        )
