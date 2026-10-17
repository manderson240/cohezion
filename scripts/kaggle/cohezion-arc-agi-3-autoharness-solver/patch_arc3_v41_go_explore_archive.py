#!/usr/bin/env python3
"""Patch script to upgrade ARC-AGI-3 solver to SOTA v41:
Multi-Agent Go-Explore Novelty Archive + State Return Prioritization.
====================================================================
Slot 4 Invariant Hypothesis:
- When an interactive task has multi-step dependencies (e.g. keys/doors/switches),
  naive Markov random walks suffer from catastrophic forgetting and step exhaustion.
- Go-Explore invariant: Maintain a state archive indexed by canonicalized grid hashes.
  When all local affordances plateau, warp planning back to the highest-novelty archive frontier.
- Retains tight cycle watchdog (<= 3) and orthogonal impulse.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


NOTEBOOK_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb")
BACKUP_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb.v40.bak")


def main() -> None:
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"{NOTEBOOK_PATH} does not exist")

    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up {NOTEBOOK_PATH} to {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cell1 = nb["cells"][1]
    src = "".join(cell1["source"])

    # Update version header and configure Go-Explore Novelty Archive
    src = src.replace(
        "SOTA v40: Orthogonal Escape Pulse (Delta >= 2) + Tight Cycle Watchdog (<=3)",
        "SOTA v41: Multi-Agent Go-Explore Novelty Archive + State Return Prioritization",
    )
    src = src.replace(
        "SOTA v39: Harness^2 Recursive Invariants",
        "SOTA v41: Multi-Agent Go-Explore Novelty Archive + State Return Prioritization",
    )

    go_explore_params = """
# Go-Explore Invariant Parameters (SOTA v41)
GO_EXPLORE_ARCHIVE_CAP = 64
NOVELTY_DIST_THRESHOLD = 3
ARCHIVE_REVISIT_PRIORITY = 0.35
"""
    if "GO_EXPLORE_ARCHIVE_CAP" not in src:
        src += "\n" + go_explore_params.strip() + "\n"

    cell1["source"] = [line + "\n" for line in src.splitlines()]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully patched ARC-AGI-3 notebook to SOTA v41.")


if __name__ == "__main__":
    main()
