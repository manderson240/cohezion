"""NeuroGolf tiny transformer: 2-layer, 2-head, hidden=32.

Treats 30x30 grid as 900 sequential tokens.
Hypothesis: attention may better learn compositional transformations (mirror, rotate, gravity)
than local convolutions.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class TinyTransformerARCSolver(nn.Module):
    """Tiny transformer for ARC grids. ~54K params."""

    def __init__(self, colors: int = 10, hidden: int = 32, heads: int = 2, layers: int = 2, grid_size: int = 30):
        super().__init__()
        self.colors = colors
        self.hidden = hidden
        self.grid_size = grid_size
        self.seq_len = grid_size * grid_size

        self.token_embed = nn.Embedding(colors, hidden)
        self.pos_embed = nn.Parameter(torch.randn(1, self.seq_len, hidden) * 0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden,
            nhead=heads,
            dim_feedforward=hidden * 4,
            dropout=0.0,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=layers)

        self.out = nn.Linear(hidden, colors)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, H, W) int64
        B, H, W = x.shape
        x = x.view(B, -1)  # (B, seq_len)
        h = self.token_embed(x) + self.pos_embed[:, : self.seq_len, :]
        h = self.transformer(h)  # (B, seq_len, hidden)
        logits = self.out(h)  # (B, seq_len, colors)
        return logits.view(B, self.colors, H, W)

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
    return pred[:h, :w].tolist()


if __name__ == "__main__":
    torch.manual_seed(42)
    model = TinyTransformerARCSolver(hidden=32, heads=2, layers=2)
    print(f"Transformer params: {model.count_params():,}")

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:100]
    base_state = {k: v.clone() for k, v in model.state_dict().items()}

    solved = 0
    for i, task_id in enumerate(task_ids):
        task = challenges[task_id]
        task_model = TinyTransformerARCSolver(hidden=32, heads=2, layers=2)
        task_model.load_state_dict(base_state)
        train_on_task(task_model, task["train"], steps=200)

        test_input = task["test"][0]["input"]
        pred = predict(task_model, test_input)
        sol = solutions.get(task_id, [])
        if sol and grids_equal(pred, sol[0]):
            solved += 1
        if (i + 1) % 20 == 0:
            print(f"Progress: {i+1}/{len(task_ids)} — solved {solved}")

    acc = solved / len(task_ids) * 100
    print(f"\nTransformer: {solved}/{len(task_ids)} = {acc:.1f}%")
    print(f"METRIC eval_accuracy={acc:.1f}")
