"""NeuroGolf v4: Coordinate-aware conv for ARC generalization.

Adds row/col position encoding to input channels at negligible cost.
Hypothesis: some ARC tasks (border, mirror, gravity) depend on absolute position.
Current model lacks positional awareness beyond local conv receptive fields.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class CoordConvARCSolver(nn.Module):
    """Coordinate-aware 5-layer residual conv for ARC grids.

    Input channels: color_embed(40) + row_idx(1) + col_idx(1) = 42
    Hidden channels: 40
    Output: 10-color logits
    """

    def __init__(self, colors: int = 10, hidden: int = 40, max_size: int = 30):
        super().__init__()
        self.hidden = hidden
        self.colors = colors
        self.max_size = max_size

        self.embed = nn.Embedding(colors, hidden)

        # Coordinate grids (fixed, not learned)
        self.register_buffer("row_grid", torch.arange(max_size).float().view(1, 1, max_size, 1) / max_size)
        self.register_buffer("col_grid", torch.arange(max_size).float().view(1, 1, 1, max_size) / max_size)

        # Conv layers operate on hidden+2 channels (embed + row + col)
        in_ch = hidden + 2
        self.conv1 = nn.Conv2d(in_ch, hidden, 3, padding=1)
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

    def _get_coords(self, batch_size: int, h: int, w: int) -> torch.Tensor:
        """Return row/col coordinate channels for the actual grid size."""
        rows = self.row_grid[:, :, :h, :].expand(batch_size, 1, h, w)
        cols = self.col_grid[:, :, :, :w].expand(batch_size, 1, h, w)
        return torch.cat([rows, cols], dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, H, W) int64 color indices
        B, H, W = x.shape
        h = self.embed(x).permute(0, 3, 1, 2)  # (B, hidden, H, W)
        coords = self._get_coords(B, H, W)  # (B, 2, H, W)
        h = torch.cat([h, coords], dim=1)  # (B, hidden+2, H, W)

        h = F.relu(self.bn1(self.conv1(h)))
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
    h = len(grid)
    w = len(grid[0]) if grid else 0
    pred_cropped = pred[:h, :w].tolist()
    return pred_cropped


if __name__ == "__main__":
    model = CoordConvARCSolver(hidden=40)
    print(f"Params: {model.count_params():,}")

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:30]  # 30 tasks for speed
    base_state = {k: v.clone() for k, v in model.state_dict().items()}

    solved = 0
    for i, task_id in enumerate(task_ids):
        task = challenges[task_id]
        task_model = CoordConvARCSolver(hidden=40)
        task_model.load_state_dict(base_state)
        train_on_task(task_model, task["train"], steps=200)

        test_input = task["test"][0]["input"]
        pred = predict(task_model, test_input)
        sol = solutions.get(task_id, [])
        if sol and grids_equal(pred, sol[0]):
            solved += 1
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{len(task_ids)} — solved {solved}")

    acc = solved / len(task_ids) * 100
    print(f"\nCoordConv: {solved}/{len(task_ids)} = {acc:.1f}%")
    print(f"METRIC eval_accuracy={acc:.1f}")
