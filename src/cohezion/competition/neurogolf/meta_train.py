"""NeuroGolf meta-training: pre-train on ALL training pairs, then test-time fine-tune per task.

The pure conv net memorizes training pairs (83%) but generalizes poorly (2%).
This experiment tests whether meta-training on thousands of task pairs teaches
a generic "grid transformation" prior, improving test generalization.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


class TinyConvARCV3(nn.Module):
    """5-layer residual conv + batch norm — same architecture as v3."""

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


if __name__ == "__main__":
    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    # Step 1: Build meta-training dataset from ALL tasks
    all_pairs = []
    for task_id, task in challenges.items():
        for pair in task["train"]:
            all_pairs.append((pair["input"], pair["output"]))
        # optionally include test pairs for meta-training (cheating if eval, but training set only)
        # We DON'T include test pairs — that's the held-out true test

    print(f"Meta-training pairs: {len(all_pairs)}")

    # Step 2: Initialize model
    model = TinyConvARCV3(hidden=40)
    print(f"Params: {model.count_params():,}")

    opt = torch.optim.Adam(model.parameters(), lr=0.01)

    # Step 3: Meta-train for N epochs
    epochs = 5
    batch_size = 32
    for epoch in range(epochs):
        random.shuffle(all_pairs)
        losses = []
        for i in range(0, len(all_pairs), batch_size):
            batch = all_pairs[i : i + batch_size]
            total_loss = 0.0
            for inp_grid, out_grid in batch:
                inp = pad_grid(inp_grid).unsqueeze(0)
                target = pad_grid(out_grid).unsqueeze(0)
                logits = model(inp)
                loss = F.cross_entropy(logits, target)
                total_loss += loss
            avg_loss = total_loss / len(batch)
            opt.zero_grad()
            avg_loss.backward()
            opt.step()
            losses.append(avg_loss.item())
        print(f"Epoch {epoch + 1}/{epochs} — avg loss: {sum(losses) / len(losses):.4f}")

    # Step 4: Save meta-trained weights
    meta_weights = {k: v.clone() for k, v in model.state_dict().items()}

    # Step 5: Test-time fine-tune per task (100 tasks)
    task_ids = list(challenges.keys())[:100]
    solved = 0
    for i, task_id in enumerate(task_ids):
        task = challenges[task_id]

        # Reset to meta-trained weights
        model.load_state_dict(meta_weights)

        # Fine-tune on this task's training pairs
        opt_task = torch.optim.Adam(model.parameters(), lr=0.05)
        for _ in range(100):  # fewer steps for fine-tuning
            for pair in task["train"]:
                inp = pad_grid(pair["input"]).unsqueeze(0)
                target = pad_grid(pair["output"]).unsqueeze(0)
                logits = model(inp)
                loss = F.cross_entropy(logits, target)
                opt_task.zero_grad()
                loss.backward()
                opt_task.step()

        # Predict test input
        test_input = task["test"][0]["input"]
        inp = pad_grid(test_input).unsqueeze(0)
        with torch.no_grad():
            pred = model(inp).argmax(dim=1).squeeze(0)
        h = len(test_input)
        w = len(test_input[0]) if test_input else 0
        pred_cropped = pred[:h, :w].tolist()

        sol = solutions.get(task_id, [])
        if sol and grids_equal(pred_cropped, sol[0]):
            solved += 1
        if (i + 1) % 20 == 0:
            print(f"Progress: {i + 1}/{len(task_ids)} — solved {solved}")

    acc = solved / len(task_ids) * 100
    print(f"\nMeta-trained + fine-tuned: {solved}/{len(task_ids)} test tasks = {acc:.1f}%")
    print(f"METRIC eval_accuracy={acc:.1f}")
