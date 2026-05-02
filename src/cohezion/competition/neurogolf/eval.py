"""Evaluate TinyConvARCSolver on ARC training tasks."""

from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn.functional as F
from tiny_conv_arc import TinyConvARCSolver


def pad_grid(grid: list, size: int = 30) -> torch.Tensor:
    """Pad a 2D list to size x size."""
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


def grids_equal(a: list, b: list) -> bool:
    """Check equality of two grids."""
    if len(a) != len(b):
        return False
    return all(row_a == row_b for row_a, row_b in zip(a, b))


def train_on_task(model: TinyConvARCSolver, train_examples: list, steps: int = 200) -> float:
    """Quick SGD training on a single task with train examples."""
    opt = torch.optim.SGD(model.parameters(), lr=0.1)
    losses = []
    for _ in range(steps):
        total_loss = 0.0
        for ex in train_examples:
            inp = pad_grid(ex["input"]).unsqueeze(0)
            target = pad_grid(ex["output"]).unsqueeze(0)
            logits = model(inp)
            loss = F.cross_entropy(logits, target)
            total_loss += loss.item()
            opt.zero_grad()
            loss.backward()
            opt.step()
        losses.append(total_loss / len(train_examples))
    return losses[-1]


def evaluate_task(model: TinyConvARCSolver, task: dict) -> bool:
    """Test if model solves all train examples after quick training."""
    # Clone model for per-task training
    task_model = TinyConvARCSolver(hidden=16)
    task_model.load_state_dict(model.state_dict())

    train_on_task(task_model, task["train"], steps=200)

    # Verify all train examples match
    for ex in task["train"]:
        inp = pad_grid(ex["input"]).unsqueeze(0)
        target = pad_grid(ex["output"])
        with torch.no_grad():
            pred = task_model(inp).argmax(dim=1).squeeze(0)
        if not torch.equal(pred, target):
            return False
    return True


if __name__ == "__main__":
    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)

    base_model = TinyConvARCSolver(hidden=16)
    print(f"Model parameters: {base_model.count_params():,}")

    # Test on first 50 tasks
    tasks = list(challenges.values())[:50]
    solved = 0
    for i, task in enumerate(tasks):
        if evaluate_task(base_model, task):
            solved += 1
        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{len(tasks)} — solved {solved}")

    acc = solved / len(tasks) * 100
    print(f"\nSolved {solved}/{len(tasks)} tasks = {acc:.1f}%")
    print(f"METRIC neurogolf_params={base_model.count_params()}")
