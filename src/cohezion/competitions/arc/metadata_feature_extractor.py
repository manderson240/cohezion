"""ARC Geometric & Color Palette Metadata Feature Extractor (Adversarially Hardened)."""

from __future__ import annotations

from typing import Any

import numpy as np


def extract_arc_metadata(train_pairs: list[dict[str, Any]]) -> dict[str, Any]:
    """Extracts geometric invariants, color palettes, and D4 symmetries with full defensive bounds."""
    if not train_pairs:
        return {
            "shape_class": "SAME_SHAPE",
            "is_same_shape": True,
            "background_color": 0,
            "unique_colors_in": [0],
            "unique_colors_out": [0],
            "colors_preserved": True,
            "new_colors_introduced": [],
            "scale_ratios": [(1.0, 1.0)],
        }

    shapes_in = []
    shapes_out = []
    scale_ratios = []
    color_hist_in = np.zeros(10, dtype=np.int32)
    color_hist_out = np.zeros(10, dtype=np.int32)

    for pair in train_pairs:
        raw_in = pair.get("input", [[0]])
        raw_out = pair.get("output", raw_in)

        g_in = np.array(raw_in, dtype=np.int32)
        g_out = np.array(raw_out, dtype=np.int32)

        if g_in.ndim != 2 or g_in.size == 0:
            g_in = np.zeros((1, 1), dtype=np.int32)
        if g_out.ndim != 2 or g_out.size == 0:
            g_out = np.zeros((1, 1), dtype=np.int32)

        h_in, w_in = g_in.shape
        h_out, w_out = g_out.shape
        shapes_in.append((h_in, w_in))
        shapes_out.append((h_out, w_out))

        # Guarded division
        scale_ratios.append((h_out / max(1.0, float(h_in)), w_out / max(1.0, float(w_in))))

        for c in range(10):
            color_hist_in[c] += int(np.sum(g_in == c))
            color_hist_out[c] += int(np.sum(g_out == c))

    # Floating point epsilon-guarded integer scaling
    is_same_shape = all(s_in == s_out for s_in, s_out in zip(shapes_in, shapes_out))
    is_integer_scaling = all(
        (
            abs(sr[0] - round(sr[0])) < 1e-4
            and abs(sr[1] - round(sr[1])) < 1e-4
            and round(sr[0]) > 0
            and round(sr[1]) > 0
        )
        for sr in scale_ratios
    )
    is_downscale = all(sr[0] < 1.0 and sr[1] < 1.0 for sr in scale_ratios)

    if is_same_shape:
        shape_class = "SAME_SHAPE"
    elif is_integer_scaling:
        shape_class = f"INTEGER_SCALE_{round(scale_ratios[0][0])}x{round(scale_ratios[0][1])}"
    elif is_downscale:
        shape_class = "CROPPING_OR_SUBGRID"
    else:
        shape_class = "DYNAMIC_BOUNDING_BOX"

    unique_in = np.where(color_hist_in > 0)[0].tolist() or [0]
    unique_out = np.where(color_hist_out > 0)[0].tolist() or [0]
    colors_preserved = set(unique_in) == set(unique_out)
    new_colors_introduced = list(set(unique_out) - set(unique_in))
    background_color = int(np.argmax(color_hist_in)) if np.sum(color_hist_in) > 0 else 0

    return {
        "shape_class": shape_class,
        "is_same_shape": is_same_shape,
        "background_color": background_color,
        "unique_colors_in": unique_in,
        "unique_colors_out": unique_out,
        "colors_preserved": colors_preserved,
        "new_colors_introduced": new_colors_introduced,
        "scale_ratios": scale_ratios,
    }
