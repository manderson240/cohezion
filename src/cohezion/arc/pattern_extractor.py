"""Pattern Rule Extractor using Compound Engineering.

Extracts human-readable, verifiable transformation rules from ARC task training
examples by combining:

1. Geometric primitive search (DSL ops from arc_solver)
2. Compound-engineering consensus voting across multiple search strategies
3. FLUME 256-D latent similarity for analogy detection
4. HIHO-gated rule confidence scoring

The output is a list of ``CompoundRule`` objects that can be serialized,
verified, and fed into the submission builder.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cohezion.arc.codec import ARCCodec, Grid, grids_equal


# ---------------------------------------------------------------------------
# Dependencies: try to import solver ops, fall back gracefully
# ---------------------------------------------------------------------------
try:
    from cohezion.competition.arc_solver import get_all_ops as _get_solver_ops
    from cohezion.competition.arc_solver import search_program
except Exception:
    get_all_ops = None  # type: ignore[misc]
    search_program = None  # type: ignore[misc]
else:
    get_all_ops = _get_solver_ops

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
Program = Callable[[Grid], Grid | None]


# ---------------------------------------------------------------------------
# CompoundRule dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompoundRule:
    """A verified transformation rule extracted by compound engineering."""

    name: str  # e.g. "color_map + gravity_down"
    ops: tuple[str, ...]  # ordered primitive names
    confidence: float  # 0..1, compound consensus score
    train_coverage: float  # fraction of train examples matched
    strategy_votes: int  # how many search strategies agreed
    hiho_score: float  # geometric coherence of the rule
    latent_delta: tuple[float, ...]  # mean 256-D delta vector (latent analogy)
    signature: str  # deterministic SHA-256 of op sequence

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ops": list(self.ops),
            "confidence": self.confidence,
            "train_coverage": self.train_coverage,
            "strategy_votes": self.strategy_votes,
            "hiho_score": self.hiho_score,
            "latent_delta": list(self.latent_delta),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CompoundRule:
        return cls(
            name=d["name"],
            ops=tuple(d["ops"]),
            confidence=d["confidence"],
            train_coverage=d["train_coverage"],
            strategy_votes=d["strategy_votes"],
            hiho_score=d["hiho_score"],
            latent_delta=tuple(d["latent_delta"]),
            signature=d["signature"],
        )


# ---------------------------------------------------------------------------
# Primitive registry (inline fallback so extractor works even if solver import fails)
# ---------------------------------------------------------------------------


def _identity(g: Grid) -> Grid:
    return [r[:] for r in g]


def _transpose(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]))]


def _rot90(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]) - 1, -1, -1)]


def _rot180(g: Grid) -> Grid:
    return [r[::-1] for r in reversed(g)]


def _flip_h(g: Grid) -> Grid:
    return [r[:] for r in reversed(g)]


def _flip_v(g: Grid) -> Grid:
    return [r[::-1] for r in g]


def _replace_color(g: Grid, old: int, new: int) -> Grid | None:
    if not any(c == old for row in g for c in row):
        return None
    return [[new if c == old else c for c in row] for row in g]


def _invert_colors(g: Grid) -> Grid | None:
    colors = sorted({c for row in g for c in row})
    if len(colors) != 2:
        return None
    a, b = colors
    return [[b if c == a else a for c in row] for row in g]


def _most_common_color(g: Grid) -> int:
    from collections import Counter

    cnt = Counter(c for row in g for c in row)
    return cnt.most_common(1)[0][0] if cnt else 0


def _remove_bg(g: Grid) -> Grid | None:
    bg = _most_common_color(g)
    ng = [[0 if c == bg else c for c in row] for row in g]
    return ng if ng != g else None


def _fill_holes(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    result = [r[:] for r in g]
    changed = False
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if result[r][c] != 0:
                continue
            nbrs = {result[r - 1][c], result[r + 1][c], result[r][c - 1], result[r][c + 1]}
            nbrs.discard(0)
            if len(nbrs) == 1:
                result[r][c] = nbrs.pop()
                changed = True
    return result if changed else None


def _mirror_h(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    if cols % 2 != 0:
        return None
    half = cols // 2
    result = []
    for r in range(rows):
        left = g[r][:half]
        right = g[r][half:]
        if left != right[::-1]:
            result.append(left + left[::-1])
        else:
            result.append(g[r])
    return result if result != g else None


def _mirror_v(g: Grid) -> Grid | None:
    if not g:
        return None
    rows = len(g)
    if rows % 2 != 0:
        return None
    half = rows // 2
    top = g[:half]
    bottom = g[half:]
    if top == [row[::-1] for row in bottom[::-1]]:
        return None
    return top + [row[::-1] for row in top[::-1]]


def _gravity_down(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    result = [[0] * cols for _ in range(rows)]
    changed = False
    for c in range(cols):
        col = [g[r][c] for r in range(rows) if g[r][c] != 0]
        if col:
            for r in range(rows - len(col), rows):
                result[r][c] = col[r - (rows - len(col))]
            if any(result[r][c] != g[r][c] for r in range(rows)):
                changed = True
    return result if changed else None


def _gravity_up(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    result = [[0] * cols for _ in range(rows)]
    changed = False
    for c in range(cols):
        col = [g[r][c] for r in range(rows) if g[r][c] != 0]
        if col:
            for r in range(len(col)):
                result[r][c] = col[r]
            if any(result[r][c] != g[r][c] for r in range(rows)):
                changed = True
    return result if changed else None


def _extend_down(g: Grid) -> Grid | None:
    """Double height by appending a vertically-mirrored copy below."""
    if not g:
        return None
    result = g + [r[:] for r in reversed(g)]
    return result if len(result) <= 30 else None


def _extend_right(g: Grid) -> Grid | None:
    """Double width by appending a horizontally-mirrored copy to the right."""
    if not g or not g[0]:
        return None
    result = [r + r[::-1] for r in g]
    return result if all(len(r) <= 30 for r in result) else None


def _crop_to_object(g: Grid) -> Grid | None:
    """Crop to the bounding box of the first non-background connected component."""
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    # Find background (most common color)
    from collections import Counter

    counts: Counter[int] = Counter(g[r][c] for r in range(rows) for c in range(cols))
    bg = counts.most_common(1)[0][0]
    # BFS to find connected components of non-background colors
    visited = [[False] * cols for _ in range(rows)]
    for sr in range(rows):
        for sc in range(cols):
            if g[sr][sc] == bg or visited[sr][sc]:
                continue
            # BFS
            queue = [(sr, sc)]
            component: list[tuple[int, int]] = []
            visited[sr][sc] = True
            while queue:
                r, c = queue.pop()
                component.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and not visited[nr][nc]
                        and g[nr][nc] != bg
                    ):
                        visited[nr][nc] = True
                        queue.append((nr, nc))
            min_r = min(r for r, c in component)
            max_r = max(r for r, c in component)
            min_c = min(c for r, c in component)
            max_c = max(c for r, c in component)
            cropped = [g[r][min_c : max_c + 1] for r in range(min_r, max_r + 1)]
            if len(cropped) != rows or len(cropped[0]) != cols:
                return cropped
    return None


def _deduplicate_cols(g: Grid) -> Grid | None:
    """Remove duplicate columns, keeping first occurrence of each unique column pattern."""
    if not g or not g[0]:
        return None
    seen: list[tuple[int, ...]] = []
    kept: list[int] = []
    for c in range(len(g[0])):
        col = tuple(g[r][c] for r in range(len(g)))
        if col not in seen:
            seen.append(col)
            kept.append(c)
    if len(kept) == len(g[0]):
        return None
    return [[g[r][c] for c in kept] for r in range(len(g))]


# Parametric color-map wrapper


def _color_map(g: Grid, train: list[dict[str, Grid]]) -> Grid | None:
    """Learn a color mapping from input->output statistics across all train pairs."""
    mapping: dict[int, int] = {}
    counts: dict[tuple[int, int], int] = {}
    for ex in train:
        inp, out = ex["input"], ex["output"]
        if len(inp) != len(out) or any(
            len(ir) != len(or_) for ir, or_ in zip(inp, out, strict=False)
        ):
            return None
        for r in range(len(inp)):
            for c in range(len(inp[0])):
                pair = (inp[r][c], out[r][c])
                counts[pair] = counts.get(pair, 0) + 1

    # Build deterministic mapping: pick most common output per input
    for (ic, oc), cnt in counts.items():
        if ic not in mapping or counts.get((ic, mapping[ic]), 0) < cnt:
            mapping[ic] = oc

    if not mapping or mapping == {k: k for k in mapping}:
        return None
    return [[mapping.get(cell, cell) for cell in row] for row in g]


# Parametric wrappers
def _make_replace(old: int, new: int):
    def fn(g: Grid) -> Grid | None:
        return _replace_color(g, old, new)

    return fn


def _make_color_map(train: list[dict[str, Grid]]):
    def fn(g: Grid) -> Grid | None:
        return _color_map(g, train)

    return fn


def _make_upsample(n: int):
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0]) if g else 0
        if rows * n > 30 or cols * n > 30:
            return None
        result = []
        for r in range(rows):
            new_row = []
            for c in range(cols):
                new_row.extend([g[r][c]] * n)
            for _ in range(n):
                result.append(new_row)
        return result

    return fn


def _make_downsample(n: int):
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0]) if g else 0
        if rows % n != 0 or cols % n != 0:
            return None
        return [[g[r][c] for c in range(0, cols, n)] for r in range(0, rows, n)]

    return fn


# ---------------------------------------------------------------------------
# Strategy builders
# ---------------------------------------------------------------------------


def _build_strategy(name: str, train: list[dict[str, Grid]]) -> list[tuple[str, Program]]:
    """Return a focused list of primitives for a named strategy."""
    base: list[tuple[str, Program]] = [
        ("identity", _identity),
        ("flip_h", _flip_h),
        ("flip_v", _flip_v),
        ("transpose", _transpose),
        ("rot90", _rot90),
        ("rot180", _rot180),
    ]

    color: list[tuple[str, Program]] = (
        base
        + [
            ("invert", _invert_colors),
            ("remove_bg", _remove_bg),
            ("fill_holes", _fill_holes),
        ]
        + [
            (f"replace_{old}_{new}", _make_replace(old, new))
            for old in range(10)
            for new in range(10)
            if old != new
        ]
    )

    geo = [
        *base,
        ("mirror_h", _mirror_h),
        ("mirror_v", _mirror_v),
        ("extend_down", _extend_down),
        ("extend_right", _extend_right),
    ]

    obj = [
        *base,
        ("fill_holes", _fill_holes),
        ("remove_bg", _remove_bg),
        ("gravity_d", _gravity_down),
        ("gravity_u", _gravity_up),
        ("crop_obj", _crop_to_object),
        ("dedup_cols", _deduplicate_cols),
    ]

    scale = [
        ("identity", _identity),
        *_make_parametric_scale(),
    ]

    cm = [*base, ("color_map", _make_color_map(train))]

    return {
        "color": color,
        "geo": geo,
        "obj": obj,
        "scale": scale,
        "color_map": cm,
        "all": [*color, *geo, *obj, *scale, *cm],
    }.get(name, base)


def _make_parametric_scale() -> list[tuple[str, Program]]:
    out: list[tuple[str, Program]] = []
    for n in (2, 3):
        out.append((f"upsample{n}", _make_upsample(n)))
        out.append((f"downsample{n}", _make_downsample(n)))
    return out


# ---------------------------------------------------------------------------
# Pattern Extractor
# ---------------------------------------------------------------------------


class PatternExtractor:
    """
    Extract ``CompoundRule`` objects from an ARC task using compound
    engineering consensus across multiple search strategies.

    Parameters
    ----------
    max_depth : int
        Maximum length of operation chain to test (default 3).
    budget_per_strategy : int
        Candidate program evaluations per strategy (default 800).
    consensus_threshold : int
        Minimum number of strategies that must agree on a rule for it to be
        emitted (default 1 — set >1 for strict consensus).
    codec : ARCCodec | None
        Optional encoder/decoder for latent-delta computation.
    """

    def __init__(
        self,
        max_depth: int = 3,
        budget_per_strategy: int = 800,
        consensus_threshold: int = 1,
        codec: ARCCodec | None = None,
    ) -> None:
        self.max_depth = max_depth
        self.budget = budget_per_strategy
        self.consensus_threshold = consensus_threshold
        self.codec = codec or ARCCodec()
        self._counter: list[int] = [0]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(self, task: dict[str, Any]) -> list[CompoundRule]:
        """
        Extract all ``CompoundRule``<s> that explain the training examples.

        Returns a list sorted by descending confidence.
        """
        train: list[dict[str, Grid]] = task.get("train", [])
        if not train:
            return []

        strategies = ["color", "geo", "obj", "scale", "color_map", "all"]
        vote_map: dict[tuple[str, ...], list[str]] = {}
        coverage_map: dict[tuple[str, ...], float] = {}
        hiho_map: dict[tuple[str, ...], float] = {}
        latent_map: dict[tuple[str, ...], list[float]] = {}

        for strat_name in strategies:
            ops = _build_strategy(strat_name, train)
            program = self._search(train, ops)
            if program is None:
                continue
            op_names = tuple(name for name, _ in program)
            vote_map.setdefault(op_names, []).append(strat_name)

            # Coverage
            coverage = self._coverage(train, program)
            coverage_map[op_names] = max(coverage_map.get(op_names, 0.0), coverage)

            # HIHO coherence (geometric validity of the transformation)
            hiho = self._compute_hiho(train, program)
            hiho_map[op_names] = max(hiho_map.get(op_names, 0.0), hiho)

            # Latent delta (FLUME 256-D analogy)
            latent = self._compute_latent_delta(train, program)
            latent_map[op_names] = latent  # overwrite with latest — deterministic per strat

        results: list[CompoundRule] = []
        for op_names, voters in vote_map.items():
            if len(voters) < self.consensus_threshold:
                continue
            sig = hashlib.sha256("->".join(op_names).encode()).hexdigest()[:16]
            results.append(
                CompoundRule(
                    name=" + ".join(op_names),
                    ops=op_names,
                    confidence=min(1.0, 0.5 + 0.1 * len(voters) + 0.3 * coverage_map[op_names]),
                    train_coverage=coverage_map[op_names],
                    strategy_votes=len(voters),
                    hiho_score=hiho_map.get(op_names, 0.5),
                    latent_delta=tuple(latent_map.get(op_names, [0.0] * 12)),
                    signature=sig,
                )
            )

        results.sort(key=lambda r: (r.confidence, r.strategy_votes, r.hiho_score), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Search core
    # ------------------------------------------------------------------
    def _search(
        self, train: list[dict[str, Grid]], ops: list[tuple[str, Program]]
    ) -> list[tuple[str, Program]] | None:
        self._counter[0] = 0
        for depth in range(1, self.max_depth + 1):
            result = self._dfs(train, depth, ops)
            if result is not None:
                return result
        return None

    def _dfs(
        self,
        train: list[dict[str, Grid]],
        depth: int,
        ops: list[tuple[str, Program]],
    ) -> list[tuple[str, Program]] | None:
        if depth == 1:
            for name, op in ops:
                self._counter[0] += 1
                if self._counter[0] > self.budget:
                    return None
                if all(
                    (r := op(deepcopy(ex["input"]))) is not None and grids_equal(r, ex["output"])
                    for ex in train
                ):
                    return [(name, op)]
            return None

        for name, op in ops:
            transformed = []
            valid = True
            for ex in train:
                t = op(deepcopy(ex["input"]))
                if t is None:
                    valid = False
                    break
                transformed.append({"input": t, "output": ex["output"]})
            if not valid:
                continue
            sub = self._dfs(transformed, depth - 1, ops)
            if sub is not None:
                return [(name, op), *sub]
        return None

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------
    def _coverage(self, train: list[dict[str, Grid]], program: list[tuple[str, Program]]) -> float:
        """Fraction of train examples perfectly transformed by ``program``."""
        if not train:
            return 0.0
        matched = 0
        for ex in train:
            g = deepcopy(ex["input"])
            for _, op in program:
                g = op(g)
                if g is None:
                    break
            if g is not None and grids_equal(g, ex["output"]):
                matched += 1
        return matched / len(train)

    def _compute_hiho(
        self, train: list[dict[str, Grid]], program: list[tuple[str, Program]]
    ) -> float:
        """Average HIHO coherence over transformed outputs."""
        try:
            import numpy as np
        except Exception:
            return 0.5
        hihos = []
        for ex in train:
            g = deepcopy(ex["input"])
            for _, op in program:
                g = op(g)
                if g is None:
                    break
            if g is not None:
                enc = self.codec.encode(g)
                hihos.append(enc.get("hiho", 0.5))
        return float(np.mean(hihos)) if hihos else 0.5

    def _compute_latent_delta(
        self, train: list[dict[str, Grid]], program: list[tuple[str, Program]]
    ) -> list[float]:
        """Mean latent_12 delta between input and output across train examples."""
        try:
            import numpy as np
        except Exception:
            return [0.0] * 12
        deltas = []
        for ex in train:
            g = deepcopy(ex["input"])
            for _, op in program:
                g = op(g)
                if g is None:
                    break
            if g is not None:
                enc_in = self.codec.encode(ex["input"])
                enc_out = self.codec.encode(g)
                if enc_in.get("latent_12") is not None and enc_out.get("latent_12") is not None:
                    deltas.append(np.array(enc_out["latent_12"]) - np.array(enc_in["latent_12"]))
        if not deltas:
            return [0.0] * 12
        mean = np.mean(deltas, axis=0)
        return [round(float(v), 6) for v in mean.tolist()]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def save_rules(self, rules: list[CompoundRule], path: str | Path) -> None:
        Path(path).write_text(json.dumps([r.to_dict() for r in rules], indent=2))

    def load_rules(self, path: str | Path) -> list[CompoundRule]:
        data = json.loads(Path(path).read_text())
        return [CompoundRule.from_dict(d) for d in data]


# ---------------------------------------------------------------------------
# CLI sanity check
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simple synthetic task: invert colors
    task = {
        "train": [
            {"input": [[0, 1, 0], [1, 0, 1]], "output": [[1, 0, 1], [0, 1, 0]]},
            {"input": [[1, 1], [0, 0]], "output": [[0, 0], [1, 1]]},
        ],
        "test": [{"input": [[0, 0, 1], [1, 0, 0]], "output": [[0, 0, 0]]}],
    }
    extractor = PatternExtractor(max_depth=1, budget_per_strategy=200)
    rules = extractor.extract(task)
    print(f"Extracted {len(rules)} rule(s)")
    for r in rules:
        hiho = r.hiho_score
        print(f"  {r.name} | conf={r.confidence:.2f} | votes={r.strategy_votes} | hiho={hiho:.3f}")
    # Expect invert to appear with high confidence
    if not any("invert" in r.name for r in rules):
        raise SystemExit("Expected invert rule not found")
    print("PatternExtractor OK")
