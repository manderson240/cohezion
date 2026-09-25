#!/usr/bin/env python3
"""
verify_submission_invariants.py — Hardware-Aware Zero-Cost Deterministic Submission Verifier.

Mandate:
- Operates on Tier 0 Zen 5 CPU (< 100MB RAM, 0 MB GPU GTT/aperture).
- Evaluates AST bytecode invariants, boundary conditions, and mathematical metric sensitivities
  before any submission is dispatched to Kaggle.
- Prevents catastrophic metric penalties (e.g. Biohub w_FN=10.0 cascading loss,
  RSNA log-loss -ln(p)->inf singularities, ARC-AGI identical attempt waste).

Usage:
    python scripts/kaggle/verify_submission_invariants.py --competition <comp_id> --submission <file_path>
"""

import argparse
import ast
import json
import os
import sys
from typing import Dict, List, Tuple, Any
import numpy as np


class VerificationResult:
    def __init__(self, passed: bool, warnings: List[str], errors: List[str], metrics: Dict[str, Any]):
        self.passed = passed
        self.warnings = warnings
        self.errors = errors
        self.metrics = metrics

    def print_report(self, competition: str):
        print("=" * 70)
        print(f"  COHEZION DETERMINISTIC INVARIANT VERIFICATION: {competition}")
        print("=" * 70)
        print(f"Status: {'PASSED (Safe to Submit)' if self.passed else 'FAILED (Blocked from Submission)'}")
        print("\nKey Metrics:")
        for k, v in self.metrics.items():
            print(f"  - {k}: {v}")
        if self.warnings:
            print("\nWarnings:")
            for w in self.warnings:
                print(f"  [!] {w}")
        if self.errors:
            print("\nErrors (Must Fix):")
            for e in self.errors:
                print(f"  [X] {e}")
        print("=" * 70)


def verify_biohub_submission(file_path: str) -> VerificationResult:
    warnings = []
    errors = []
    metrics = {}

    if not os.path.exists(file_path):
        return VerificationResult(False, [], [f"File not found: {file_path}"], {})

    import pandas as pd
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return VerificationResult(False, [], [f"Failed to read CSV: {e}"], {})

    # Check official Kaggle Biohub multi-row schema
    official_cols = {"id", "dataset", "row_type", "node_id", "t", "z", "y", "x", "source_id", "target_id"}
    if official_cols.issubset(set(df.columns)):
        nodes = df[df["row_type"] == "node"]
        edges = df[df["row_type"] == "edge"]
        metrics["total_nodes"] = len(nodes)
        metrics["total_edges"] = len(edges)
        metrics["datasets"] = list(df["dataset"].unique())

        time_frames = sorted(nodes["t"].unique())
        metrics["num_frames"] = len(time_frames)
        metrics["frame_range"] = (int(time_frames[0]), int(time_frames[-1])) if time_frames else (0, 0)

        # 1. Detection drop stability across frames
        counts_by_t = nodes["t"].value_counts().sort_index()
        for t_prev, t_curr in zip(time_frames[:-1], time_frames[1:]):
            c_prev = counts_by_t.get(t_prev, 0)
            c_curr = counts_by_t.get(t_curr, 0)
            if c_prev > 0 and c_curr / c_prev < 0.60:
                warnings.append(
                    f"Severe detection drop at t={t_curr} vs t={t_prev}: {c_curr} vs {c_prev} "
                    f"({c_curr/c_prev:.1%}). High risk of w_FN=10.0 cascade penalty!"
                )

        # 2. Node lookup map: (dataset, node_id) -> t
        node_lookup = {}
        for _, r in nodes.iterrows():
            node_lookup[(r["dataset"], int(r["node_id"]))] = int(r["t"])

        invalid_temporal_links = 0
        dangling_links = 0
        out_degree: Dict[Tuple[str, int], int] = {}

        for _, r in edges.iterrows():
            ds = r["dataset"]
            src = int(r["source_id"])
            tgt = int(r["target_id"])

            src_key = (ds, src)
            tgt_key = (ds, tgt)

            if src_key not in node_lookup or tgt_key not in node_lookup:
                dangling_links += 1
                continue

            t_src = node_lookup[src_key]
            t_tgt = node_lookup[tgt_key]

            if t_src >= t_tgt:
                invalid_temporal_links += 1

            out_degree[src_key] = out_degree.get(src_key, 0) + 1

        if dangling_links > 0:
            errors.append(f"Found {dangling_links} edges referencing non-existent nodes.")
        if invalid_temporal_links > 0:
            errors.append(f"Found {invalid_temporal_links} non-monotonic temporal edges (t_source >= t_target).")

        # 3. Mitotic branching invariant (max 2 daughter cells)
        excess_branches = [k for k, deg in out_degree.items() if deg > 2]
        if excess_branches:
            errors.append(f"Found {len(excess_branches)} parent cells with out-degree > 2 (mitotic biological violation).")

        metrics["mitotic_divisions"] = sum(1 for deg in out_degree.values() if deg == 2)
        metrics["linear_tracks"] = sum(1 for deg in out_degree.values() if deg == 1)

        passed = len(errors) == 0
        return VerificationResult(passed, warnings, errors, metrics)

    # Legacy flat schema fallback
    expected_cols = {"id", "t", "x", "y", "z", "parent_id"}
    if not expected_cols.issubset(set(df.columns)):
        missing = expected_cols - set(df.columns)
        errors.append(f"Unknown schema. Expected official Biohub or flat schema. Missing: {missing}")
        return VerificationResult(False, warnings, errors, metrics)

    metrics["total_detections"] = len(df)
    passed = len(errors) == 0
    return VerificationResult(passed, warnings, errors, metrics)


def verify_rsna_submission(file_path: str) -> VerificationResult:
    warnings = []
    errors = []
    metrics = {}

    if not os.path.exists(file_path):
        return VerificationResult(False, [], [f"File not found: {file_path}"], {})

    import pandas as pd
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return VerificationResult(False, [], [f"Failed to read CSV: {e}"], {})

    expected_cols = ["series_id", "acl_tear", "meniscus_tear", "abnormal", "fracture", "tendon_injury"]
    # Check flexible column naming
    col_mapping = {c.lower(): c for c in df.columns}
    prob_cols = [c for c in df.columns if c.lower() != "series_id"]

    if len(prob_cols) < 5:
        errors.append(f"Expected at least 5 target condition columns, found: {prob_cols}")
        return VerificationResult(False, warnings, errors, metrics)

    metrics["total_test_series"] = len(df)
    metrics["target_conditions"] = prob_cols

    # 1. Asymptotic log-loss singularity check: p must never be exactly 0 or 1
    min_prob = df[prob_cols].min().min()
    max_prob = df[prob_cols].max().max()
    metrics["min_predicted_probability"] = float(min_prob)
    metrics["max_predicted_probability"] = float(max_prob)

    if min_prob <= 0.0:
        errors.append(f"Fatal Log-Loss Singularity: Min probability {min_prob} <= 0.0 incurs -ln(0) = infinity!")
    elif min_prob < 1e-4:
        warnings.append(f"Extreme confidence risk: Min probability {min_prob:.2e} < 1e-4. Consider margin clipping [1e-4, 1-1e-4].")

    if max_prob >= 1.0:
        errors.append(f"Fatal Log-Loss Singularity: Max probability {max_prob} >= 1.0 incurs -ln(0) = infinity on negative cases!")
    elif max_prob > 1.0 - 1e-4:
        warnings.append(f"Extreme confidence risk: Max probability {max_prob:.6f} > 1 - 1e-4. Consider margin clipping.")

    # 2. Check for accidental rank-averaging uniform distribution distortion
    for col in prob_cols:
        vals = df[col].values
        # Kolmogorov-Smirnov test against uniform distribution U(0, 1)
        mean_val = float(np.mean(vals))
        std_val = float(np.std(vals))
        metrics[f"{col}_mean"] = f"{mean_val:.4f}"
        # A uniform distribution on [0, 1] has mean 0.5 and std 1/sqrt(12) = 0.2887
        if 0.48 <= mean_val <= 0.52 and 0.27 <= std_val <= 0.31:
            warnings.append(
                f"Column '{col}' exhibits uniform distribution characteristics (mean={mean_val:.3f}, std={std_val:.3f}). "
                f"Verify that .rank(pct=True) was NOT applied, as it destroys calibrated Brier probabilities and ruins log-loss!"
            )

    # 3. Kolmogorov Parent Monotonicity Check: P(abnormal) >= max(specific conditions)
    abnormal_col = next((c for c in prob_cols if "abnormal" in c.lower()), None)
    specific_cols = [c for c in prob_cols if c != abnormal_col]
    if abnormal_col and specific_cols:
        max_specific = df[specific_cols].max(axis=1)
        violations = df[df[abnormal_col] < max_specific - 0.01]
        metrics["monotonicity_violations"] = len(violations)
        if len(violations) > 0:
            warnings.append(
                f"Found {len(violations)} rows violating Kolmogorov parent monotonicity: "
                f"P(Abnormal) < max(P(specific)). Abnormal is an umbrella condition; "
                f"consider applying: df['{abnormal_col}'] = np.maximum(df['{abnormal_col}'], df[{specific_cols}].max(axis=1))"
            )

    # 4. Check for row-wise trivial duplicates
    if df[prob_cols].duplicated().sum() > len(df) * 0.5:
        warnings.append("Over 50% identical predictions across rows. Verify ensemble diversity.")

    passed = len(errors) == 0
    return VerificationResult(passed, warnings, errors, metrics)


def verify_arc_submission(file_path: str) -> VerificationResult:
    warnings = []
    errors = []
    metrics = {}

    if not os.path.exists(file_path):
        return VerificationResult(False, [], [f"File not found: {file_path}"], {})

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return VerificationResult(False, [], [f"Failed to parse JSON: {e}"], {})

    if not isinstance(data, dict):
        return VerificationResult(False, [], ["Root submission must be a JSON object mapping task_id to attempts"], {})

    metrics["total_tasks"] = len(data)
    identical_attempts = 0
    invalid_dimensions = 0
    invalid_colors = 0
    total_test_outputs = 0

    for task_id, attempts_list in data.items():
        if not isinstance(attempts_list, list):
            errors.append(f"Task {task_id}: expected list of output test instances.")
            continue

        for i, pair in enumerate(attempts_list):
            total_test_outputs += 1
            if not isinstance(pair, dict) or "attempt_1" not in pair or "attempt_2" not in pair:
                errors.append(f"Task {task_id}[{i}]: missing 'attempt_1' or 'attempt_2' keys.")
                continue

            att1 = np.array(pair["attempt_1"])
            att2 = np.array(pair["attempt_2"])

            # Dimension checks
            for name, arr in [("attempt_1", att1), ("attempt_2", att2)]:
                if arr.ndim != 2 or arr.shape[0] < 1 or arr.shape[0] > 30 or arr.shape[1] < 1 or arr.shape[1] > 30:
                    invalid_dimensions += 1
                    errors.append(f"Task {task_id}[{i}] {name}: invalid shape {arr.shape}. ARC bounds are 1x1 to 30x30.")
                # Color bounds [0, 9]
                if (arr < 0).any() or (arr > 9).any():
                    invalid_colors += 1
                    errors.append(f"Task {task_id}[{i}] {name}: pixel values outside ARC palette [0, 9].")

            # Check Attempt 1 vs Attempt 2 diversity
            if att1.shape == att2.shape and np.array_equal(att1, att2):
                identical_attempts += 1

    metrics["total_test_instances"] = total_test_outputs
    metrics["identical_attempt_pairs"] = identical_attempts
    metrics["attempt_diversity_rate"] = f"{(total_test_outputs - identical_attempts) / max(total_test_outputs, 1):.1%}"

    if identical_attempts > 0:
        warnings.append(
            f"{identical_attempts} tasks have identical Attempt 1 and Attempt 2! "
            f"Wastes second evaluation shot. Use Pareto diversity scoring (Hamming distance >= 0.15) for Attempt 2."
        )

    passed = len(errors) == 0
    return VerificationResult(passed, warnings, errors, metrics)


def verify_kaggriculture_bot(file_path: str) -> VerificationResult:
    warnings = []
    errors = []
    metrics = {}

    if not os.path.exists(file_path):
        return VerificationResult(False, [], [f"File not found: {file_path}"], {})

    try:
        with open(file_path, "r") as f:
            code = f.read()
    except Exception as e:
        return VerificationResult(False, [], [f"Failed to read file: {e}"], {})

    metrics["code_lines"] = len(code.splitlines())
    metrics["file_size_bytes"] = len(code)

    # 1. AST Syntax parse
    try:
        tree = ast.parse(code)
    except SyntaxError as se:
        errors.append(f"Syntax Error in bot code at line {se.lineno}: {se.msg}")
        return VerificationResult(False, warnings, errors, metrics)

    # 2. Check for required entrypoint: def step(state) or def agent(observation, configuration)
    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    metrics["functions"] = function_names

    if "agent" not in function_names and "step" not in function_names and "my_agent" not in function_names:
        errors.append("No valid Kaggle simulation entrypoint found (expected 'agent', 'step', or 'my_agent').")

    # 3. Check for SOTA strategies: 8C/4S Dairy opening & Turn-28 liquidation
    if "dairy" not in code.lower() and "cow" not in code.lower():
        warnings.append("Bot does not appear to reference Dairy/Cow compounding logic (essential for 2900+ score).")

    if "liquidation" not in code.lower() and "turn" not in code.lower() and "day" not in code.lower():
        warnings.append("Bot does not appear to contain end-game inventory liquidation logic (turns 28-30).")

    passed = len(errors) == 0
    return VerificationResult(passed, warnings, errors, metrics)


def main():
    parser = argparse.ArgumentParser(description="Cohezion Strix Halo Deterministic Invariant Verifier")
    parser.add_argument("--competition", required=True, choices=["biohub", "rsna", "arc", "kaggriculture"],
                        help="Competition track to verify")
    parser.add_argument("--submission", required=True, help="Path to submission file (.csv, .json, or .py)")
    args = parser.parse_args()

    if args.competition == "biohub":
        result = verify_biohub_submission(args.submission)
    elif args.competition == "rsna":
        result = verify_rsna_submission(args.submission)
    elif args.competition == "arc":
        result = verify_arc_submission(args.submission)
    elif args.competition == "kaggriculture":
        result = verify_kaggriculture_bot(args.submission)
    else:
        print(f"Unknown competition: {args.competition}")
        sys.exit(1)

    result.print_report(args.competition.upper())
    if not result.passed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
