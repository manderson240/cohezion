"""Focused ARC-AGI-2 solver: task-type detection + per-task conv for same-size.

Strategy:
1. Detect task type from train examples
2. Same-size → train TinyConv per-task with more capacity + steps
3. Shape-change → try scale/crop/pad primitives
4. Always return a prediction (no None)
"""

from __future__ import annotations

from typing import Callable


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

Grid = list[list[int]]
Program = Callable[[Grid], Grid | None]


def grids_equal(a, b):
    if a is None or b is None:
        return False
    if len(a) != len(b):
        return False
    if not a:
        return not b
    if any(len(ar) != len(br) for ar, br in zip(a, b)):
        return False
    return all(ar == br for ar, br in zip(a, b))


# ── Same-size tasks: TinyConv per-task ──────────────────────────


class TinyConv(nn.Module):
    def __init__(self, colors=10, hidden=32):
        super().__init__()
        self.conv1 = nn.Conv2d(colors, hidden, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(hidden)
        self.conv2 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(hidden)
        self.conv3 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(hidden)
        self.out = nn.Conv2d(hidden, colors, 1)

    def forward(self, x):
        h = self.conv1(x)
        h = F.relu(self.bn1(h))
        h = self.conv2(h)
        h = F.relu(self.bn2(h))
        h = self.conv3(h)
        h = F.relu(self.bn3(h))
        return self.out(h)


def _grid_to_onehot(grid, colors=10, size=30):
    h = len(grid)
    w = len(grid[0]) if grid else 0
    t = torch.zeros(colors, size, size, dtype=torch.float32)
    hh = min(h, size)
    ww = min(w, size)
    for i in range(hh):
        for j in range(ww):
            c = grid[i][j]
            if 0 <= c < colors:
                t[c, i, j] = 1.0
    return t


def _tensor_to_grid(t, th, tw):
    return [list(row) for row in t[:th, :tw].tolist()]


def _train_conv(train, colors=10, hidden=32, steps=200, lr=0.05):
    """Train per-task conv with early stopping on train set."""
    model = TinyConv(hidden=hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()

    best_loss = float("inf")
    no_improve = 0

    for epoch in range(steps):
        epoch_loss = 0.0
        for ex in train:
            inp = _grid_to_onehot(ex["input"]).unsqueeze(0)
            target = _grid_to_onehot(ex["output"]).unsqueeze(0)
            logits = model(inp)
            loss = F.cross_entropy(logits, target.argmax(dim=1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_loss += loss.item()

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            no_improve = 0
        else:
            no_improve += 1

        if no_improve > 30:  # Early stop if no improvement for 30 epochs
            break

    return model


def _predict_conv(model, grid):
    model.eval()
    h = len(grid)
    w = len(grid[0]) if grid else 0
    inp = _grid_to_onehot(grid).unsqueeze(0)
    with torch.no_grad():
        pred = model(inp).argmax(dim=1).squeeze(0)
    return _tensor_to_grid(pred, h, w)


# ── Shape-change primitives ───────────────────────────────────


def identity(g):
    return [r[:] for r in g]


def crop_to_size(g, th, tw):
    """Crop or pad grid to target size."""
    h = len(g)
    w = len(g[0]) if g else 0
    result = []
    for i in range(th):
        row = []
        for j in range(tw):
            if i < h and j < w:
                row.append(g[i][j])
            else:
                row.append(0)
        result.append(row)
    return result


def try_primitives(train, test_input):
    """Try simple geometric primitives on shape-changing tasks."""
    primitives = [
        ("identity", identity),
        ("flip_h", lambda g: g[::-1]),
        ("flip_v", lambda g: [r[::-1] for r in g]),
        ("transpose", lambda g: list(map(list, zip(*g)))),
        ("rot90", lambda g: [list(r) for r in zip(*g[::-1])]),
        ("rot180", lambda g: [r[::-1] for r in g[::-1]]),
    ]

    for name, fn in primitives:
        try:
            if all(grids_equal(fn(ex["input"]), ex["output"]) for ex in train):
                return fn(test_input)
        except Exception:
            pass

    # Fallback: identity with size adjustment
    target_h = len(train[0]["output"])
    target_w = len(train[0]["output"][0]) if train[0]["output"] else 0
    return crop_to_size(test_input, target_h, target_w)


# ── Task type detection ───────────────────────────────────────


def _task_type(task):
    """Returns 'same_size', 'downscale', 'upscale', 'mixed'."""
    train = task.get("train", [])
    if not train:
        return "unknown"

    same = True
    for ex in train:
        if len(ex["input"]) != len(ex["output"]):
            same = False
            break
        if ex["input"] and ex["output"] and len(ex["input"][0]) != len(ex["output"][0]):
            same = False
            break

    if same:
        return "same_size"

    # Check if output is consistently smaller or larger
    smaller = all(
        len(ex["input"]) >= len(ex["output"])
        and (not ex["input"] or len(ex["input"][0]) >= len(ex["output"][0]))
        for ex in train
    )
    larger = all(
        len(ex["input"]) <= len(ex["output"])
        and (not ex["input"] or len(ex["input"][0]) <= len(ex["output"][0]))
        for ex in train
    )

    if smaller and any(len(ex["input"]) > len(ex["output"]) for ex in train):
        return "downscale"
    if larger and any(len(ex["input"]) < len(ex["output"]) for ex in train):
        return "upscale"

    return "mixed"


# ── Main solve entry point ─────────────────────────────────────


def solve_task(task: dict, max_depth: int = 3):
    task_id = task.get("id", "unknown")
    train = task.get("train", [])
    test = task.get("test", [])

    ttype = _task_type(task)
    predictions: list[dict] = []

    if ttype == "same_size" and HAS_TORCH:
        try:
            model = _train_conv(train, hidden=32, steps=300, lr=0.05)
            for test_ex in test:
                pred = _predict_conv(model, test_ex["input"])
                predictions.append({"attempt_1": [pred], "attempt_2": [pred]})
            return {task_id: predictions}
        except Exception:
            pass

    # Fallback: primitives for shape-change, identity for same-size if conv failed
    for test_ex in test:
        pred = try_primitives(train, test_ex["input"])
        predictions.append({"attempt_1": [pred], "attempt_2": [pred]})

    return {task_id: predictions}


# Legacy entry points for eval harness compatibility
def get_all_ops(train):
    """Return a basic op list (eval harness expects this)."""
    return [("identity", identity)]


def search_program(train, max_depth=3, ops=None, budget=2000):
    """Eval harness calls this — we return identity since solve_task handles everything."""
    return [identity]


def apply_program(g, program):
    result = [r[:] for r in g]
    for op in program:
        result = op(result)
    return result
