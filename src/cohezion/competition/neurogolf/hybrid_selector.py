"""NeuroGolf hybrid: tiny neural program selector + symbolic execution.

Use the 73K conv net to encode input grid, then a tiny classifier
predicts which primitive programs to try. Executes them symbolically.
This should combine neural pattern recognition with compositional reasoning.

Uses our existing arc_solver.py primitives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


# Add arc_solver to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from arc_solver import apply_program, get_all_ops, grids_equal


PRIMITIVES = [name for name, _ in get_all_ops([])]
print(f"Primitives: {len(PRIMITIVES)}: {PRIMITIVES}")


class GridEncoder(nn.Module):
    """Encode grid to fixed-size vector."""

    def __init__(self, colors: int = 10, hidden: int = 32):
        super().__init__()
        self.embed = nn.Embedding(colors, hidden)
        self.conv1 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.embed(x).permute(0, 3, 1, 2)
        h = F.relu(self.conv1(h))
        h = F.relu(self.conv2(h))
        h = self.pool(h).squeeze(-1).squeeze(-1)
        return h  # (B, hidden)


class ProgramSelector(nn.Module):
    """Predict which primitives to try, given encoded grid."""

    def __init__(self, grid_hidden: int = 32, n_primitives: int = 23):
        super().__init__()
        self.encoder = GridEncoder(hidden=grid_hidden)
        self.classifier = nn.Sequential(
            nn.Linear(grid_hidden, 64),
            nn.ReLU(),
            nn.Linear(64, n_primitives),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.encoder(x)
        return self.classifier(emb)  # logits over primitives

    def count_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


def pad_grid(grid: list, size: int = 30) -> torch.Tensor:
    h = len(grid)
    w = len(grid[0]) if grid else 0
    t = torch.zeros(size, size, dtype=torch.long)
    if h > size:
        h = size
    if w > size:
        w = size
    for i in range(h):
        for j in range(w):
            t[i, j] = grid[i][j]
    return t


def grids_equal(a, b) -> bool:
    if len(a) != len(b):
        return False
    return all(row_a == row_b for row_a, row_b in zip(a, b))


if __name__ == "__main__":
    selector = ProgramSelector(grid_hidden=32, n_primitives=len(PRIMITIVES))
    print(f"Selector params: {selector.count_params():,}")

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    # Very rough: for each task, encode first train input, predict top-3 primitives,
    # try them on test input
    task_ids = list(challenges.keys())[:100]
    solved = 0
    for i, task_id in enumerate(task_ids):
        task = challenges[task_id]
        test_input = task["test"][0]["input"]

        # Encode first training input
        train_inp = pad_grid(task["train"][0]["input"]).unsqueeze(0)
        with torch.no_grad():
            scores = selector(train_inp).squeeze(0)
            top_prims = scores.argsort(descending=True)[:3].tolist()

        # Try top-3 primitives
        for pidx in top_prims:
            pname = PRIMITIVES[pidx]
            try:
                # Single primitive program
                ops = get_all_ops(task["train"])
                op_map = {name: fn for name, fn in ops}
                if pname not in op_map:
                    continue
                pred = apply_program(test_input, [op_map[pname]])
                sol = solutions.get(task_id, [])
                if pred and sol and grids_equal(pred, sol[0]):
                    solved += 1
                    break
            except Exception:
                continue

        if (i + 1) % 20 == 0:
            print(f"Progress: {i + 1}/{len(task_ids)} — solved {solved}")

    acc = solved / len(task_ids) * 100
    print(f"\nSolved {solved}/{len(task_ids)} = {acc:.1f}%")
    print(f"METRIC eval_accuracy={acc:.1f}")
