"""ARC Grid Processing Pipeline.

Unified grid encoder/decoder for ARC JSON format with FLUME-compatible
256-D latent vectors, HIHO coherence scoring, and deterministic hashing.

Uses V-Model decomposition:
- Requirements: deterministic encode/decode, 0..9 colors, <=30x30
- Architecture: ARCCodec with pure-NumPy fast path + optional torch bridge
- Implementation: see codec.py (existing)
- Verification: round-trip invariant checked below
- Validation: grids_equal harness with property-based checks
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


try:
    import numpy as np
except Exception:
    np = None  # type: ignore[misc]

from cohezion.arc.codec import MAX_SIZE, NUM_COLORS, ARCCodec, Grid, grids_equal


def encode_grid(grid: Grid) -> dict[str, Any]:
    """Encode a single ARC grid to structured dict.

    Returns shape, flat padded array, normalized tensor, latent vectors,
    HIHO coherence, color palette, and SHA-256 hash.
    """
    codec = ARCCodec()
    return codec.encode(grid)


def decode_grid(encoded: dict[str, Any]) -> Grid:
    """Decode encoded grid back to list-of-lists 0..9."""
    codec = ARCCodec()
    return codec.decode(encoded)


def decode_from_latent(latent_256: Any, shape: tuple[int, int]) -> Grid:
    """Reconstruct grid from 256-D latent (lossy but useful for probes)."""
    codec = ARCCodec()
    return codec.decode_from_latent(latent_256, shape)


def validate_grid(grid: Any) -> tuple[bool, str]:
    """Validate ARC grid invariants.  Returns (valid, reason)."""
    if not isinstance(grid, list) or not grid:
        return False, "grid must be non-empty list of lists"
    rows = len(grid)
    if rows > MAX_SIZE:
        return False, f"rows {rows} > max {MAX_SIZE}"
    cols = len(grid[0]) if rows > 0 else 0
    if cols > MAX_SIZE:
        return False, f"cols {cols} > max {MAX_SIZE}"
    for ri, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != cols:
            return False, f"row {ri} length mismatch (expected {cols})"
        for ci, v in enumerate(row):
            if not isinstance(v, int) or not (0 <= v <= NUM_COLORS - 1):
                return False, f"cell ({ri},{ci}) value {v} out of range 0..9"
    return True, "ok"


def batch_encode(grids: list[Grid]) -> list[dict[str, Any]]:
    """Batch encode multiple grids."""
    codec = ARCCodec()
    return codec.encode_batch(grids)


def batch_decode(encodeds: list[dict[str, Any]]) -> list[Grid]:
    """Batch decode multiple grids."""
    codec = ARCCodec()
    return codec.decode_batch(encodeds)


def grid_hash(grid: Grid) -> str:
    """Deterministic SHA-256 hex digest of a grid."""
    return hashlib.sha256(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()


def grid_summary(grid: Grid) -> dict[str, Any]:
    """Human-readable summary of grid properties."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    colors: set[int] = set()
    for row in grid:
        colors.update(row)
    return {
        "shape": (rows, cols),
        "unique_colors": sorted(colors),
        "color_count": len(colors),
        "hash": grid_hash(grid)[:16],
    }


# ---------------------------------------------------------------------------
# V-Model Verification Harness
# ---------------------------------------------------------------------------


def verify_roundtrip(grid: Grid) -> tuple[bool, str]:
    """Unit verification: encode then decode returns identical grid."""
    enc = encode_grid(grid)
    dec = decode_grid(enc)
    if grids_equal(grid, dec):
        return True, "roundtrip OK"
    return False, f"roundtrip mismatch: {grid} != {dec}"


def verify_pipeline_sanity() -> dict[str, Any]:
    """System validation: run property-based checks across sample grids."""
    samples = [
        [[1, 2], [3, 4]],
        [[0] * 30 for _ in range(30)],
        [[i % 10 for i in range(30)] for _ in range(30)],
        [[7]],
        [[5, 5, 5], [5, 0, 5], [5, 5, 5]],
    ]
    results = {}
    all_ok = True
    for idx, g in enumerate(samples):
        ok, msg = verify_roundtrip(g)
        results[f"sample_{idx}"] = {"ok": ok, "msg": msg}
        all_ok = all_ok and ok
    return {"all_ok": all_ok, "results": results}


if __name__ == "__main__":
    result = verify_pipeline_sanity()
    print(json.dumps(result, indent=2))
    if not result["all_ok"]:
        raise SystemExit(1)
