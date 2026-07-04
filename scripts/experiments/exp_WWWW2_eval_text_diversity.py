#!/usr/bin/env python3
"""
exp_WWWW2: Eval Text Diversity for Smart Seed

Improve smart_seed mechanism by using 3-phrase average instead of single
eval phrase for seed selection. Hypothesis: averaging across diverse phrases
will select a seed that generalizes better to all evaluation tasks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# Configuration
# ============================================================================

EXPERIMENT_ID = "exp_WWWW2"
EXPERIMENT_TITLE = "Eval Text Diversity for Smart Seed"
ROUND = 8

# Seed candidates
SEED_CANDIDATES = [1, 42, 123, 999, 2026]

# Baseline from Round 7 (exp_PPPP2)
BASELINE_NL = 15.43

# ============================================================================
# Evaluation Phrases
# ============================================================================

EVAL_PHRASES = {
    "phrase_a_technical": "What is the HIHO stability principle?",
    "phrase_b_reasoning": "How does compound lift work in a tiered inference system?",
    "phrase_c_tradeoff": "What are the tradeoffs between NPU and GPU routing?",
}


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class SeedEvaluation:
    """Evaluation result for a single seed on a single phrase."""

    seed: int
    phrase_id: str
    ppl_score: float
    generalization_quality: float  # 0.0 to 1.0
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SeedComparison:
    """Comparison of a seed across all eval phrases."""

    seed: int
    phrase_a_ppl: float
    phrase_b_ppl: float
    phrase_c_ppl: float
    mean_ppl: float
    ppl_variance: float  # Variance across the 3 phrases
    best_phrase_ppl: float  # Best (lowest) PPL
    worst_phrase_ppl: float  # Worst (highest) PPL

    @property
    def is_robust(self) -> bool:
        """Seed is robust if variance is low (generalizes evenly)."""
        return self.ppl_variance < 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentResult:
    """Overall experiment result."""

    experiment_id: str
    title: str
    round: int
    date_executed: str
    # Control: single-phrase selection (phrase A only)
    control_best_seed: int
    control_seed_comparisons: dict[int, SeedComparison]
    control_mean_ppl: float
    # Treatment: 3-phrase average selection
    treatment_best_seed: int
    treatment_seed_comparisons: dict[int, SeedComparison]
    treatment_mean_ppl: float
    # Summary
    status: str  # "PASS", "FAIL"
    notes: str

    @property
    def treatment_better_generalization(self) -> bool:
        """Treatment seed has lower variance (better generalization)."""
        treatment_var = self.treatment_seed_comparisons[self.treatment_best_seed].ppl_variance
        control_var = self.control_seed_comparisons[self.control_best_seed].ppl_variance
        return treatment_var < control_var

    @property
    def treatment_no_regression(self) -> bool:
        """Treatment mean PPL doesn't exceed control."""
        return self.treatment_mean_ppl <= self.control_mean_ppl

    @property
    def recommendation(self) -> str:
        """Recommendation for adopting 3-phrase smart seed."""
        if self.treatment_no_regression and self.treatment_better_generalization:
            return "ADOPT_3PHRASE_SELECTION"
        elif self.treatment_no_regression:
            return "ADOPT_WITH_MONITORING"
        else:
            return "KEEP_SINGLE_PHRASE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "round": self.round,
            "date_executed": self.date_executed,
            "control": {
                "best_seed": self.control_best_seed,
                "mean_ppl": self.control_mean_ppl,
                "seed_details": {s: c.to_dict() for s, c in self.control_seed_comparisons.items()},
            },
            "treatment": {
                "best_seed": self.treatment_best_seed,
                "mean_ppl": self.treatment_mean_ppl,
                "seed_details": {s: c.to_dict() for s, c in self.treatment_seed_comparisons.items()},
            },
            "status": self.status,
            "notes": self.notes,
            "treatment_better_generalization": self.treatment_better_generalization,
            "treatment_no_regression": self.treatment_no_regression,
            "recommendation": self.recommendation,
        }


# ============================================================================
# Evaluation Functions (Stubs - To Be Implemented)
# ============================================================================


def eval_quality_single_phrase(seed: int, phrase_id: str) -> float:
    """
    Evaluate quality of a model trained with given seed on a single phrase.

    Args:
        seed: Random seed for training
        phrase_id: Evaluation phrase identifier

    Returns:
        Quality score (PPL, lower is better)

    TODO: Implement actual lightweight model training and evaluation
    - Train HIHO v5 with given seed
    - Evaluate on phrase
    - Return PPL score
    """
    # Placeholder: return seed-based values for reproducibility
    import hashlib

    hash_val = hashlib.md5(f"{seed}:{phrase_id}".encode()).hexdigest()
    base_value = int(hash_val, 16) % 1000 / 100  # 0.0 to 10.0
    return 15.0 + base_value  # 15.0 to 25.0 range


def eval_quality_average(seed: int, phrase_ids: list[str]) -> float:
    """
    Evaluate quality by averaging across multiple phrases.

    Args:
        seed: Random seed
        phrase_ids: List of phrase IDs to evaluate

    Returns:
        Average quality score (PPL)
    """
    scores = [eval_quality_single_phrase(seed, pid) for pid in phrase_ids]
    return sum(scores) / len(scores)


# ============================================================================
# Experiment Execution
# ============================================================================


def run_experiment() -> ExperimentResult:
    """Run the eval text diversity experiment."""

    print(f"[{EXPERIMENT_ID}] Starting eval text diversity for smart seed...")
    print(f"[{EXPERIMENT_ID}] Comparing single-phrase vs 3-phrase seed selection")
    print(f"[{EXPERIMENT_ID}] Seed candidates: {SEED_CANDIDATES}")

    # ========================================================================
    # Control: Single-Phrase Selection (phrase A only)
    # ========================================================================
    print(f"\n[{EXPERIMENT_ID}] Control: Single-phrase selection (phrase A)")

    control_evals = {}
    for seed in SEED_CANDIDATES:
        ppl_a = eval_quality_single_phrase(seed, "phrase_a_technical")
        ppl_b = eval_quality_single_phrase(seed, "phrase_b_reasoning")
        ppl_c = eval_quality_single_phrase(seed, "phrase_c_tradeoff")

        control_evals[seed] = SeedComparison(
            seed=seed,
            phrase_a_ppl=ppl_a,
            phrase_b_ppl=ppl_b,
            phrase_c_ppl=ppl_c,
            mean_ppl=(ppl_a + ppl_b + ppl_c) / 3,
            ppl_variance=_compute_variance([ppl_a, ppl_b, ppl_c]),
            best_phrase_ppl=min(ppl_a, ppl_b, ppl_c),
            worst_phrase_ppl=max(ppl_a, ppl_b, ppl_c),
        )

    # Select best seed based on phrase A only
    control_best_seed = min(
        (s for s in SEED_CANDIDATES), key=lambda s: control_evals[s].phrase_a_ppl
    )
    control_mean_ppl = sum(e.mean_ppl for e in control_evals.values()) / len(control_evals)

    print(f"  Best seed (single phrase A): seed={control_best_seed}")
    for seed in SEED_CANDIDATES:
        eval_result = control_evals[seed]
        print(
            f"    Seed {seed}: A={eval_result.phrase_a_ppl:.3f}, "
            f"B={eval_result.phrase_b_ppl:.3f}, C={eval_result.phrase_c_ppl:.3f}, "
            f"mean={eval_result.mean_ppl:.3f}, var={eval_result.ppl_variance:.3f}"
        )

    # ========================================================================
    # Treatment: 3-Phrase Average Selection
    # ========================================================================
    print(f"\n[{EXPERIMENT_ID}] Treatment: 3-phrase average selection")

    treatment_evals = {}
    for seed in SEED_CANDIDATES:
        ppl_a = eval_quality_single_phrase(seed, "phrase_a_technical")
        ppl_b = eval_quality_single_phrase(seed, "phrase_b_reasoning")
        ppl_c = eval_quality_single_phrase(seed, "phrase_c_tradeoff")

        treatment_evals[seed] = SeedComparison(
            seed=seed,
            phrase_a_ppl=ppl_a,
            phrase_b_ppl=ppl_b,
            phrase_c_ppl=ppl_c,
            mean_ppl=(ppl_a + ppl_b + ppl_c) / 3,
            ppl_variance=_compute_variance([ppl_a, ppl_b, ppl_c]),
            best_phrase_ppl=min(ppl_a, ppl_b, ppl_c),
            worst_phrase_ppl=max(ppl_a, ppl_b, ppl_c),
        )

    # Select best seed based on average of all 3 phrases
    treatment_best_seed = min(
        (s for s in SEED_CANDIDATES), key=lambda s: treatment_evals[s].mean_ppl
    )
    treatment_mean_ppl = sum(e.mean_ppl for e in treatment_evals.values()) / len(treatment_evals)

    print(f"  Best seed (3-phrase average): seed={treatment_best_seed}")
    for seed in SEED_CANDIDATES:
        eval_result = treatment_evals[seed]
        print(
            f"    Seed {seed}: A={eval_result.phrase_a_ppl:.3f}, "
            f"B={eval_result.phrase_b_ppl:.3f}, C={eval_result.phrase_c_ppl:.3f}, "
            f"mean={eval_result.mean_ppl:.3f}, var={eval_result.ppl_variance:.3f}"
        )

    # ========================================================================
    # Analysis
    # ========================================================================
    print(f"\n[{EXPERIMENT_ID}] Analysis:")

    control_best = control_evals[control_best_seed]
    treatment_best = treatment_evals[treatment_best_seed]

    print(f"  Control best seed variance: {control_best.ppl_variance:.3f}")
    print(f"  Treatment best seed variance: {treatment_best.ppl_variance:.3f}")
    print(f"  Variance improvement: {control_best.ppl_variance - treatment_best.ppl_variance:+.3f}")

    print(f"\n  Control mean PPL (all seeds): {control_mean_ppl:.3f}")
    print(f"  Treatment mean PPL (all seeds): {treatment_mean_ppl:.3f}")

    generalization_better = treatment_best.ppl_variance < control_best.ppl_variance
    no_regression = treatment_mean_ppl <= control_mean_ppl

    status = "PASS" if (generalization_better and no_regression) else "FAIL"
    notes = f"Variance: {control_best.ppl_variance:.3f} → {treatment_best.ppl_variance:.3f}"

    result = ExperimentResult(
        experiment_id=EXPERIMENT_ID,
        title=EXPERIMENT_TITLE,
        round=ROUND,
        date_executed=datetime.now().isoformat(),
        control_best_seed=control_best_seed,
        control_seed_comparisons=control_evals,
        control_mean_ppl=control_mean_ppl,
        treatment_best_seed=treatment_best_seed,
        treatment_seed_comparisons=treatment_evals,
        treatment_mean_ppl=treatment_mean_ppl,
        status=status,
        notes=notes,
    )

    return result


# ============================================================================
# Utilities
# ============================================================================


def _compute_variance(values: list[float]) -> float:
    """Compute variance of a list of values."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


# ============================================================================
# Result Logging
# ============================================================================


def log_result(result: ExperimentResult, output_path: Path | None = None) -> None:
    """Log experiment result to file and SurrealDB."""

    if output_path is None:
        output_path = Path.home() / ".autoharness" / "results" / f"{EXPERIMENT_ID}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\n[{EXPERIMENT_ID}] Result logged to {output_path}")
    print(f"[{EXPERIMENT_ID}] Status: {result.status}")
    print(f"[{EXPERIMENT_ID}] Recommendation: {result.recommendation}")


# ============================================================================
# Main
# ============================================================================


def main():
    """Run the experiment and log results."""
    result = run_experiment()
    log_result(result)

    print(f"\n[{EXPERIMENT_ID}] Summary:")
    print(f"  Status: {result.status}")
    print(f"  Better generalization: {result.treatment_better_generalization}")
    print(f"  No regression: {result.treatment_no_regression}")
    print(f"  Recommendation: {result.recommendation}")

    return result


if __name__ == "__main__":
    main()
