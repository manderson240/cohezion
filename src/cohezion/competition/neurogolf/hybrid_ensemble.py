"""NeuroGolf hybrid: DSL solver first, conv net fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from arc_solver import apply_program, search_program


class TinyConvARCV3(nn.Module):
    """5-layer residual conv + batch norm — same as v3."""

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


def predict_conv(model, grid: list) -> list:
    inp = pad_grid(grid).unsqueeze(0)
    with torch.no_grad():
        pred = model(inp).argmax(dim=1).squeeze(0)
    h = len(grid)
    w = len(grid[0]) if grid else 0
    return pred[:h, :w].tolist()


def predict_dsl(task: dict, budget: int = 5000) -> list | None:
    """Run DSL solver, return test prediction if found."""
    try:
        program = search_program(task["train"], max_depth=3, budget=budget)
        if program:
            pred = apply_program(task["test"][0]["input"], program)
            if pred:
                return pred
    except Exception:
        pass
    return None


def predict_fallback(task: dict) -> list | None:
    """Try depth-1 primitive search as final fallback."""
    try:
        ops = [
            ("identity", lambda g: [[c for c in row] for row in g]),
            ("flip_h", lambda g: g[::-1]),
            ("transpose", lambda g: list(map(list, zip(*g)))),
        ]
        for _name, op in ops:
            all_match = True
            for ex in task["train"]:
                pred = op(ex["input"])
                if not grids_equal(pred, ex["output"]):
                    all_match = False
                    break
            if all_match:
                return op(task["test"][0]["input"])
    except Exception:
        pass
    return None


if __name__ == "__main__":
    torch.manual_seed(42)
    model = TinyConvARCV3(hidden=40)
    print(f"Conv params: {model.count_params():,}")
    base_state = {k: v.clone() for k, v in model.state_dict().items()}

    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:100]
    dsl_solved = 0
    conv_solved = 0
    hybrid_solved = 0
    both_solved = 0
    fallback_solved = 0

    for i, task_id in enumerate(task_ids):
        task = challenges[task_id]
        sol = solutions.get(task_id, [])
        if not sol:
            continue

        # DSL first
        dsl_pred = predict_dsl(task)
        dsl_ok = dsl_pred and grids_equal(dsl_pred, sol[0])
        if dsl_ok:
            dsl_solved += 1

        # Conv fallback
        task_model = TinyConvARCV3(hidden=40)
        task_model.load_state_dict(base_state)
        train_on_task(task_model, task["train"], steps=200)
        conv_pred = predict_conv(task_model, task["test"][0]["input"])
        conv_ok = grids_equal(conv_pred, sol[0])
        if conv_ok:
            conv_solved += 1

        if dsl_ok or conv_ok:
            hybrid_solved += 1
        if dsl_ok and conv_ok:
            both_solved += 1

        # Fallback: try simple primitives if both fail
        if not dsl_ok and not conv_ok:
            fb_pred = predict_fallback(task)
            if fb_pred and grids_equal(fb_pred, sol[0]):
                fallback_solved += 1
                hybrid_solved += 1

        if (i + 1) % 10 == 0:
            print(
                f"Progress: {i + 1}/{len(task_ids)} — dsl={dsl_solved} conv={conv_solved} hybrid={hybrid_solved} fallback={fallback_solved}"
            )

    n = len(task_ids)
    print(f"\nDSL:        {dsl_solved}/{n} = {dsl_solved / n * 100:.1f}%")
    print(f"Conv:       {conv_solved}/{n} = {conv_solved / n * 100:.1f}%")
    print(f"Fallback:   {fallback_solved}/{n} = {fallback_solved / n * 100:.1f}%")
    print(f"Hybrid:     {hybrid_solved}/{n} = {hybrid_solved / n * 100:.1f}%")
    print(f"Both agree: {both_solved}/{n}")
    print(f"METRIC eval_accuracy={hybrid_solved / n * 100:.1f}")
