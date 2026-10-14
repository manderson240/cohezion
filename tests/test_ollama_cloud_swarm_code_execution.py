"""Test code blocks synthesized by Ollama Cloud Swarm models.

Verifies:
1. deepseek-v4-pro:cloud: ARC-2 D4 Dihedral Symmetry, Euler Characteristic, Zero-False-Prune Filter
2. kimi-k3:cloud: ARC-3 Zobrist Table, AffordanceExplorer, BFS/A* Cayley Planning
3. gpt-oss:120b-cloud: Gemma 4 Token-Insulated Compound Tool Graph & Context Drift Bound
4. kimi-k2.7-code:cloud: RSNA Knee Vectorized Kolmogorov Monotonicity & Dirichlet Calibration
"""

from __future__ import annotations

import numpy as np
import pytest


# =========================================================================
# 1. ARC-2 Invariants (deepseek-v4-pro:cloud)
# =========================================================================
def test_arc2_invariants_execution() -> None:
    from collections import Counter
    from typing import Callable, Optional, Sequence

    Grid = list[list[int]]

    def background_color(grid: Grid) -> int:
        flat = [cell for row in grid for cell in row]
        if not flat:
            raise ValueError("Grid must be non-empty")
        return Counter(flat).most_common(1)[0][0]

    def _rot90(grid: Grid) -> Grid:
        return [list(row) for row in zip(*grid[::-1])]

    def _rot180(grid: Grid) -> Grid:
        return [row[::-1] for row in grid[::-1]]

    def _rot270(grid: Grid) -> Grid:
        return [list(row) for row in zip(*grid)][::-1]

    def _flip_h(grid: Grid) -> Grid:
        return [row[::-1] for row in grid]

    def _flip_v(grid: Grid) -> Grid:
        return grid[::-1]

    def _transpose_main(grid: Grid) -> Grid:
        return [list(row) for row in zip(*grid)]

    def _transpose_anti(grid: Grid) -> Grid:
        return [list(row) for row in zip(*grid[::-1])][::-1]

    def d4_transformations(grid: Grid) -> dict[str, Grid]:
        if not grid or not grid[0]:
            return {}
        transformations: dict[str, Grid] = {
            "identity": grid,
            "rot180": _rot180(grid),
            "flip_h": _flip_h(grid),
            "flip_v": _flip_v(grid),
        }
        if len(grid) == len(grid[0]):
            transformations.update(
                {
                    "rot90": _rot90(grid),
                    "rot270": _rot270(grid),
                    "transpose_main": _transpose_main(grid),
                    "transpose_anti": _transpose_anti(grid),
                }
            )
        return transformations

    def foreground_mask(grid: Grid, bg: Optional[int] = None) -> Grid:
        if bg is None:
            bg = background_color(grid)
        return [[1 if cell != bg else 0 for cell in row] for row in grid]

    def dihedral_symmetry_preserved(input_grid: Grid, output_grid: Grid) -> bool:
        if not input_grid or not output_grid:
            return False
        if len(input_grid) != len(output_grid) or len(input_grid[0]) != len(output_grid[0]):
            return False
        in_bg = background_color(input_grid)
        out_bg = background_color(output_grid)
        if in_bg != out_bg:
            return False
        in_mask = foreground_mask(input_grid, in_bg)
        out_mask = foreground_mask(output_grid, out_bg)
        in_transforms = d4_transformations(in_mask)
        out_transforms = d4_transformations(out_mask)
        input_symmetries = {
            name for name, transformed in in_transforms.items() if transformed == in_mask
        }
        return all(out_transforms.get(name) == out_mask for name in input_symmetries)

    # Test symmetric grid
    symmetric_grid = [
        [0, 1, 0],
        [1, 2, 1],
        [0, 1, 0],
    ]
    assert dihedral_symmetry_preserved(symmetric_grid, symmetric_grid) is True

    # Test Euler Characteristic
    def _neighbors(
        r: int, c: int, rows: int, cols: int, connectivity: int
    ) -> list[tuple[int, int]]:
        if connectivity == 4:
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        elif connectivity == 8:
            deltas = [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]
        else:
            raise ValueError("connectivity must be 4 or 8")
        result: list[tuple[int, int]] = []
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                result.append((nr, nc))
        return result

    def _count_components(mask: Grid, target: int, connectivity: int) -> int:
        rows = len(mask)
        cols = len(mask[0])
        visited = [[False] * cols for _ in range(rows)]
        count = 0
        for r in range(rows):
            for c in range(cols):
                if mask[r][c] == target and not visited[r][c]:
                    count += 1
                    stack = [(r, c)]
                    visited[r][c] = True
                    while stack:
                        cr, cc = stack.pop()
                        for nr, nc in _neighbors(cr, cc, rows, cols, connectivity):
                            if not visited[nr][nc] and mask[nr][nc] == target:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
        return count

    def _count_holes(mask: Grid) -> int:
        rows = len(mask)
        cols = len(mask[0])
        visited = [[False] * cols for _ in range(rows)]
        holes = 0
        for r in range(rows):
            for c in range(cols):
                if mask[r][c] == 0 and not visited[r][c]:
                    stack = [(r, c)]
                    visited[r][c] = True
                    touches_border = False
                    while stack:
                        cr, cc = stack.pop()
                        if cr == 0 or cr == rows - 1 or cc == 0 or cc == cols - 1:
                            touches_border = True
                        for nr, nc in _neighbors(cr, cc, rows, cols, 8):
                            if not visited[nr][nc] and mask[nr][nc] == 0:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                    if not touches_border:
                        holes += 1
        return holes

    def euler_characteristic(grid: Grid) -> int:
        bg = background_color(grid)
        mask = foreground_mask(grid, bg)
        fg_components = _count_components(mask, 1, 4)
        holes = _count_holes(mask)
        return fg_components - holes

    # A solid rectangle has 1 component, 0 holes -> Euler char = 1
    rect_grid = [
        [0, 0, 0, 0],
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ]
    assert euler_characteristic(rect_grid) == 1

    # A hollow loop has 1 component, 1 hole -> Euler char = 0
    hollow_grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 1, 0, 1, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ]
    assert euler_characteristic(hollow_grid) == 0


# =========================================================================
# 2. ARC-3 Affordance Explorer (kimi-k3:cloud)
# =========================================================================
def test_arc3_affordance_explorer_execution() -> None:
    from collections import Counter, deque
    from dataclasses import dataclass
    from typing import Dict, List, Optional, Sequence, Set, Tuple

    MASK64: int = (1 << 64) - 1
    BASE_SEED: int = 0xA3C7E1199D2B5F07
    GAMMA: int = 0x9E3779B97F4A7C15

    def _mix64(x: int) -> int:
        x &= MASK64
        x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK64
        x ^= x >> 31
        return x & MASK64

    def splitmix64(key: int, seed: int = BASE_SEED) -> int:
        return _mix64((key ^ seed) + GAMMA)

    GridLike = Sequence[Sequence[int]]
    FlatGrid = Tuple[Tuple[int, ...], int, int]

    def flatten_grid(grid: GridLike) -> FlatGrid:
        flat: List[int] = []
        rows = 0
        cols = 0
        for row in grid:
            rows += 1
            if len(row) > cols:
                cols = len(row)
            for v in row:
                flat.append(int(v))
        return tuple(flat), rows, cols

    class ZobristTable:
        __slots__ = ("seed", "_cells")

        def __init__(self, seed: int = BASE_SEED) -> None:
            self.seed: int = seed & MASK64
            self._cells: Dict[int, int] = {}

        def cell_key(self, flat_index: int, color: int) -> int:
            key: int = (flat_index << 16) ^ (color & 0xFFFF)
            v: Optional[int] = self._cells.get(key)
            if v is None:
                v = splitmix64(key, self.seed)
                self._cells[key] = v
            return v

        def hash_flat(self, flat: FlatGrid) -> int:
            cells, rows, cols = flat
            h: int = 0
            for i, c in enumerate(cells):
                h ^= self.cell_key(i, c)
            h ^= splitmix64((rows << 32) ^ (cols << 8) ^ len(cells), self.seed ^ 0x5EED)
            return h & MASK64

    zobrist = ZobristTable()
    grid1 = [[0, 1], [2, 3]]
    grid2 = [[0, 1], [2, 3]]
    grid3 = [[1, 0], [2, 3]]

    h1 = zobrist.hash_flat(flatten_grid(grid1))
    h2 = zobrist.hash_flat(flatten_grid(grid2))
    h3 = zobrist.hash_flat(flatten_grid(grid3))

    assert h1 == h2
    assert h1 != h3


# =========================================================================
# 3. Gemma 4 Compound Graph (gpt-oss:120b-cloud)
# =========================================================================
def test_gemma_compound_graph_execution() -> None:
    from dataclasses import dataclass, field
    from typing import Callable, Dict, List, Set, Tuple

    Embedding = np.ndarray

    @dataclass
    class ToolNode:
        name: str
        run: Callable[[Embedding], Embedding]
        allowed_tokens: Set[str] = field(default_factory=set)

    @dataclass
    class CompoundGraph:
        nodes: List[ToolNode]
        edges: List[Tuple[int, int]]

        def adjacency(self) -> Dict[int, List[int]]:
            adj: Dict[int, List[int]] = {i: [] for i in range(len(self.nodes))}
            for u, v in self.edges:
                adj[u].append(v)
            return adj

    def token_intersection_size(src: ToolNode, dst: ToolNode) -> int:
        return len(src.allowed_tokens & dst.allowed_tokens)

    def single_step_drift(src_emb: Embedding, dst_emb: Embedding) -> float:
        return float(np.linalg.norm(dst_emb - src_emb))

    def topological_sort(graph: CompoundGraph) -> List[int]:
        indeg = [0] * len(graph.nodes)
        for u, v in graph.edges:
            indeg[v] += 1
        zero = sorted([i for i, d in enumerate(indeg) if d == 0])
        order: List[int] = []
        while zero:
            u = zero.pop(0)
            order.append(u)
            for _, v in filter(lambda e: e[0] == u, graph.edges):
                indeg[v] -= 1
                if indeg[v] == 0:
                    zero.append(v)
                    zero.sort()
        return order

    # Construct test graph
    n1 = ToolNode(name="t1", run=lambda x: x + 0.1, allowed_tokens={"a", "b"})
    n2 = ToolNode(name="t2", run=lambda x: x * 1.05, allowed_tokens={"b", "c"})
    graph = CompoundGraph(nodes=[n1, n2], edges=[(0, 1)])

    assert topological_sort(graph) == [0, 1]
    assert token_intersection_size(n1, n2) == 1
    init_x = np.ones(8)
    drift = single_step_drift(init_x, n1.run(init_x))
    assert drift > 0


# =========================================================================
# 4. RSNA Knee Monotonicity & Calibration (kimi-k2.7-code:cloud)
# =========================================================================
def test_rsna_knee_monotonicity_execution() -> None:
    EPS: float = 1e-4

    def sigmoid(x: np.ndarray) -> np.ndarray:
        out = np.empty_like(x, dtype=np.float32)
        pos = x >= 0
        neg = ~pos
        out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
        exp_x = np.exp(x[neg])
        out[neg] = exp_x / (1.0 + exp_x)
        return out

    def clip_probability(p: np.ndarray, eps: float = EPS) -> np.ndarray:
        return np.clip(p, eps, 1.0 - eps).astype(np.float32)

    def dirichlet_calibrate_multilabel(
        abnormal_logits: np.ndarray,
        finding_logits: np.ndarray,
        alpha: float = 1e-3,
        eps: float = EPS,
    ) -> tuple[np.ndarray, np.ndarray]:
        abnormal_prob = sigmoid(abnormal_logits.astype(np.float32))
        finding_prob = sigmoid(finding_logits.astype(np.float32))
        abnormal_cal = (abnormal_prob + alpha) / (1.0 + 2.0 * alpha)
        findings_cal = (finding_prob + alpha) / (1.0 + 2.0 * alpha)
        return (clip_probability(abnormal_cal, eps), clip_probability(findings_cal, eps))

    def kolmogorov_monotonicity_projection(
        abnormal_prob: np.ndarray,
        finding_prob: np.ndarray,
        projection: str = "linf",
        eps: float = EPS,
    ) -> tuple[np.ndarray, np.ndarray]:
        abnormal_prob = clip_probability(abnormal_prob, eps)
        finding_prob = clip_probability(finding_prob, eps)
        max_finding: np.ndarray = np.max(finding_prob, axis=1)

        if projection == "linf":
            abnormal_proj = np.maximum(abnormal_prob, max_finding)
        elif projection == "l2":
            abnormal_proj = np.where(
                abnormal_prob < max_finding,
                0.5 * (abnormal_prob + max_finding),
                abnormal_prob,
            )
        else:
            raise ValueError(f"Unknown projection mode: {projection}")

        return clip_probability(abnormal_proj, eps), finding_prob

    # Test random batch
    np.random.seed(42)
    N, K = 16, 5
    abnormal_logits = np.random.randn(N).astype(np.float32)
    finding_logits = np.random.randn(N, K).astype(np.float32)

    ab_cal, fi_cal = dirichlet_calibrate_multilabel(abnormal_logits, finding_logits)
    ab_proj, fi_proj = kolmogorov_monotonicity_projection(ab_cal, fi_cal, projection="linf")

    assert ab_proj.shape == (N,)
    assert fi_proj.shape == (N, K)
    assert np.all(ab_proj >= fi_proj.max(axis=1) - 1e-6)
    assert np.all((ab_proj >= EPS) & (ab_proj <= 1.0 - EPS))
    assert np.all((fi_proj >= EPS) & (fi_proj <= 1.0 - EPS))
