"""Verified neuro-symbolic DSL synthesizer for ARC attempt_2 (numpy + stdlib only).

Contract (Monotonic Improvement Invariant): attempt_1 is NEVER modified. attempt_2 is replaced
only when a program reproduces 100% of the demonstration pairs exactly AND its test output
differs from attempt_1 AND the MDL-weighted posterior confidence clears `min_conf`.

    p* = argmin_{p in P : p(x_i)=y_i for all i}  len(p)        (len = description length, bits)
    y^ = argmax_y  sum_{distinct behaviours b: b(x*)=y} 2^-len(b)   (Occam-weighted vote)

Run `python arc_dsl_attempt2.py --self-test` for the discriminating tests.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


Grid = np.ndarray
_GUARD_ERRORS = (ValueError, KeyError, IndexError, ZeroDivisionError)
PRIM_BITS = 6.0  # ~log2(|primitive set|)
COLOR_BITS = 3.3  # log2(10)


# --------------------------------------------------------------------------- grid utilities
def bg_of(g: Grid) -> int:
    vals, counts = np.unique(g, return_counts=True)
    return int(vals[counts.argmax()])


@dataclass
class Comp:
    color: int
    cells: np.ndarray  # (N, 2) row, col

    @property
    def size(self) -> int:
        return len(self.cells)

    @property
    def r0(self) -> int:
        return int(self.cells[:, 0].min())

    @property
    def r1(self) -> int:
        return int(self.cells[:, 0].max())

    @property
    def c0(self) -> int:
        return int(self.cells[:, 1].min())

    @property
    def c1(self) -> int:
        return int(self.cells[:, 1].max())

    @property
    def h(self) -> int:
        return self.r1 - self.r0 + 1

    @property
    def w(self) -> int:
        return self.c1 - self.c0 + 1

    def touches_border(self, h: int, w: int) -> bool:
        return self.r0 == 0 or self.c0 == 0 or self.r1 == h - 1 or self.c1 == w - 1


def components(g: Grid, bg: int, conn: int = 4, multicolor: bool = False) -> list[Comp]:
    h, w = g.shape
    seen = np.zeros((h, w), bool)
    nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        nbrs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    out: list[Comp] = []
    for r in range(h):
        for c in range(w):
            if seen[r, c] or g[r, c] == bg:
                continue
            col = g[r, c]
            stack, cells = [(r, c)], []
            seen[r, c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in nbrs:
                    ny, nx = y + dy, x + dx
                    if (
                        0 <= ny < h
                        and 0 <= nx < w
                        and not seen[ny, nx]
                        and g[ny, nx] != bg
                        and (multicolor or g[ny, nx] == col)
                    ):
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            out.append(Comp(int(col), np.array(cells)))
    return out


# --------------------------------------------------------------------------- parameter-free primitives
def _grav_down(g: Grid) -> Grid:
    bg = bg_of(g)
    out = np.full_like(g, bg)
    for c in range(g.shape[1]):
        keep = g[:, c][g[:, c] != bg]
        if len(keep):
            out[-len(keep) :, c] = keep
    return out


def _crop_nonbg(g: Grid) -> Grid:
    rr, cc = np.where(g != bg_of(g))
    if not len(rr):
        raise ValueError("empty")
    return g[rr.min() : rr.max() + 1, cc.min() : cc.max() + 1]


def _crop_comp(pick: Callable) -> Callable[[Grid], Grid]:
    def f(g: Grid) -> Grid:
        comps = components(g, bg_of(g), 8, multicolor=True)
        if not comps:
            raise ValueError("no comps")
        sizes = [c.size for c in comps]
        best = pick(sizes)
        if sizes.count(best) != 1:
            raise ValueError("ambiguous pick")  # tie => refuse, never guess
        c = comps[sizes.index(best)]
        return g[c.r0 : c.r1 + 1, c.c0 : c.c1 + 1]

    return f


def _remove_small(k: int) -> Callable[[Grid], Grid]:
    def f(g: Grid) -> Grid:
        bg, out = bg_of(g), g.copy()
        for c in components(g, bg, 8):
            if c.size <= k:
                out[c.cells[:, 0], c.cells[:, 1]] = bg
        return out

    return f


def _fill_enclosed(color: int) -> Callable[[Grid], Grid]:
    def f(g: Grid) -> Grid:
        bg, (h, w) = bg_of(g), g.shape
        reach = np.zeros((h, w), bool)
        stack = [
            (r, c)
            for r in range(h)
            for c in range(w)
            if (r in (0, h - 1) or c in (0, w - 1)) and g[r, c] == bg
        ]
        for p in stack:
            reach[p] = True
        while stack:
            y, x = stack.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not reach[ny, nx] and g[ny, nx] == bg:
                    reach[ny, nx] = True
                    stack.append((ny, nx))
        out = g.copy()
        out[(g == bg) & ~reach] = color
        return out

    return f


def _bbox_fill(color: int) -> Callable[[Grid], Grid]:
    def f(g: Grid) -> Grid:
        bg, out = bg_of(g), g.copy()
        for c in components(g, bg, 8, multicolor=True):
            sub = out[c.r0 : c.r1 + 1, c.c0 : c.c1 + 1]
            sub[sub == bg] = color
        return out

    return f


def _halo(color: int) -> Callable[[Grid], Grid]:
    def f(g: Grid) -> Grid:
        bg, (h, w) = bg_of(g), g.shape
        fg = np.pad(g != bg, 1)
        near = np.zeros((h, w), bool)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near |= fg[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        out = g.copy()
        out[near & (g == bg)] = color
        return out

    return f


def _upscale(k: int) -> Callable[[Grid], Grid]:
    return lambda g: np.kron(g, np.ones((k, k), dtype=g.dtype))


def _tile(fn_h, fn_v) -> Callable[[Grid], Grid]:
    return lambda g: np.vstack([np.hstack([g, fn_h(g)]), np.hstack([fn_v(g), fn_h(fn_v(g))])])


def _partner_maps(h: int, w: int):
    """Candidate reflection symmetries with unknown axis offset (lr, ud, diagonal)."""
    R, C = np.indices((h, w))
    for s in range(1, 2 * w - 2):
        yield "lr", R, s - C
    for s in range(1, 2 * h - 2):
        yield "ud", s - R, C
    if h == w:
        yield "diag", C, R
        yield "diag", h - 1 - C, w - 1 - R


def _sym_fill(mask_color: int, crop: bool) -> Callable[[Grid], Grid]:
    """Fill `mask_color` cells from VERIFIED symmetries (100% agreement on overlapping known cells)."""

    def f(g: Grid) -> Grid:
        mask = g == mask_color
        if not mask.any() or mask.all():
            raise ValueError("no mask")
        h, w = g.shape
        known = ~mask

        def verified(Rp, Cp):
            v = (Rp >= 0) & (Rp < h) & (Cp >= 0) & (Cp < w)
            Rc, Cc = np.clip(Rp, 0, h - 1), np.clip(Cp, 0, w - 1)
            both = v & known & known[Rc, Cc]
            if both.sum() < max(6, 0.25 * known.sum()):  # vacuous symmetries are not evidence
                return None
            if (g[both] != g[Rc, Cc][both]).any():  # one disagreement kills the hypothesis
                return None
            return v, Rc, Cc

        syms, lrs, uds = [], [], []
        for kind, Rp, Cp in _partner_maps(h, w):
            s = verified(Rp, Cp)
            if s is not None:
                syms.append(s)
                {"lr": lrs, "ud": uds}.get(kind, []).append((Rp, Cp))
        for (_, Cl), (Ru, _) in (
            (a, b) for a in lrs for b in uds
        ):  # rot180 = lr∘ud, needed when mask meets its mirror
            s = verified(Ru, Cl)
            if s is not None:
                syms.append(s)
        if not syms:
            raise ValueError("no symmetry")
        out, cur = g.copy(), mask.copy()
        for _ in range(4):
            changed = False
            for v, Rc, Cc in syms:
                fillable = cur & v & ~cur[Rc, Cc]
                if fillable.any():
                    out[fillable] = out[Rc, Cc][fillable]
                    cur &= ~fillable
                    changed = True
            if not changed or not cur.any():
                break
        if cur.any():
            raise ValueError("incomplete fill")  # never emit a half-completed grid
        if crop:
            rr, cc = np.where(mask)
            return out[rr.min() : rr.max() + 1, cc.min() : cc.max() + 1]
        return out

    return f


def build_prims(in_colors: set[int], out_colors: set[int]) -> list[tuple[str, Callable, float]]:
    d4 = {
        "rot90": lambda g: np.rot90(g, 1),
        "rot180": lambda g: np.rot90(g, 2),
        "rot270": lambda g: np.rot90(g, 3),
        "flipud": np.flipud,
        "fliplr": np.fliplr,
        "T": lambda g: g.T,
        "antiT": lambda g: np.rot90(g, 2).T,
    }
    P: list[tuple[str, Callable, float]] = [(n, f, PRIM_BITS) for n, f in d4.items()]
    P += [
        ("grav_down", _grav_down, PRIM_BITS),
        ("grav_up", lambda g: np.flipud(_grav_down(np.flipud(g))), PRIM_BITS),
        ("grav_right", lambda g: _grav_down(g.T).T, PRIM_BITS),
        ("grav_left", lambda g: np.fliplr(_grav_down(np.fliplr(g).T).T), PRIM_BITS),
        ("crop_nonbg", _crop_nonbg, PRIM_BITS),
        ("crop_largest", _crop_comp(max), PRIM_BITS),
        ("crop_smallest", _crop_comp(min), PRIM_BITS),
        ("rm_small1", _remove_small(1), PRIM_BITS),
        ("rm_small2", _remove_small(2), PRIM_BITS),
        ("up2", _upscale(2), PRIM_BITS),
        ("up3", _upscale(3), PRIM_BITS),
        ("tile_plain", lambda g: np.tile(g, (2, 2)), PRIM_BITS),
        ("tile_mirror", _tile(np.fliplr, np.flipud), PRIM_BITS),
        ("mirror_h", lambda g: np.hstack([g, np.fliplr(g)]), PRIM_BITS),
        ("mirror_v", lambda g: np.vstack([g, np.flipud(g)]), PRIM_BITS),
    ]
    for c in sorted(out_colors):
        P += [
            (f"fill_enclosed({c})", _fill_enclosed(c), PRIM_BITS + COLOR_BITS),
            (f"bbox_fill({c})", _bbox_fill(c), PRIM_BITS + COLOR_BITS),
            (f"halo({c})", _halo(c), PRIM_BITS + COLOR_BITS),
        ]
    for m in sorted(in_colors):
        P += [
            (f"sym_fill({m})", _sym_fill(m, False), PRIM_BITS + COLOR_BITS),
            (f"sym_crop({m})", _sym_fill(m, True), PRIM_BITS + COLOR_BITS),
        ]
    return P


# --------------------------------------------------------------------------- learned terminals
Terminal = Optional[tuple[float, Callable[[Grid], Grid]]]


def term_exact(mids, ys) -> Terminal:
    ok = all(m.shape == y.shape and np.array_equal(m, y) for m, y in zip(mids, ys))
    return (0.0, lambda g: g) if ok else None


def term_cmap(mids, ys) -> Terminal:
    if any(m.shape != y.shape for m, y in zip(mids, ys)):
        return None
    table: dict[int, int] = {}
    for m, y in zip(mids, ys):
        for a, b in zip(m.ravel().tolist(), y.ravel().tolist()):
            if table.setdefault(a, b) != b:
                return None
    moved = {a: b for a, b in table.items() if a != b}
    if not moved:
        return None
    return 2 + COLOR_BITS * len(moved), lambda g: np.vectorize(lambda v: moved.get(int(v), int(v)))(
        g
    )


def _nbr_keys(g: Grid, mode: str) -> list[tuple]:
    p = np.pad(g, 1, constant_values=-1)
    h, w = g.shape
    offs = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
    if mode.startswith("n8"):
        offs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    st = np.stack([p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] for dy, dx in offs], -1)
    rows = st.reshape(h * w, -1).tolist()
    if mode.endswith(
        "set"
    ):  # position-free abstraction: (centre, SET of neighbour colours) generalises further
        return [(r[0], tuple(sorted({v for v in r[1:] if v >= 0}))) for r in rows]
    return [tuple(r) for r in rows]


def term_ca(mode: str) -> Callable:
    def fit(mids, ys) -> Terminal:
        if len(mids) < 2 or any(m.shape != y.shape for m, y in zip(mids, ys)):
            return None
        table: dict[tuple, int] = {}
        for m, y in zip(mids, ys):
            for k, v in zip(_nbr_keys(m, mode), y.ravel().tolist()):
                if table.setdefault(k, v) != v:
                    return None
        if all(k[0] == v for k, v in table.items()):
            return None  # identity rule

        def apply(g: Grid) -> Grid:
            keys = _nbr_keys(g, mode)
            if any(k not in table for k in keys):
                raise KeyError("unseen neighbourhood")  # COVERAGE GUARD: no extrapolation
            return np.array([table[k] for k in keys]).reshape(g.shape)

        return 8 + 2.0 * len(table), apply

    return fit


def _comp_feats(comps: list[Comp], shape) -> list[dict]:
    sizes = [c.size for c in comps]
    mx, mn = max(sizes), min(sizes)
    return [
        {
            "size": c.size,
            "is_max": c.size == mx,
            "is_min": c.size == mn,
            "border": c.touches_border(*shape),
            "height": c.h,
            "width": c.w,
            "is_rect": c.size == c.h * c.w,
        }
        for c in comps
    ]


def term_recolor(feat: str) -> Callable:
    def fit(mids, ys) -> Terminal:
        if any(m.shape != y.shape for m, y in zip(mids, ys)):
            return None
        table: dict = {}
        changed = False
        for m, y in zip(mids, ys):
            bg = bg_of(m)
            comps = components(m, bg, 4)
            if not comps:
                return None
            covered = np.zeros(m.shape, bool)
            for c, f in zip(comps, _comp_feats(comps, m.shape)):
                tgt = np.unique(y[c.cells[:, 0], c.cells[:, 1]])
                if len(tgt) != 1 or table.setdefault(f[feat], int(tgt[0])) != int(tgt[0]):
                    return None
                changed |= int(tgt[0]) != c.color
                covered[c.cells[:, 0], c.cells[:, 1]] = True
            if not np.array_equal(m[~covered], y[~covered]):
                return None
        if not changed:
            return None

        def apply(g: Grid) -> Grid:
            out, bg = g.copy(), bg_of(g)
            comps = components(g, bg, 4)
            for c, f in zip(comps, _comp_feats(comps, g.shape) if comps else []):
                out[c.cells[:, 0], c.cells[:, 1]] = table[
                    f[feat]
                ]  # KeyError => unseen feature value
            return out

        return 8 + COLOR_BITS * len(table), apply

    return fit


TERMINALS_ALL = [
    ("exact", term_exact),
    ("cmap", term_cmap),
    ("ca4", term_ca("n4")),
    ("ca8", term_ca("n8")),
    ("ca4set", term_ca("n4set")),
    ("ca8set", term_ca("n8set")),
] + [
    (f"recolor_{f}", term_recolor(f))
    for f in ("size", "is_max", "is_min", "border", "height", "width", "is_rect")
]
TERMINALS_DEEP = TERMINALS_ALL[:2]


# --------------------------------------------------------------------------- synthesis
@dataclass
class Candidate:
    cost: float
    name: str
    apply: Callable[[Grid], Grid]


@dataclass
class Result:
    grid: Grid | None
    confidence: float
    program: str
    n_programs: int


def _valid(g) -> bool:
    return (
        isinstance(g, np.ndarray)
        and g.ndim == 2
        and 1 <= g.shape[0] <= 30
        and 1 <= g.shape[1] <= 30
        and g.min() >= 0
        and g.max() <= 9
    )


def _chain(fns, g):
    for f in fns:
        g = f(g)
    return np.asarray(g)


def find_programs(
    train: list[tuple[Grid, Grid]], budget_s: float = 6.0, max_depth: int = 2
) -> list[Candidate]:
    xs, ys = [x for x, _ in train], [y for _, y in train]
    deadline = time.monotonic() + budget_s
    prims = build_prims(
        {int(v) for x in xs for v in np.unique(x)}, {int(v) for y in ys for v in np.unique(y)}
    )
    d4_names = {"rot90", "rot180", "rot270", "flipud", "fliplr", "T", "antiT"}
    cands: list[Candidate] = []

    def run_terminals(names, fns, cost, mids, terminals):
        if not names and terminals is TERMINALS_ALL:
            terminals = TERMINALS_ALL[1:]  # empty prefix + exact == identity task: reject
        for tname, fit in terminals:
            try:
                t = fit(mids, ys)
            except _GUARD_ERRORS:
                t = None
            if t is not None:
                tc, tf = t
                cands.append(
                    Candidate(
                        cost + tc,
                        "∘".join(names + [tname]) or tname,
                        (lambda fs, tf_: lambda g: tf_(_chain(fs, g)))(list(fns), tf),
                    )
                )

    def apply_all(f, mids):
        try:
            out = [np.asarray(f(m)) for m in mids]
        except _GUARD_ERRORS:
            return None
        return out if all(_valid(o) for o in out) else None

    run_terminals([], [], 0.0, xs, TERMINALS_ALL)
    level1 = []
    for n, f, c in prims:
        if time.monotonic() > deadline:
            break
        m1 = apply_all(f, xs)
        if m1 is None:
            continue
        level1.append((n, f, c, m1))
        run_terminals([n], [f], c, m1, TERMINALS_ALL)
    if max_depth >= 2:
        for n1, f1, c1, m1 in level1:
            for n2, f2, c2 in prims:
                if time.monotonic() > deadline:
                    return cands
                if n1 in d4_names and n2 in d4_names:
                    continue  # D4 is a group: compositions are already depth-1
                m2 = apply_all(f2, m1)
                if m2 is None:
                    continue
                run_terminals([n1, n2], [f1, f2], c1 + c2, m2, TERMINALS_DEEP)
    return cands


def solve_task(
    train: list[tuple[Grid, Grid]], tests: list[Grid], budget_s: float = 6.0
) -> list[Result]:
    cands = find_programs(train, budget_s)
    results: list[Result] = []
    for x in tests:
        behaviours: dict[bytes, tuple[float, str, Grid]] = {}
        for c in cands:
            try:
                out = np.asarray(c.apply(x))
            except _GUARD_ERRORS:
                continue
            if not _valid(out):
                continue
            key = bytes(out.shape) + out.astype(np.uint8).tobytes()
            if key not in behaviours or c.cost < behaviours[key][0]:
                behaviours[key] = (
                    c.cost,
                    c.name,
                    out,
                )  # equivalent programs count ONCE (max, not sum)
        if not behaviours:
            results.append(Result(None, 0.0, "", len(cands)))
            continue
        cmin = min(v[0] for v in behaviours.values())
        weights = {k: 2.0 ** (-(v[0] - cmin)) for k, v in behaviours.items()}
        best = max(weights, key=lambda k: weights[k])
        results.append(
            Result(
                behaviours[best][2],
                weights[best] / sum(weights.values()),
                behaviours[best][1],
                len(cands),
            )
        )
    return results


# --------------------------------------------------------------------------- attempt_2 placement
def merge_attempts(a1: list, a2: list, dsl: Grid | None, conf: float, min_conf: float = 0.5):
    """Returns (attempt_1, attempt_2). attempt_1 is returned untouched (same object)."""
    if dsl is None or conf < min_conf:
        return a1, a2
    if np.array_equal(np.asarray(a1), dsl):
        return a1, a2  # DSL agrees with the neural top pick: keep neural diversity in slot 2
    return a1, dsl.tolist()


def apply_dsl_to_submission(
    challenges: dict, submission: dict, budget_s: float = 6.0, min_conf: float = 0.5
) -> tuple[dict, dict]:
    new, stats = json.loads(json.dumps(submission)), {"tasks": 0, "replaced": 0, "solved_train": 0}
    for tid, task in challenges.items():
        stats["tasks"] += 1
        train = [(np.array(p["input"]), np.array(p["output"])) for p in task["train"]]
        res = solve_task(train, [np.array(t["input"]) for t in task["test"]], budget_s)
        stats["solved_train"] += any(r.grid is not None for r in res)
        for i, r in enumerate(res):
            slot = new[tid][i]
            a1_before = json.dumps(slot["attempt_1"])
            slot["attempt_1"], slot["attempt_2"] = merge_attempts(
                slot["attempt_1"], slot["attempt_2"], r.grid, r.confidence, min_conf
            )
            assert json.dumps(slot["attempt_1"]) == a1_before, "MONOTONIC INVARIANT VIOLATED"
            stats["replaced"] += slot["attempt_2"] != submission[tid][i]["attempt_2"]
    return new, stats


# --------------------------------------------------------------------------- self-test
def _pairs(fn, grids):
    return [(g, fn(g)) for g in grids]


def self_test() -> None:
    rng = np.random.default_rng(0)
    rnd = lambda h, w, k=4, p=0.3: np.where(rng.random((h, w)) < p, rng.integers(1, k, (h, w)), 0)
    grids = [rnd(7, 7) for _ in range(5)]
    checks = []

    def case(name, fn, expect_solved=True, train_grids=None):
        gs = train_grids or grids
        res = solve_task(_pairs(fn, gs[:-1]), [gs[-1]], budget_s=8)[0]
        ok = (
            (res.grid is not None and np.array_equal(res.grid, fn(gs[-1])))
            if expect_solved
            else res.grid is None
        )
        checks.append((name, ok, res.program, round(res.confidence, 2)))

    case("gravity_down", _grav_down)
    case("flip+colormap", lambda g: np.where(np.fliplr(g) == 1, 5, np.fliplr(g)))
    case("fill_enclosed", _fill_enclosed(4))

    # enclosed-fill needs rings: build explicit
    def ring(sz):
        g = np.zeros((9, 9), int)
        o = rng.integers(0, 9 - sz)
        g[o : o + sz, o : o + sz] = 1
        g[o + 1 : o + sz - 1, o + 1 : o + sz - 1] = 0
        return g

    ringg = [ring(s) for s in (4, 5, 6, 5, 4)]
    case("ring_fill", _fill_enclosed(4), train_grids=ringg)

    def symgrid():
        q = rng.integers(1, 5, (4, 4))
        a = np.hstack([q, np.fliplr(q)])
        return np.vstack([a, np.flipud(a)])

    sg = [symgrid() for _ in range(5)]
    masked = []
    for g in sg:
        m = g.copy()
        r, c = rng.choice(
            [0, 1, 4, 5], 2
        )  # avoid masks covering a cell AND all its mirrors (unrecoverable)
        m[r : r + 3, c : c + 3] = 9
        masked.append((m, g))
    res = solve_task(masked[:-1], [masked[-1][0]], 8)[0]
    checks.append(
        (
            "symmetry_completion",
            res.grid is not None and np.array_equal(res.grid, masked[-1][1]),
            res.program,
            round(res.confidence, 2),
        )
    )

    def size_recolor(g):
        out = g.copy()
        comps = components(g, 0, 4)
        for c in comps:
            out[c.cells[:, 0], c.cells[:, 1]] = (
                6 if c.size == max(k.size for k in comps) else c.color
            )
        return out

    blobs = [np.where(rng.random((8, 8)) < 0.35, 1, 0) for _ in range(6)]
    case("recolor_largest", size_recolor, train_grids=blobs)

    # CA: cells 4-adjacent to color-1 cell become 2
    def ca(g):
        p = np.pad(g == 1, 1)
        n = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        return np.where((g == 0) & n, 2, g)

    case(
        "ca_neighbour_rule",
        ca,
        train_grids=[np.where(rng.random((9, 9)) < 0.15, 1, 0) for _ in range(7)],
    )

    # NEGATIVE CONTROLS -- the guards must say NO
    perm = rng.integers(0, 10, (7, 7))
    case("neg_random_mapping_unsolvable", lambda g: (g * 7 + perm) % 10, expect_solved=False)
    # coverage guard: CA fitted on tiny sparse data must not extrapolate to a dense unseen test grid
    tr = _pairs(ca, [np.where(rng.random((6, 6)) < 0.1, 1, 0) for _ in range(2)])
    dense = rng.integers(0, 4, (6, 6))
    r = solve_task(tr, [dense], 8)[0]
    checks.append(
        (
            "neg_ca_coverage_guard",
            r.grid is None or not r.program.startswith("ca"),
            r.program,
            round(r.confidence, 2),
        )
    )

    # Monotonic invariant + placement semantics
    a1, a2 = [[1, 2]], [[3, 4]]
    o1, o2 = merge_attempts(a1, a2, np.array([[9, 9]]), 0.9)
    checks.append(("merge_keeps_attempt_1_replaces_2", o1 is a1 and o2 == [[9, 9]], "", 0))
    o1, o2 = merge_attempts(a1, a2, np.array([[1, 2]]), 0.9)
    checks.append(("merge_dsl_equals_a1_keeps_neural_a2", o1 is a1 and o2 == a2, "", 0))
    o1, o2 = merge_attempts(a1, a2, np.array([[9, 9]]), 0.1)
    checks.append(("merge_low_conf_noop", o2 == a2, "", 0))

    for name, ok, prog, conf in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name:42s} {prog} conf={conf}")
    assert all(ok for _, ok, _, _ in checks), "SELF-TEST FAILED"
    print(f"{len(checks)}/{len(checks)} passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--challenges"), ap.add_argument("--submission"), ap.add_argument("--out")
    (
        ap.add_argument("--budget", type=float, default=6.0),
        ap.add_argument("--min-conf", type=float, default=0.5),
    )
    a = ap.parse_args()
    if a.self_test:
        self_test()
    else:
        new, st = apply_dsl_to_submission(
            json.loads(Path(a.challenges).read_text()),
            json.loads(Path(a.submission).read_text()),
            a.budget,
            a.min_conf,
        )
        Path(a.out).write_text(json.dumps(new))
        print(st)
