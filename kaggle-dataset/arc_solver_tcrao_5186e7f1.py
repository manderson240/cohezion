"""ARC-AGI-2 solver v3: topology-aware primitives + TinyConv fallback.

Key primitives added:
  - select_largest_object: Keep biggest connected component
  - fill_enclosed: Fill 0s enclosed by non-zero borders
  - remove_noise: Remove isolated pixels
  - color_by_object_order: Assign colors by object size rank
"""

from __future__ import annotations

from collections.abc import Callable


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

Grid = list[list[int]]
Op = Callable[[Grid], Grid | None]


def deepcopy_grid(g: Grid) -> Grid:
    return [list(r) for r in g]


def grids_equal(a: Grid | None, b: Grid | None) -> bool:
    if a is None or b is None:
        return False
    if not a and not b:
        return True
    if not a or not b:
        return False
    if len(a) != len(b):
        return False
    return all(ar == br for ar, br in zip(a, b))


# ═══════════════════════════════════════════════════════════════
# TOPOLOGY PRIMITIVES
# ═══════════════════════════════════════════════════════════════


def _connected_components(g: Grid, bg: int = 0) -> list[list[tuple[int, int]]]:
    if not g:
        return []
    h, w = len(g), len(g[0])
    visited = [[False] * w for _ in range(h)]
    comps = []
    for r in range(h):
        for c in range(w):
            if g[r][c] == bg or visited[r][c]:
                continue
            comp = []
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                if not (0 <= cr < h and 0 <= cc < w):
                    continue
                if visited[cr][cc] or g[cr][cc] == bg:
                    continue
                visited[cr][cc] = True
                comp.append((cr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    stack.append((cr + dr, cc + dc))
            if comp:
                comps.append(comp)
    return comps


def get_bounding_box(comp: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    rs = [r for r, _ in comp]
    cs = [c for _, c in comp]
    return min(rs), min(cs), max(rs), max(cs)


def select_largest_object(g: Grid, bg: int = 0) -> Grid | None:
    comps = _connected_components(g, bg=bg)
    if not comps:
        return None
    largest = max(comps, key=len)
    out = [[bg] * len(g[0]) for _ in range(len(g))]
    for r, c in largest:
        out[r][c] = g[r][c]
    return out


def fill_enclosed(
    g: Grid, fill_color: int = 1, bg: int = 0, border: int | None = None
) -> Grid | None:
    """Flood fill bg pixels that are enclosed by non-bg pixels. Simple approach."""
    if not g:
        return None
    h, w = len(g), len(g[0])

    # Mark all bg cells connected to border as non-enclosed
    non_enclosed = [[False] * w for _ in range(h)]
    from collections import deque

    q = deque()
    for r in range(h):
        for c in range(w):
            if g[r][c] == bg:
                if r == 0 or r == h - 1 or c == 0 or c == w - 1:
                    q.append((r, c))
                    non_enclosed[r][c] = True
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                if g[nr][nc] == bg and not non_enclosed[nr][nc]:
                    non_enclosed[nr][nc] = True
                    q.append((nr, nc))

    result = [row[:] for row in g]
    for r in range(h):
        for c in range(w):
            if g[r][c] == bg and not non_enclosed[r][c]:
                result[r][c] = fill_color
    return result


def remove_noise(g: Grid, min_size: int = 2, bg: int = 0) -> Grid | None:
    comps = _connected_components(g, bg=bg)
    result = [[bg] * len(g[0]) for _ in range(len(g))]
    for comp in comps:
        if len(comp) >= min_size:
            for r, c in comp:
                result[r][c] = g[r][c]
    return result


def color_by_object_rank(g: Grid, bg: int = 0) -> Grid | None:
    comps = _connected_components(g, bg=bg)
    if not comps:
        return None
    ranked = sorted(enumerate(comps), key=lambda x: len(x[1]), reverse=True)
    colors = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    result = [[bg] * len(g[0]) for _ in range(len(g))]
    for rank, (_, comp) in enumerate(ranked):
        color = colors[rank % len(colors)]
        for r, c in comp:
            result[r][c] = color
    return result


# ═══════════════════════════════════════════════════════════════
# GEOMETRIC PRIMITIVES
# ═══════════════════════════════════════════════════════════════


def identity(g: Grid) -> Grid:
    return [r[:] for r in g]


def flip_h(g: Grid) -> Grid:
    return [list(r) for r in g[::-1]]


def flip_v(g: Grid) -> Grid:
    return [r[::-1] for r in g]


def transpose(g: Grid) -> Grid:
    return list(map(list, zip(*g)))


def rot90(g: Grid) -> Grid:
    return [list(r) for r in zip(*g[::-1])]


def rot180(g: Grid) -> Grid:
    return [r[::-1] for r in g[::-1]]


def rot270(g: Grid) -> Grid:
    return [list(r) for r in zip(*g)][::-1]


def _replace_color(g, old, new):
    return [[new if c == old else c for c in row] for row in g]


def get_all_ops(train: list[dict[str, Grid]]) -> list[tuple[str, Op]]:
    ops: list[tuple[str, Op]] = [
        ("identity", identity),
        ("flip_h", flip_h),
        ("flip_v", flip_v),
        ("transpose", transpose),
        ("rot90", rot90),
        ("rot180", rot180),
        ("rot270", rot270),
        ("select_largest", select_largest_object),
        ("remove_noise_2", lambda g: remove_noise(g, min_size=2)),
        ("remove_noise_3", lambda g: remove_noise(g, min_size=3)),
        ("fill_enclosed", fill_enclosed),
        ("color_by_rank", color_by_object_rank),
    ]
    # Fill with specific colors
    colors = set()
    for ex in train:
        for row in ex["input"]:
            colors |= set(row)
        for row in ex["output"]:
            colors |= set(row)
    colors -= {0}
    for fill_c in colors:
        ops.append((f"fill_{fill_c}", lambda g, c=fill_c: fill_enclosed(g, fill_color=c)))
    # Color mappings
    for old_c in colors:
        for new_c in colors:
            if old_c != new_c:
                ops.append(
                    (f"rep_{old_c}_to_{new_c}", lambda g, o=old_c, n=new_c: _replace_color(g, o, n))
                )
    return ops


# ═══════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════


def _search_depth(train, depth, ops, budget):
    if depth == 1:
        for name, fn in ops:
            if budget <= 0:
                return None
            budget -= 1
            try:
                if all(grids_equal(fn(deepcopy_grid(ex["input"])), ex["output"]) for ex in train):
                    return [fn]
            except Exception:
                pass
        return None

    for name, fn in ops:
        try:
            transformed = []
            for ex in train:
                t = fn(deepcopy_grid(ex["input"]))
                if t is None:
                    raise ValueError
                transformed.append({"input": t, "output": ex["output"]})
            sub = _search_depth(transformed, depth - 1, ops, budget)
            if sub is not None:
                return [fn] + sub
        except Exception:
            pass
    return None


def search_program(
    train: list[dict[str, Grid]],
    max_depth: int = 3,
    ops: list[tuple[str, Op]] | None = None,
    budget: int = 2000,
) -> list[Op] | None:
    _ops = ops if ops is not None else get_all_ops(train)
    for d in range(1, min(max_depth, 2) + 1):  # Depth 1-2 only for speed
        result = _search_depth(train, d, _ops, budget)
        if result is not None:
            return result
    # Fallback to Conv
    if HAS_TORCH:
        same = True
        for ex in train:
            if len(ex["input"]) != len(ex["output"]):
                same = False
                break
            if ex["input"] and ex["output"] and len(ex["input"][0]) != len(ex["output"][0]):
                same = False
                break
        if same:
            try:
                model = _train_conv(train)
                return [lambda g: _predict_conv(model, g)]
            except Exception:
                pass
    return None


def apply_program(g: Grid, program: list[Op]) -> Grid | None:
    result = deepcopy_grid(g)
    for op in program:
        result = op(result)
        if result is None:
            return None
    return result


# ═══════════════════════════════════════════════════════════════
# TINYCONV (one-hot fallback)
# ═══════════════════════════════════════════════════════════════


class _TinyConv(nn.Module):
    def __init__(self, colors=10, hidden=32):
        super().__init__()
        self.conv1 = nn.Conv2d(colors, hidden, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(hidden)
        self.conv2 = nn.Conv2d(hidden, hidden, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(hidden)
        self.out = nn.Conv2d(hidden, colors, 1)

    def forward(self, x):
        h = F.relu(self.bn1(self.conv1(x)))
        h = F.relu(self.bn2(self.conv2(h)))
        return self.out(h)


def _grid_to_onehot(grid, colors=10, size=30):
    h = len(grid)
    w = len(grid[0]) if grid else 0
    t = torch.zeros(colors, size, size, dtype=torch.float32)
    for i in range(min(h, size)):
        for j in range(min(w, size)):
            c = grid[i][j]
            if 0 <= c < colors:
                t[c, i, j] = 1.0
    return t


def _tensor_to_grid(t, th, tw):
    return [list(row) for row in t[:th, :tw].tolist()]


def _train_conv(train, hidden=32, steps=200):
    model = _TinyConv(hidden=hidden)
    opt = torch.optim.Adam(model.parameters(), lr=0.05)
    for _ in range(steps):
        for ex in train:
            inp = _grid_to_onehot(ex["input"]).unsqueeze(0)
            target = _grid_to_onehot(ex["output"]).unsqueeze(0)
            logits = model(inp)
            loss = F.cross_entropy(logits, target.argmax(dim=1))
            opt.zero_grad()
            loss.backward()
            opt.step()
    return model


def _predict_conv(model, grid):
    model.eval()
    h = len(grid)
    w = len(grid[0]) if grid else 0
    inp = _grid_to_onehot(grid).unsqueeze(0)
    with torch.no_grad():
        pred = model(inp).argmax(dim=1).squeeze(0)
    return _tensor_to_grid(pred, h, w)


# ═══════════════════════════════════════════════════════════════
# TCRAO INTERFACE
# ═══════════════════════════════════════════════════════════════


def solve_task(task: dict, max_depth: int = 3):
    task_id = task.get("id", "unknown")
    train = task.get("train", [])
    test = task.get("test", [])

    program = search_program(train, max_depth=max_depth)
    predictions = []
    if program:
        for test_ex in test:
            pred = apply_program(deepcopy_grid(test_ex["input"]), program)
            predictions.append({"attempt_1": [pred], "attempt_2": [pred]})
    else:
        for test_ex in test:
            predictions.append(
                {
                    "attempt_1": [deepcopy_grid(test_ex["input"])],
                    "attempt_2": [deepcopy_grid(test_ex["input"])],
                }
            )
    return {task_id: predictions}
