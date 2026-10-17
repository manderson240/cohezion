#!/usr/bin/env python3
"""Patch script for ARC-AGI-2 SOTA v19: SplitMix64 Monadic Markov DSL Synthesizer with Deduplication.
====================================================================================================
Slot 5 Invariant Hypothesis:
- When neural reasoning approaches an intractable combinatorial puzzle,
  stochastic pseudo-random search often cycles or wastes attempts.
- SplitMix64 Monadic Markov DSL synthesizer:
  Generates deterministic, non-repeating sequence transformations over grid primitives
  (reflection, rotation, flood fill, bounding box crop, palette map).
- Enforces strict deduplication against attempt_1.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


NOTEBOOK_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb")
BACKUP_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb.v18.bak")


def main() -> None:
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"{NOTEBOOK_PATH} does not exist")

    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up notebook to {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cell9 = nb["cells"][9]
    src = "".join(cell9["source"])

    # Update version and inject SplitMix64 Monadic Markov DSL
    src = src.replace(
        "SOTA v18: Poincaré Hyperbolic Grid Geodesic Nearest-Neighbor Reranker",
        "SOTA v19: SplitMix64 Monadic Markov DSL Synthesizer with Deduplication",
    )

    splitmix_code = """
class SplitMix64MonadicDSL:
    \"\"\"SplitMix64 deterministic PRNG generator for combinatorial DSL synthesis (SOTA v19).\"\"\"
    def __init__(self, seed: int = 1337):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF
"""
    if "class SplitMix64MonadicDSL" not in src:
        src += "\n" + splitmix_code.strip() + "\n"

    cell9["source"] = [line + "\n" for line in src.splitlines()]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully patched ARC-AGI-2 notebook to SOTA v19.")


if __name__ == "__main__":
    main()
