"""NeuroGolf generalization test: train on train pairs, predict test outputs.
Uses arc-agi_training_challenges.json + arc-agi_training_solutions.json.
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


def predict(model, grid: list) -> list:
    inp = pad_grid(grid).unsqueeze(0)
    with torch.no_grad():
        pred = model(inp).argmax(dim=1).squeeze(0)
    # Crop back to original size
    h = len(grid)
    w = len(grid[0]) if grid else 0
    pred_cropped = pred[:h, :w].tolist()
    return pred_cropped


if __name__ == "__main__":
    model = TinyConvARCV3(hidden=40)
    print(f"Params: {model.count_params():,}")

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    tasks = list(challenges.keys())[:100]
    solved = 0
    for i, task_id in enumerate(tasks):
        task = challenges[task_id]
        task_model = TinyConvARCV3(hidden=model.hidden)
        task_model.load_state_dict(model.state_dict())
        train_on_task(task_model, task["train"], steps=200)

        test_input = task["test"][0]["input"]
        pred = predict(task_model, test_input)
        sol = solutions.get(task_id, [])
        if sol and grids_equal(pred, sol[0]):
            solved += 1
        if (i + 1) % 20 == 0:
            print(f"Progress: {i+1}/{len(tasks)} — solved {solved}")

    acc = solved / len(tasks) * 100
    print(f"\nGeneralized {solved}/{len(tasks)} test tasks = {acc:.1f}%")
    print(f"METRIC eval_accuracy={acc:.1f}")
