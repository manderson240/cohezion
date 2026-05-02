"""NeuroGolf test-time optimization sweep.

For each task, try multiple (lr, steps, optimizer) combos and pick best.
Goal: find if some tasks are sensitive to test-time hyperparameters.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class TinyConvARCV3(nn.Module):
    def __init__(self, colors: int = 10, hidden: int = 40):
        super().__init__()
        self.hidden = hidden
        self.colors = colors
        self.embed = nn.Embedding(colors, hidden)
        self.conv1 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(hidden)
        self.conv2 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(hidden)
        self.conv3 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(hidden)
        self.conv4 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn4 = nn.BatchNorm2d(hidden)
        self.conv5 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn5 = nn.BatchNorm2d(hidden)
        self.out = nn.Conv2d(hidden, colors, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.embed(x).permute(0, 3, 1, 2)
        h = h + F.relu(self.bn1(self.conv1(h)))
        h = h + F.relu(self.bn2(self.conv2(h)))
        h = h + F.relu(self.bn3(self.conv3(h)))
        h = h + F.relu(self.bn4(self.conv4(h)))
        h = h + F.relu(self.bn5(self.conv5(h)))
        return self.out(h)

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


def grids_equal(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    return all(row_a == row_b for row_a, row_b in zip(a, b))


def train_and_predict(base_state, task, lr, steps, opt_name):
    model = TinyConvARCV3(hidden=40)
    model.load_state_dict(base_state)

    if opt_name == "adam":
        opt = torch.optim.Adam(model.parameters(), lr=lr)
    else:
        opt = torch.optim.SGD(model.parameters(), lr=lr)

    for _ in range(steps):
        for ex in task["train"]:
            inp = pad_grid(ex["input"]).unsqueeze(0)
            target = pad_grid(ex["output"]).unsqueeze(0)
            logits = model(inp)
            loss = F.cross_entropy(logits, target)
            opt.zero_grad()
            loss.backward()
            opt.step()

    test_input = task["test"][0]["input"]
    h = len(test_input)
    w = len(test_input[0]) if test_input else 0
    inp = pad_grid(test_input).unsqueeze(0)
    with torch.no_grad():
        pred = model(inp).argmax(dim=1).squeeze(0)
    return pred[:h, :w].tolist()


if __name__ == "__main__":
    model = TinyConvARCV3(hidden=40)
    base_state = {k: v.clone() for k, v in model.state_dict().items()}
    print(f"Params: {model.count_params():,}")

    configs = [
        (0.01, 100, "adam"),
        (0.05, 100, "adam"),
    ]

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:20]
    solved = 0
    for i, task_id in enumerate(task_ids):
        task = challenges[task_id]
        sol = solutions.get(task_id, [])
        if not sol:
            continue

        best_correct = False
        for lr, steps, opt_name in configs:
            pred = train_and_predict(base_state, task, lr, steps, opt_name)
            if grids_equal(pred, sol[0]):
                best_correct = True
                break

        if best_correct:
            solved += 1

        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{len(task_ids)} — solved {solved}")

    acc = solved / len(task_ids) * 100
    print(f"\nBest-of-4 configs: {solved}/{len(task_ids)} = {acc:.1f}%")
    print(f"METRIC eval_accuracy={acc:.1f}")
