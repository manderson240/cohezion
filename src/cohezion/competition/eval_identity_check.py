"""Check if any eval tasks are solvable by identity alone."""

from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import arc_solver
from arc_solver import grids_equal


root = Path("/home/mike-anderson/dev/cohezion")
with open(root / "data/arc-agi-2/arc-agi_evaluation_challenges.json") as f:
    challenges = json.load(f)

identity = arc_solver.identity
found = 0

for task_id, task in list(challenges.items())[:120]:
    if all(
        grids_equal(identity(arc_solver.deepcopy_grid(ex["input"])), ex["output"])
        for ex in task["train"]
    ):
        found += 1
        print(f"IDENTITY SOLVES: {task_id}")

print(f"\nIdentity solves {found}/120 eval tasks")
