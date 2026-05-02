"""NeuroGolf Kaggle Submission Script

Self-contained script for Kaggle notebook submission.
Submits predictions for all eval tasks using the best tiny conv model.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class TinyConvARCV3(nn.Module):
    """5-layer residual conv + batch norm, 73,410 params."""

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
    h = len(grid)
    w = len(grid[0]) if grid else 0
    pred_cropped = pred[:h, :w].tolist()
    return pred_cropped


if __name__ == "__main__":
    # On Kaggle, data is at /kaggle/input/arc-prize-2026/
    data_dir = Path("/kaggle/input/arc-prize-2026/")
    if not data_dir.exists():
        data_dir = Path("/home/mike-anderson/dev/cohezion/data/arc-agi-2")

    with open(data_dir / "arc-agi_evaluation_challenges.json") as f:
        eval_challenges = json.load(f)

    base_model = TinyConvARCV3(hidden=40)
    print(f"Model parameters: {base_model.count_params():,}")

    predictions = {}
    for task_id, task in eval_challenges.items():
        task_model = TinyConvARCV3(hidden=40)
        task_model.load_state_dict(base_model.state_dict())
        train_on_task(task_model, task["train"], steps=200)

        preds = []
        for test_pair in task["test"]:
            pred_grid = predict(task_model, test_pair["input"])
            preds.append(pred_grid)

        predictions[task_id] = preds

    # Write submission
    with open("submission.json", "w") as f:
        json.dump(predictions, f)

    print(f"Submission written for {len(predictions)} tasks")
