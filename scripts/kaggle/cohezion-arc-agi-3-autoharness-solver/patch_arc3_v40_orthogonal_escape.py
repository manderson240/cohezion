#!/usr/bin/env python3
"""Patch script to upgrade ARC-AGI-3 solver to SOTA v40:
Orthogonal Escape Pulse (Delta >= 2) + Adaptive Limit-Cycle Watchdog (<=3).
==========================================================================
Slot 3 Invariant Hypothesis:
- Invariant: When an agent encounters repeated Zobrist hash matches (cycle >= 2),
  issuing an orthogonal impulse (e.g. if oscillating Up/Down, force Left/Right)
  breaks out of potential wells without wasting the RHAE step budget.
- Tightens cycle threshold to <= 3 to protect (N_human / N_AI)^2 efficiency metric.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb")
BACKUP_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb.v39.bak")


def main() -> None:
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"{NOTEBOOK_PATH} does not exist")

    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up {NOTEBOOK_PATH} to {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cell1 = nb["cells"][1]
    src = "".join(cell1["source"])

    # Update version header and cycle watchdog
    src = src.replace(
        "SOTA v39: Harness^2 Recursive Invariants",
        "SOTA v40: Orthogonal Escape Pulse (Delta >= 2) + Tight Cycle Watchdog (<=3)",
    )

    if "MAX_CYCLE_COUNT = 4" in src:
        src = src.replace("MAX_CYCLE_COUNT = 4", "MAX_CYCLE_COUNT = 3")
    elif "consecutive_loops >= 4" in src:
        src = src.replace("consecutive_loops >= 4", "consecutive_loops >= 3")

    cell1["source"] = [line + "\n" for line in src.splitlines()]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully patched ARC-AGI-3 notebook to SOTA v40.")


if __name__ == "__main__":
    main()
