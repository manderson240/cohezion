"""ARC Color Mapping & Exact Permutation Synthesizer.

Solves the large class of ARC tasks where shapes are preserved but colors are remapped
via discrete substitution functions f(c_in) -> c_out.
"""

from typing import Any, Callable

def solve_color_remapping_task(task: dict[str, Any]) -> list[list[int]] | None:
    train = task.get("train", [])
    test_in = task.get("test", [{}])[0].get("input", [[0]])
    if not train:
        return None

    # Check if all train pairs preserve dimensions exactly
    for p in train:
        inp = p.get("input", [])
        out = p.get("output", [])
        if len(inp) != len(out) or len(inp[0]) != len(out[0]):
            return None

    # Learn deterministic color map
    color_map = {}
    for p in train:
        inp = p.get("input", [])
        out = p.get("output", [])
        h, w = len(inp), len(inp[0])
        for r in range(h):
            for c in range(w):
                src = inp[r][c]
                dst = out[r][c]
                if src in color_map and color_map[src] != dst:
                    # Inconsistent color mapping
                    return None
                color_map[src] = dst

    # Apply color map to test input
    res = []
    for row in test_in:
        res.append([color_map.get(c, c) for c in row])
    return res
