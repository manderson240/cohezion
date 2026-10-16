"""Formal Specification of Competition Metrics, Optimal Data Structures, and Invariant Algorithms.
================================================================================================
Implements:
- Strict mathematical evaluation metrics for all active Kaggle tracks.
- Validation functions guaranteeing adherence to competition invariants.
- Catalog of optimal data structures and domain-specific algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Tuple
import numpy as np


class CompetitionDomain(str, Enum):
    ARC_AGI_2 = "arc-prize-2026-arc-agi-2"
    ARC_AGI_3 = "arc-prize-2026-arc-agi-3"
    RSNA_KNEE = "rsna-knee-abnormality-detection"
    CASMI26 = "enveda-CASMI26-molecule-id-mass-spectra"
    NAME_THAT_LLM = "name-that-llm"
    GEMMA_4_DEV_AGENT = "gemma-4-developer-agent"
    NFL_BDB_2027 = "nfl-big-data-bowl-2027"


# ==============================================================================
# Metric Mathematical Evaluators
# ==============================================================================

def compute_balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes exact Balanced Accuracy: macro-average of recall per class.
    
    Formula:
        Balanced Accuracy = (1 / K) * sum_{k=1}^K (TP_k / P_k)
    """
    classes = np.unique(y_true)
    if len(classes) == 0:
        return 0.0
    recalls = []
    for c in classes:
        mask = (y_true == c)
        actual_positives = np.sum(mask)
        if actual_positives == 0:
            continue
        true_positives = np.sum((y_pred == c) & mask)
        recalls.append(true_positives / actual_positives)
    return float(np.mean(recalls)) if recalls else 0.0


def compute_macro_roc_auc(y_true: np.ndarray, y_pred_prob: np.ndarray) -> float:
    """Computes mean column-wise ROC-AUC across multi-label abnormalities.
    
    In RSNA Knee Abnormality Detection, evaluations are conducted over 12 findings.
    """
    if y_true.ndim == 1:
        y_true = y_true[:, None]
        y_pred_prob = y_pred_prob[:, None]

    n_cols = y_true.shape[1]
    aucs = []
    for c in range(n_cols):
        yt = y_true[:, c]
        yp = y_pred_prob[:, c]
        pos_mask = (yt == 1)
        neg_mask = (yt == 0)
        n_pos = np.sum(pos_mask)
        n_neg = np.sum(neg_mask)
        if n_pos == 0 or n_neg == 0:
            continue
        pos_scores = yp[pos_mask]
        neg_scores = yp[neg_mask]
        # Fast Wilcoxon-Mann-Whitney AUC statistic
        pairs = np.sum(pos_scores[:, None] > neg_scores[None, :]) + 0.5 * np.sum(
            pos_scores[:, None] == neg_scores[None, :]
        )
        aucs.append(pairs / (n_pos * n_neg))
    return float(np.mean(aucs)) if aucs else 0.5


def compute_topk_canonical_inchikey_accuracy(
    y_true_inchikeys: list[str], y_pred_candidate_lists: list[list[str]], k: int = 1
) -> float:
    """Computes Top-k accuracy on 14-character tautomer-canonical InChIKey skeleton.
    
    In CASMI26, the molecular skeleton is identified by the first 14 chars of the InChIKey.
    """
    if not y_true_inchikeys:
        return 0.0
    correct = 0
    for true_key, pred_list in zip(y_true_inchikeys, y_pred_candidate_lists):
        true_skeleton = true_key[:14]
        candidate_skeletons = [cand[:14] for cand in pred_list[:k]]
        if true_skeleton in candidate_skeletons:
            correct += 1
    return float(correct / len(y_true_inchikeys))


def compute_arc_exact_match_top2(
    ground_truth_grids: list[np.ndarray], predicted_attempts: list[list[np.ndarray]]
) -> float:
    """Computes ARC-AGI-2 exact match rate across 2 attempts.
    
    A task is scored 1 if AT LEAST ONE of the top 2 predicted grids matches perfectly.
    """
    if not ground_truth_grids:
        return 0.0
    solved = 0
    for gt, attempts in zip(ground_truth_grids, predicted_attempts):
        task_solved = False
        for cand in attempts[:2]:
            if cand.shape == gt.shape and np.array_equal(cand, gt):
                task_solved = True
                break
        if task_solved:
            solved += 1
    return float(solved / len(ground_truth_grids))


# ==============================================================================
# Optimal Algorithms & Transforms
# ==============================================================================

def sinkhorn_uniform_marginal_balance(
    probs: np.ndarray, max_iter: int = 200, tol: float = 1e-6
) -> np.ndarray:
    """Sinkhorn-Knopp Optimal Transport balancing for Balanced Accuracy.
    
    Forces marginal class distribution over test instances to match uniform 1/K prior:
        sum_i P[i, k] = N / K
        sum_k P[i, k] = 1.0
    """
    N, K = probs.shape
    P = np.maximum(probs, 1e-12)
    target_row = np.ones(N)
    target_col = np.ones(K) * (N / K)

    u = np.ones(N)
    v = np.ones(K)

    for _ in range(max_iter):
        u = target_row / np.maximum(P @ v, 1e-12)
        v = target_col / np.maximum(P.T @ u, 1e-12)
        balanced = u[:, None] * P * v[None, :]
        row_err = np.max(np.abs(balanced.sum(axis=1) - target_row))
        col_err = np.max(np.abs(balanced.sum(axis=0) - target_col))
        if max(row_err, col_err) < tol:
            break

    return u[:, None] * P * v[None, :]


def copula_rank_transform(prob_matrix: np.ndarray) -> np.ndarray:
    """Converts column-wise probabilities to empirical copula ranks in [0, 1].
    
    Mathematically optimal for ROC-AUC ensembling because ROC-AUC is scale-invariant
    per column but sensitive to inter-model calibration shifts.
    """
    if prob_matrix.ndim == 1:
        n = len(prob_matrix)
        ranks = np.argsort(np.argsort(prob_matrix))
        return (ranks + 0.5) / n
    ranks = np.zeros_like(prob_matrix, dtype=float)
    n = prob_matrix.shape[0]
    for c in range(prob_matrix.shape[1]):
        col = prob_matrix[:, c]
        ranks[:, c] = (np.argsort(np.argsort(col)) + 0.5) / n
    return ranks


# ==============================================================================
# Specification Data Structures
# ==============================================================================

@dataclass(frozen=True)
class CompetitionMetricSpec:
    domain: CompetitionDomain
    official_metric: str
    direction: str  # "higher" or "lower"
    primary_data_structures: tuple[str, ...]
    optimal_algorithms: tuple[str, ...]
    invariant_rules: tuple[str, ...]


COMPETITION_METRIC_SPECS: dict[CompetitionDomain, CompetitionMetricSpec] = {
    CompetitionDomain.ARC_AGI_2: CompetitionMetricSpec(
        domain=CompetitionDomain.ARC_AGI_2,
        official_metric="Exact Match Pixel Grid Accuracy (Top-2 Attempts)",
        direction="higher",
        primary_data_structures=(
            "2D uint8 numpy arrays [H, W] (values 0-9)",
            "64-bit Zobrist Hash Transposition Tables (uint64)",
            "Poincaré Hyperbolic Coordinate Vectors (float64 in D^n)",
            "Priority Queue Heap (heapq) of DSL hypotheses",
        ),
        optimal_algorithms=(
            "Dihedral D4 Equivariant Transformation Filtering",
            "Poincaré Hyperbolic Tree Search",
            "Monadic Program Synthesis & TTT LoRA Conditioning",
            "Zobrist State Deduplication & Cycle Evasion",
        ),
        invariant_rules=(
            "Grid dimension invariance under color permutation",
            "Commutativity with D4 planar reflections and rotations",
            "Exact zero tolerance for single-pixel discrepancy",
        ),
    ),
    CompetitionDomain.ARC_AGI_3: CompetitionMetricSpec(
        domain=CompetitionDomain.ARC_AGI_3,
        official_metric="Interactive Gym Environment Solve Rate & Action Efficiency",
        direction="higher",
        primary_data_structures=(
            "Macro-Action Sequence DAGs",
            "64-bit Zobrist Novelty Archive Dict",
            "Ring Buffer for Monadic Rollback State History",
        ),
        optimal_algorithms=(
            "Go-Explore BFS with Macro-Action Compilation",
            "Soft-Affordance Oracle for Interactive State Exploration",
            "Orthogonal Escape Pulse when Cyclic Trapping is Detected",
        ),
        invariant_rules=(
            "Legal action constraints enforced via AutoHarness",
            "Reversibility checks for non-destructive exploration",
        ),
    ),
    CompetitionDomain.RSNA_KNEE: CompetitionMetricSpec(
        domain=CompetitionDomain.RSNA_KNEE,
        official_metric="Macro Column-Wise ROC-AUC (12 Findings)",
        direction="higher",
        primary_data_structures=(
            "3D MRI Volume Multi-Slice Triplet Tensors (K, 3, H, W)",
            "Contralateral Bilateral Ratio Vectors (float32)",
            "Quantile Copula Rank Arrays",
        ),
        optimal_algorithms=(
            "Copula Rank Alignment & Percentile Ranking for Multi-Model Blends",
            "Joint Space Narrowing (JSN) Monotonic Compartment Ordering",
            "Bilateral Contralateral Symmetry Calibration",
            "Windowed 3D Multi-Scale Attention (Raptor-384 + Raptor-224 + CoAtNet)",
        ),
        invariant_rules=(
            "ROC-AUC rank preservation under monotonic transformation",
            "Contralateral symmetry bounds: |P(L) - P(R)| constrained by clinical priors",
            "Compartmental JSN degradation monotonicity (lateral <= medial in varus)",
        ),
    ),
    CompetitionDomain.CASMI26: CompetitionMetricSpec(
        domain=CompetitionDomain.CASMI26,
        official_metric="Top-1 Accuracy on Tautomer-Canonical InChIKey-14",
        direction="higher",
        primary_data_structures=(
            "2048-bit Morgan Fingerprints ECFP4 (uint64[32] bitsets)",
            "Molecular Fragment Cleavage DAGs",
            "Tautomer Canonicalized InChIKey-14 Hash Table",
        ),
        optimal_algorithms=(
            "Tandem Sub-Graph Mass Conservation Filter (|m_pre - (m_frag + m_loss)| <= 10 ppm)",
            "RDKit TautomerCanonicalizer Standardization",
            "MetFrag In-Silico Parsimonious Bond Cleavage Reranking",
            "PubChem Candidate Pool Expansion + LightGBM LambdaRank",
        ),
        invariant_rules=(
            "Precursor mass balance conservation in MS/MS spectra",
            "Tautomer invariance: different tautomers must resolve to identical InChIKey skeleton",
        ),
    ),
    CompetitionDomain.NAME_THAT_LLM: CompetitionMetricSpec(
        domain=CompetitionDomain.NAME_THAT_LLM,
        official_metric="Balanced Accuracy Score across 18 Generative LLM Classes",
        direction="higher",
        primary_data_structures=(
            "Scipy CSR Sparse Matrices for Character & Word N-Grams",
            "Closed-Class Function Word Frequency Vectors",
            "Markov Character Transition Matrices (128x128 float64)",
            "Float64 Probability Matrices for Sinkhorn Balancing",
        ),
        optimal_algorithms=(
            "Sinkhorn-Knopp Test-Time Uniform Marginal Balancing (P(Y=k) = 1/18)",
            "Transductive Prompt-Centering (x_style = x - mu_prompt)",
            "Morphological Markov Bigram/Trigram Transition Estimation",
            "LinearSVC + HistGradientBoosting Blending with Grouped 5-Fold CV on prompt_id",
        ),
        invariant_rules=(
            "Probabilities must sum strictly to 1.0 across 18 classes",
            "Test-time uniform marginal expectation: sum_i P[i, k] = N / 18",
            "Prompt leakage avoidance: Train and Validation sets strictly partitioned by prompt_id",
        ),
    ),
    CompetitionDomain.GEMMA_4_DEV_AGENT: CompetitionMetricSpec(
        domain=CompetitionDomain.GEMMA_4_DEV_AGENT,
        official_metric="Unit Test Suite Pass Rate / SWE-bench Resolution",
        direction="higher",
        primary_data_structures=(
            "Unified Diff AST Hunks",
            "Test Runner Execution Traces",
            "Isolated Container Sandboxes",
        ),
        optimal_algorithms=(
            "AST Syntax Verifier & Bound-Checked Patch Synthesis",
            "Multi-Turn Error Reflection Loop (Patch -> Run Tests -> Inspect -> Self-Repair)",
            "Context-Budgeted QAT Inference with Paced Editing",
        ),
        invariant_rules=(
            "Zero hallucinated file paths outside repository index",
            "Clean AST parsing: no syntax error allowed to reach submission bundle",
        ),
    ),
    CompetitionDomain.NFL_BDB_2027: CompetitionMetricSpec(
        domain=CompetitionDomain.NFL_BDB_2027,
        official_metric="Quick Pressure Rate (<2.5s) Prediction (Brier Score / ROC-AUC)",
        direction="higher",
        primary_data_structures=(
            "Spatial-Temporal Player Tracking Tables (x, y, s, a, dir, o)",
            "Voronoi Spatial Tessellation Polygons (scipy.spatial)",
            "Savitzky-Golay Smoothed Kinematic Acceleration Vectors",
        ),
        optimal_algorithms=(
            "Closing Acceleration Invariant (d^2x/dt^2 towards QB at t=0.5s)",
            "Voronoi Field Control Area Integration",
            "Time-to-Closest-Approach (TCA) Kinematic Extrapolation",
        ),
        invariant_rules=(
            "Temporal causal boundary: zero leakage of tracking data after t=0.5s or throw event",
            "Physical acceleration ceiling: a <= a_max_human",
        ),
    ),
}


def get_metric_spec(domain: str | CompetitionDomain) -> CompetitionMetricSpec:
    """Retrieves formal metric specification for any active competition."""
    if isinstance(domain, str):
        try:
            dom = CompetitionDomain(domain)
        except ValueError:
            raise KeyError(f"Competition '{domain}' not in active metric catalog.")
    else:
        dom = domain
    return COMPETITION_METRIC_SPECS[dom]
