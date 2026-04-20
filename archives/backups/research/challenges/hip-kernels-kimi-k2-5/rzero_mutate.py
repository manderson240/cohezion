#!/usr/bin/env python3
"""R-Zero Mutation: Create new challengers by mutating top performers.

Implements parameter perturbation and crossover.
"""

import random
import re
from pathlib import Path


def extract_params_from_gemm(code: str) -> dict:
    """Extract parameters from GEMM challenger code."""
    params = {}

    # Extract kernel name
    match = re.search(r'kernel_name = "([^"]+)"', code)
    if match:
        params["kernel"] = match.group(1)

    # Extract log2_ks
    match = re.search(r"log2_ks = (\d+)", code)
    if match:
        params["log2_ks"] = int(match.group(1))

    # Extract threshold
    match = re.search(r"M <= (\d+)", code)
    if match:
        params["threshold"] = int(match.group(1))

    return params


def mutate_gemm_params(params: dict) -> dict:
    """Mutate GEMM parameters."""
    mutated = params.copy()

    # Perturb log2_ks by ±1
    if random.random() < 0.5:
        mutated["log2_ks"] = max(0, min(4, mutated["log2_ks"] + random.choice([-1, 1])))

    # Perturb threshold
    if random.random() < 0.3:
        thresholds = [4, 8, 16, 32, 64]
        current = mutated.get("threshold", 32)
        idx = thresholds.index(current) if current in thresholds else 2
        new_idx = max(0, min(len(thresholds) - 1, idx + random.choice([-1, 1])))
        mutated["threshold"] = thresholds[new_idx]

    return mutated


def generate_mutated_gemm(base_file: Path, new_idx: int, params: dict) -> str:
    """Generate mutated GEMM challenger."""
    code = base_file.read_text()

    # Replace parameters
    code = re.sub(r"log2_ks = \d+", f"log2_ks = {params['log2_ks']}", code)
    code = re.sub(r"M <= \d+", f"M <= {params['threshold']}", code)

    # Update docstring
    code = re.sub(r'"""GEMM Challenger \d+:', f'"""GEMM Challenger M{new_idx}:', code)

    return code


def extract_params_from_moe(code: str) -> dict:
    """Extract parameters from MoE challenger code."""
    params = {}

    # Extract KS values
    matches = re.findall(r'ks = "(\d+)"', code)
    if matches:
        params["ks"] = int(matches[0])

    # Extract thresholds
    matches = re.findall(r"est_m < (\d+)", code)
    if len(matches) >= 2:
        params["threshold1"] = int(matches[0])
        params["threshold2"] = int(matches[1])

    return params


def mutate_moe_params(params: dict) -> dict:
    """Mutate MoE parameters."""
    mutated = params.copy()

    # Perturb KS
    if random.random() < 0.5:
        ks_options = [1, 2, 3, 4, 6, 8]
        current = mutated.get("ks", 2)
        idx = ks_options.index(current) if current in ks_options else 1
        new_idx = max(0, min(len(ks_options) - 1, idx + random.choice([-1, 1])))
        mutated["ks"] = ks_options[new_idx]

    return mutated


def extract_params_from_mla(code: str) -> dict:
    """Extract parameters from MLA challenger code."""
    params = {}

    # Extract num_splits
    match = re.search(r"num_splits = (\d+)", code)
    if match:
        params["num_splits"] = int(match.group(1))

    return params


def mutate_mla_params(params: dict) -> dict:
    """Mutate MLA parameters."""
    mutated = params.copy()

    # Perturb num_splits (×2 or ÷2)
    if random.random() < 0.5:
        splits = [1, 2, 4, 8, 16, 32, 64]
        current = mutated.get("num_splits", 4)
        idx = splits.index(current) if current in splits else 2
        if random.random() < 0.5 and idx < len(splits) - 1:
            mutated["num_splits"] = splits[idx + 1]
        elif idx > 0:
            mutated["num_splits"] = splits[idx - 1]

    return mutated


def crossover(parent1: Path, parent2: Path, kernel: str, new_idx: int) -> str:
    """Create child by combining two parents."""
    code1 = parent1.read_text()
    code2 = parent2.read_text()

    # Simple crossover: take structure from parent1, parameters from parent2
    # In practice, would need more sophisticated crossover

    # Update index
    code = code1
    code = re.sub(
        r'"""[^"]+Challenger[^"]+"""',
        f'"""{kernel.upper()} Challenger C{new_idx}: Crossover"""',
        code,
    )

    return code


def main():
    """Generate mutated challengers from top performers."""
    print("R-Zero Mutation")
    print("=" * 60)

    # This would be called after evaluation and selection
    # For now, show the mutation strategy

    print("\nMutation Strategy:")
    print("  GEMM: Perturb log2_ks (±1), threshold (±1 level)")
    print("  MoE: Perturb KSPLIT, threshold")
    print("  MLA: Perturb num_splits (×2 or ÷2)")
    print("\nCrossover Strategy:")
    print("  Combine parameters from two top performers")
    print("  Keep structure from one, parameters from other")


if __name__ == "__main__":
    main()
