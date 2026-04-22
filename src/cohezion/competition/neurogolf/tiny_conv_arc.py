"""Tiny convolutional network for ARC-AGI grid transformations.

Target: <100K parameters, processes 30x30 grids with 10 color values.
Evaluated on ARC-AGI training tasks to estimate accuracy.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class TinyConvARCSolver(nn.Module):
    """Minimal conv network for ARC grid transformations.

    Architecture:
    - Embed 10 colors → 16D
    - 3x3 conv (stride 1, padding 1) with residual
    - 3x3 conv (stride 1, padding 1) with residual
    - 1x1 conv to map back to 10 color logits
    """

    def __init__(self, grid_size: int = 30, colors: int = 10, hidden: int = 16):
        super().__init__()
        self.grid_size = grid_size
        self.colors = colors
        self.hidden = hidden

        # Color embedding
        self.embed = nn.Embedding(colors, hidden)

        # Two residual conv blocks
        self.conv1 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden, hidden, 3, padding=1)

        # Output projection
        self.out = nn.Conv2d(hidden, colors, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, H, W) int64 with color indices
        # Embed to (B, hidden, H, W)
        h = self.embed(x).permute(0, 3, 1, 2)

        # Residual block 1
        r = F.relu(self.conv1(h))
        h = h + r

        # Residual block 2
        r = F.relu(self.conv2(h))
        h = h + r

        # Output logits (B, colors, H, W)
        return self.out(h)

    def count_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


def test_forward():
    model = TinyConvARCSolver(hidden=16)
    print(f"Parameters: {model.count_params():,}")

    # Random grid
    x = torch.randint(0, 10, (1, 30, 30))
    logits = model(x)
    print(f"Output shape: {logits.shape}")  # (1, 10, 30, 30)

    # Test on a real ARC task
    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)

    task = list(challenges.values())[0]
    grid = torch.tensor(task["train"][0]["input"])
    # Pad or crop to 30x30
    h, w = grid.shape
    if h < 30 or w < 30:
        padded = torch.zeros(30, 30, dtype=torch.long)
        padded[:h, :w] = grid
        grid = padded
    else:
        grid = grid[:30, :30]

    logits = model(grid.unsqueeze(0))
    pred = logits.argmax(dim=1)  # (1, 30, 30)
    print(f"Prediction shape: {pred.shape}")
    print(f"Input unique colors: {grid.unique().tolist()}")
    print(f"Pred unique colors: {pred.unique().tolist()}")


if __name__ == "__main__":
    test_forward()
