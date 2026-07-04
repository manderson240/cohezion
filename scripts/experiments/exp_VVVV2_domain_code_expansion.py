#!/usr/bin/env python3
"""
exp_VVVV2: Domain-Relevant Code Expansion

Expand code corpus from 40 to 60 snippets by adding 20 domain-relevant
examples from src/cohezion/inference/ and src/cohezion/compound/.

Round 7 finding: Domain relevance > diversity — byte-level models rely
on byte n-gram overlap with domain text.
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

EXPERIMENT_ID = "exp_VVVV2"
EXPERIMENT_TITLE = "Domain-Relevant Code Expansion"
ROUND = 8

# Baseline from Round 7 (exp_PPPP2)
BASELINE_NL = 15.43
NL_THRESHOLD = 15.5  # Success criterion: maintain NL <= this
BYTE_OVERLAP_TARGET = 0.85  # 85% overlap with existing snippets

# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class CodeSnippet:
    """Single code snippet extracted from codebase."""

    source_file: str
    line_range: tuple[int, int]
    code: str
    snippet_type: str  # "pattern_matching", "routing_logic", "async_execution", etc.
    byte_count: int
    token_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": f"{self.source_file}:{self.line_range[0]}-{self.line_range[1]}",
            "type": self.snippet_type,
            "bytes": self.byte_count,
            "tokens": self.token_count,
            "code_lines": len(self.code.split("\n")),
        }


@dataclass
class CorpusAnalysis:
    """Analysis of code corpus byte statistics."""

    num_snippets: int
    total_bytes: int
    mean_bytes: float
    median_bytes: float
    min_bytes: int
    max_bytes: int
    token_estimate: int  # Rough estimate: bytes / 4
    byte_overlap_with_existing: float  # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingMetrics:
    """Metrics from a HIHO v5 training run."""

    model_id: str
    num_code_snippets: int
    ppl_test: float
    ppl_train: float
    byte_accuracy: float  # Accuracy on byte-level predictions
    training_loss: float
    convergence_steps: int
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentResult:
    """Overall experiment result."""

    experiment_id: str
    title: str
    round: int
    date_executed: str
    corpus_baseline: CorpusAnalysis
    corpus_expanded: CorpusAnalysis
    metrics_baseline: TrainingMetrics
    metrics_expanded: TrainingMetrics
    status: str  # "PASS", "FAIL"
    notes: str

    @property
    def nl_maintained(self) -> bool:
        """Check if NL is maintained within threshold."""
        return self.metrics_expanded.ppl_test <= NL_THRESHOLD

    @property
    def byte_overlap_good(self) -> bool:
        """Check if byte overlap is sufficient."""
        return self.corpus_expanded.byte_overlap_with_existing >= BYTE_OVERLAP_TARGET

    @property
    def recommendation(self) -> str:
        """Recommendation for adopting expanded corpus."""
        if self.nl_maintained and self.byte_overlap_good:
            return "ADOPT_NEW_CORPUS"
        elif self.nl_maintained:
            return "ADOPT_WITH_CAUTION"
        else:
            return "REVERT_TO_BASELINE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "round": self.round,
            "date_executed": self.date_executed,
            "corpus_baseline": self.corpus_baseline.to_dict(),
            "corpus_expanded": self.corpus_expanded.to_dict(),
            "metrics_baseline": self.metrics_baseline.to_dict(),
            "metrics_expanded": self.metrics_expanded.to_dict(),
            "status": self.status,
            "notes": self.notes,
            "nl_maintained": self.nl_maintained,
            "byte_overlap_good": self.byte_overlap_good,
            "recommendation": self.recommendation,
        }


# ============================================================================
# Code Mining Functions (Stubs - To Be Implemented)
# ============================================================================


def extract_snippets_from_file(filepath: Path, num_snippets: int = 5) -> list[CodeSnippet]:
    """
    Extract domain-relevant code snippets from a file.

    Args:
        filepath: Path to Python file to mine
        num_snippets: Target number of snippets to extract

    Returns:
        List of CodeSnippet objects

    TODO: Implement actual snippet extraction
    - Parse Python file
    - Identify high-frequency patterns
    - Extract 8-32 line snippets
    - Compute byte statistics
    """
    # Placeholder
    return []


def analyze_corpus_statistics(snippets: list[CodeSnippet]) -> CorpusAnalysis:
    """Analyze byte statistics of code corpus."""

    if not snippets:
        return CorpusAnalysis(
            num_snippets=0,
            total_bytes=0,
            mean_bytes=0.0,
            median_bytes=0,
            min_bytes=0,
            max_bytes=0,
            token_estimate=0,
            byte_overlap_with_existing=0.0,
        )

    bytes_list = [s.byte_count for s in snippets]
    bytes_list.sort()

    total_bytes = sum(bytes_list)
    mean_bytes = total_bytes / len(bytes_list)
    median_bytes = bytes_list[len(bytes_list) // 2]

    # TODO: Compute actual byte overlap with existing 40 snippets
    # This requires comparing n-gram distributions
    byte_overlap = 0.87  # Stub

    return CorpusAnalysis(
        num_snippets=len(snippets),
        total_bytes=total_bytes,
        mean_bytes=mean_bytes,
        median_bytes=median_bytes,
        min_bytes=min(bytes_list),
        max_bytes=max(bytes_list),
        token_estimate=total_bytes // 4,
        byte_overlap_with_existing=byte_overlap,
    )


def train_hiho_gate(
    snippets: list[CodeSnippet], num_code: int = 40, model_id: str = "hiho_v5"
) -> TrainingMetrics:
    """
    Train HIHO v5 gate with given code corpus.

    Args:
        snippets: Code snippets for training
        num_code: Number of code snippets to use (40 for baseline, 60 for expanded)
        model_id: Model identifier

    Returns:
        TrainingMetrics from training run

    TODO: Implement actual HIHO v5 training
    - Prepare dataset with n_code=num_code
    - Train with standard config (320 steps, lr=5e-4, SGDR, smart_seed)
    - Measure PPL on test set
    """
    # Placeholder
    return TrainingMetrics(
        model_id=model_id,
        num_code_snippets=num_code,
        ppl_test=15.43,  # Stub: will be actual measured value
        ppl_train=14.92,  # Stub
        byte_accuracy=0.87,  # Stub
        training_loss=0.0342,  # Stub
        convergence_steps=280,  # Stub
        timestamp=datetime.now().isoformat(),
    )


# ============================================================================
# Experiment Execution
# ============================================================================


def run_experiment() -> ExperimentResult:
    """Run the domain code expansion experiment."""

    print(f"[{EXPERIMENT_ID}] Starting domain-relevant code expansion...")
    print(f"[{EXPERIMENT_ID}] Target: expand from 40 to 60 code snippets")

    # Phase 1: Extract new snippets from domain modules
    print(f"[{EXPERIMENT_ID}] Phase 1: Mining domain-relevant code...")

    candidate_modules = [
        Path("/home/mike-anderson/dev/cohezion/src/cohezion/inference/task_classifier.py"),
        Path("/home/mike-anderson/dev/cohezion/src/cohezion/inference/cost_aware_router.py"),
        Path("/home/mike-anderson/dev/cohezion/src/cohezion/inference/triune_orchestrator.py"),
        Path("/home/mike-anderson/dev/cohezion/src/cohezion/compound/executor.py"),
        Path("/home/mike-anderson/dev/cohezion/src/cohezion/compound/journey_tracker.py"),
        Path("/home/mike-anderson/dev/cohezion/src/cohezion/compound/skill_refiner.py"),
    ]

    new_snippets = []
    snippets_per_module = 20 // len(candidate_modules)

    for module_path in candidate_modules:
        if module_path.exists():
            extracted = extract_snippets_from_file(module_path, num_snippets=snippets_per_module)
            new_snippets.extend(extracted)
            print(f"  Extracted {len(extracted)} snippets from {module_path.name}")
        else:
            print(f"  Module not found: {module_path.name}")

    if len(new_snippets) < 20:
        print(
            f"[{EXPERIMENT_ID}] WARNING: Only extracted {len(new_snippets)} snippets, "
            f"target is 20"
        )

    # Phase 2: Analyze corpus statistics
    print(f"[{EXPERIMENT_ID}] Phase 2: Analyzing corpus statistics...")

    corpus_expanded = analyze_corpus_statistics(new_snippets)
    print(f"  Expanded corpus: {corpus_expanded.num_snippets} snippets, "
          f"{corpus_expanded.total_bytes} bytes")
    print(f"  Byte overlap with existing: {corpus_expanded.byte_overlap_with_existing:.1%}")

    # Phase 3: Train HIHO v5 with expanded corpus
    print(f"[{EXPERIMENT_ID}] Phase 3: Training HIHO v5 with expanded corpus...")

    # Baseline training (for comparison)
    baseline_metrics = train_hiho_gate([], num_code=40, model_id="hiho_v5_baseline")
    print(f"  Baseline (40 snippets): PPL={baseline_metrics.ppl_test:.3f}")

    # Expanded training
    expanded_metrics = train_hiho_gate(new_snippets, num_code=60, model_id="hiho_v5_expanded")
    print(f"  Expanded (60 snippets): PPL={expanded_metrics.ppl_test:.3f}")

    # Phase 4: Evaluate results
    print(f"[{EXPERIMENT_ID}] Phase 4: Evaluating results...")

    nl_ok = expanded_metrics.ppl_test <= NL_THRESHOLD
    overlap_ok = corpus_expanded.byte_overlap_with_existing >= BYTE_OVERLAP_TARGET

    print(f"  NL maintained: {nl_ok} (PPL={expanded_metrics.ppl_test:.3f} <= {NL_THRESHOLD})")
    print(f"  Byte overlap good: {overlap_ok} "
          f"({corpus_expanded.byte_overlap_with_existing:.1%} >= {BYTE_OVERLAP_TARGET:.1%})")

    status = "PASS" if (nl_ok and overlap_ok) else "FAIL"
    notes = f"PPL change: {expanded_metrics.ppl_test - baseline_metrics.ppl_test:+.3f}"

    result = ExperimentResult(
        experiment_id=EXPERIMENT_ID,
        title=EXPERIMENT_TITLE,
        round=ROUND,
        date_executed=datetime.now().isoformat(),
        corpus_baseline=analyze_corpus_statistics([]),  # Placeholder
        corpus_expanded=corpus_expanded,
        metrics_baseline=baseline_metrics,
        metrics_expanded=expanded_metrics,
        status=status,
        notes=notes,
    )

    return result


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

    print(f"[{EXPERIMENT_ID}] Result logged to {output_path}")
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
    print(f"  NL maintained: {result.nl_maintained}")
    print(f"  Byte overlap good: {result.byte_overlap_good}")
    print(f"  Recommendation: {result.recommendation}")

    return result


if __name__ == "__main__":
    main()
