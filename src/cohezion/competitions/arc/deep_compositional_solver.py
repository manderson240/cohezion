"""Deep 3-Stage Compositional Program Synthesizer (Breadth & Depth).

Searches over:
- 1-Stage Direct Primitives
- 2-Stage Chains: f_2(f_1(x))
- 3-Stage Chains: f_3(f_2(f_1(x)))
- Object-Centric Operations (Filtering by Area, Cropping Objects, Color Remapping)
"""

from __future__ import annotations

from typing import Any, Callable
from cohezion.competitions.arc.dsl_synthesizer import DSL_PRIMITIVES, get_dims, MAX_DIM
from cohezion.competitions.arc.frontier_arc_primitives import (
    sort_components_by_area, geodesic_bfs_propagation, conv_pattern_replacement
)
from cohezion.competitions.arc.grandmaster_color_remap import solve_color_remapping_task
from cohezion.competitions.arc.object_dsl_engine import (
    filter_largest_object_only, filter_smallest_object_only,
    crop_largest_object, sort_objects_horizontally
)

from cohezion.competitions.arc.grandmaster_gap_filler import (
    solve_cellular_automata_moore, solve_fractal_kronecker_inflation
)

EXPANDED_PRIMITIVES: list[tuple[str, Callable[[list[list[int]]], list[list[int]]]]] = list(DSL_PRIMITIVES) + [
    ("ccl_sort_area", sort_components_by_area),
    ("geodesic_bfs", geodesic_bfs_propagation),
    ("conv_stencil_cross", conv_pattern_replacement),
    ("filter_largest", filter_largest_object_only),
    ("filter_smallest", filter_smallest_object_only),
    ("crop_largest", crop_largest_object),
    ("sort_horizontally", sort_objects_horizontally),
    ("cellular_automata_moore", solve_cellular_automata_moore),
    ("fractal_kronecker_inflation", solve_fractal_kronecker_inflation),
]

class DeepCompositionalSynthesizer:
    def __init__(self) -> None:
        self.primitives = EXPANDED_PRIMITIVES

    def solve(self, task: dict[str, Any]) -> list[list[int]]:
        train = task.get("train", [])
        test_in = task.get("test", [{}])[0].get("input", [[0]])

        # 0. Color Remap Fast Path
        remap_res = solve_color_remapping_task(task)
        if remap_res is not None:
            return remap_res

        # 1. 1-Stage Search (Breadth)
        for _, fn in self.primitives:
            if self._matches(train, fn):
                try:
                    res = fn(test_in)
                    if self._valid(res):
                        return res
                except Exception:
                    pass

        # 2. 2-Stage Compositional Search (Breadth + Depth)
        for _, f1 in self.primitives:
            for _, f2 in self.primitives:
                if self._matches(train, lambda g, fn1=f1, fn2=f2: fn2(fn1(g))):
                    try:
                        res = f2(f1(test_in))
                        if self._valid(res):
                            return res
                    except Exception:
                        pass

        # 3. 3-Stage Fast Compositional Search (High-leverage triples)
        core_fns = [fn for name, fn in self.primitives if any(k in name for k in ["rot", "flip", "crop", "filter", "gravity"])]
        for f1 in core_fns:
            for f2 in core_fns:
                for f3 in core_fns:
                    if self._matches(train, lambda g, fn1=f1, fn2=f2, fn3=f3: fn3(fn2(fn1(g)))):
                        try:
                            res = f3(f2(f1(test_in)))
                            if self._valid(res):
                                return res
                        except Exception:
                            pass

        return [r[:] for r in test_in] if test_in else [[0]]

    @staticmethod
    def _matches(train: list[dict], fn: Callable) -> bool:
        for p in train:
            try:
                if fn(p.get("input", [])) != p.get("output", []):
                    return False
            except Exception:
                return False
        return True

    @staticmethod
    def _valid(grid: list[list[int]]) -> bool:
        h, w = get_dims(grid)
        return 1 <= h <= MAX_DIM and 1 <= w <= MAX_DIM
