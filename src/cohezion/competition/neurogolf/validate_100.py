"""Validate best NeuroGolf config on 100 ARC training tasks.
Best config from sweep: hidden=48, 84,106 params, Adam, 200 steps.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class TinyConvARCV2(nn.Module):
    def __init__(self, colors: int = 10, hidden: int = 48):
        super().__init__()
        self.hidden = hidden
        self.colors = colors
        self.embed = nn.Embedding(colors, hidden)
        self.conv1 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.conv3 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.conv4 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.out = nn.Conv2d(hidden, colors, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.embed(x).permute(0, 3, 1, 2)
        h = h + F.relu(self.conv1(h))
        h = h + F.relu(self.conv2(h))
        h = h + F.relu(self.conv3(h))
        h = h + F.relu(self.conv4(h))
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


def train_on_task(model, train_examples, steps=200, lr=0.05):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for _ in range(steps):
        for ex in train_examples:
            inp = pad_grid(ex["input"]).unsqueeze(0)
            target = pad_grid(ex["output"]).unsqueeze(0)
            logits = model(inp)
            loss = F.cross_entropy(logits, target)
            opt.zero_grad()
            loss.backward()
            opt.step()


def evaluate(model, task):
    task_model = TinyConvARCV2(hidden=model.hidden)
    task_model.load_state_dict(model.state_dict())
    train_on_task(task_model, task["train"], steps=200)
    for ex in task["train"]:
        inp = pad_grid(ex["input"]).unsqueeze(0)
        target = pad_grid(ex["output"])
        with torch.no_grad():
            pred = task_model(inp).argmax(dim=1).squeeze(0)
        if not torch.equal(pred, target):
            return False
    return True


if __name__ == "__main__":
    model = TinyConvARCV2(hidden=48)
    print(f"Params: {model.count_params():,}")

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)

    tasks = list(challenges.values())[:100]
    solved = 0
    for i, task in enumerate(tasks):
        if evaluate(model, task):
            solved += 1
        if (i + 1) % 20 == 0:
            print(f"Progress: {i+1}/{len(tasks)} — solved {solved}")

    acc = solved / len(tasks) * 100
    print(f"\nSolved {solved}/{len(tasks)} = {acc:.1f}%")
    print(f"METRIC neurogolf_params={model.count_params()}")
