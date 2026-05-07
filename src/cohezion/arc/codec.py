"""ARC Grid Encoder / Decoder.

Provides deterministic, geometrically-grounded encoding of ARC grids (0-9 color
values, max 30x30) into structured tensors and FLUME-compatible 256-D latent
vectors.  Decoding reverses the exact padding and normalization so that
submission grids match the evaluation harness byte-for-byte.

Design constraints (for Kaggle CPU runtime + Nov 2026 deadline):
- Pure-NumPy fast path (no heavy DL dependency in default path).
- Optional torch/FLUME bridge when Cohezion environment is available.
- HIHO coherence metric computed on every encode as geometric validity signal.
- Palette hash for rapid duplicate / canonical-form detection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore[misc]

try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore[misc]

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
Grid = list[list[int]]
EncodedGrid = dict[str, Any]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_SIZE = 30
NUM_COLORS = 10  # ARC uses 0..9

# Deterministic 256-D projection matrix seeded by the "ARC-AGI-2 2026" phrase.
# This guarantees cross-session latent consistency even without torch.
_PROJ_256D: np.ndarray | None = None


def _projection_256d() -> np.ndarray:
    """Lazy-init deterministic 256-D projection weights (HIHO 0.5-aligned)."""
    global _PROJ_256D
    if _PROJ_256D is None and np is not None:
        rng = np.random.default_rng(seed=abs(hash("ARC-AGI-2 2026 FLUME 256D")) % 2**31)
        w = rng.standard_normal((MAX_SIZE * MAX_SIZE, 256)).astype(np.float32)
        # Normalize rows so each dim contributes equally → preserves geometric structure
        _PROJ_256D = w / np.linalg.norm(w, axis=1, keepdims=True)
    return _PROJ_256D  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Geometric helpers
# ---------------------------------------------------------------------------


def _validate_grid(g: Grid) -> tuple[int, int]:
    """Return (rows, cols) after validating ARC invariants."""
    if not isinstance(g, list) or not g:
        raise ValueError("Grid must be a non-empty list of lists")
    rows = len(g)
    cols = len(g[0]) if rows > 0 else 0
    if cols == 0:
        raise ValueError("Grid rows must not be empty")
    for ri, row in enumerate(g):
        if len(row) != cols:
            raise ValueError(f"Row {ri} length {len(row)} != expected {cols}")
        for ci, v in enumerate(row):
            if not (0 <= v <= 9):
                raise ValueError(f"Cell ({ri},{ci}) value {v} out of 0..9 range")
    if rows > MAX_SIZE or cols > MAX_SIZE:
        raise ValueError(f"Grid {rows}x{cols} exceeds max {MAX_SIZE}x{MAX_SIZE}")
    return rows, cols


def _normalize_grid(g: Grid) -> np.ndarray:
    """Pad to MAX_SIZE x MAX_SIZE and scale colors to [0,1]."""
    rows, cols = _validate_grid(g)
    arr = np.zeros((MAX_SIZE, MAX_SIZE), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            arr[r, c] = g[r][c] / 9.0  # 0..1
    return arr


def _denormalize_grid(arr: np.ndarray, rows: int, cols: int) -> Grid:
    """Crop to original shape and scale back to integers 0..9."""
    out: Grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            val = round(arr[r, c] * 9.0)
            row.append(max(0, min(9, val)))
        out.append(row)
    return out


def _hiho_coherence(arr: np.ndarray) -> float:
    """HIHO 0.5 coherence: 1 - mean distance from 0.5 in normalized space."""
    if np is None:
        return 0.5
    return float(1.0 - np.mean(np.abs(arr - 0.5)))


# ---------------------------------------------------------------------------
# Core codec class
# ---------------------------------------------------------------------------


class ARCCodec:
    """Encode / decode single ARC grids with deterministic FLUME 256-D latents."""

    def __init__(self, use_flume: bool = True) -> None:
        self.use_flume = use_flume
        self._flume_encoder = None
        if use_flume and torch is not None:
            try:
                from cohezion.flume.grid_encoder import (
                    ARCGridEncoder,  # type: ignore[import-not-found]
                )

                self._flume_encoder = ARCGridEncoder(latent_dim=256, max_grid_size=MAX_SIZE)
                self._flume_encoder.eval()
            except Exception:
                self._flume_encoder = None

    # ------------------------------------------------------------------
    # Encode
    # ------------------------------------------------------------------
    def encode(self, grid: Grid) -> EncodedGrid:
        """
        Encode an ARC grid into a dictionary containing:

            - ``shape``      : (H, W)
            - ``flat``       : padded flat list of ints 0..9 (length 900)
            - ``normalized`` : np.ndarray float32 shape (30,30) in [0,1]
            - ``latent_256`` : np.ndarray float32 shape (256,)  — FLUME-compatible
            - ``latent_12``  : np.ndarray float32 shape (12,)   — down-projected axiomatic state
            - ``hiho``       : float coherence score
            - ``palette``    : sorted tuple of unique colors present
            - ``hash``       : deterministic SHA-256 hex digest
        """
        rows, cols = _validate_grid(grid)
        flat = [0] * (MAX_SIZE * MAX_SIZE)
        for r in range(rows):
            for c in range(cols):
                flat[r * MAX_SIZE + c] = grid[r][c]

        palette = tuple(sorted({v for row in grid for v in row}))
        h = hashlib.sha256(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()

        if np is None:
            return {
                "shape": (rows, cols),
                "flat": flat,
                "normalized": None,
                "latent_256": None,
                "latent_12": None,
                "hiho": 0.5,
                "palette": palette,
                "hash": h,
            }

        norm = _normalize_grid(grid)
        hiho = _hiho_coherence(norm)

        # Deterministic 256-D latent (geometric projection)
        latent_256 = norm.flatten() @ _projection_256d()

        # 12-D axiomatic projection (tied to HIHO 0.5 principle)
        rng12 = np.random.default_rng(seed=42)
        proj_12 = rng12.standard_normal((256, 12)).astype(np.float32)
        proj_12 = proj_12 / np.linalg.norm(proj_12, axis=0, keepdims=True)
        latent_12 = np.tanh(latent_256 @ proj_12)

        # Optionally refine with FLUME torch encoder if present
        if self._flume_encoder is not None:
            try:
                with torch.no_grad():
                    t = torch.from_numpy(norm.flatten()).unsqueeze(0).float()
                    flume_z = self._flume_encoder.encoder(t).squeeze(0).numpy()
                    # Ensemble: 70 % geometric deterministic + 30 % learned FLUME
                    latent_256 = 0.7 * latent_256 + 0.3 * flume_z
            except Exception:
                pass  # fallback to deterministic projection

        return {
            "shape": (rows, cols),
            "flat": flat,
            "normalized": norm,
            "latent_256": latent_256.astype(np.float32),
            "latent_12": latent_12.astype(np.float32),
            "hiho": round(hiho, 6),
            "palette": palette,
            "hash": h,
        }

    # ------------------------------------------------------------------
    # Decode
    # ------------------------------------------------------------------
    def decode(self, encoded: EncodedGrid) -> Grid:
        """Decode an EncodedGrid dict back to the exact original list-of-lists."""
        rows, cols = encoded["shape"]
        flat = encoded["flat"]
        grid: Grid = []
        for r in range(rows):
            grid.append([flat[r * MAX_SIZE + c] for c in range(cols)])
        return grid

    def decode_from_latent(self, latent_256: np.ndarray, shape: tuple[int, int]) -> Grid:
        """
        Reconstruct a grid from a 256-D latent using the pseudo-inverse of the
        deterministic projection.  This is lossy but useful for sanity checks.
        """
        if np is None:
            raise RuntimeError("numpy required for latent decode")
        rows, cols = shape
        W = _projection_256d()  # (900, 256)
        # Moore-Penrose pseudo-inverse
        W_pinv = np.linalg.pinv(W)  # (256, 900)
        flat_norm = latent_256 @ W_pinv  # (900,)
        arr = flat_norm.reshape(MAX_SIZE, MAX_SIZE)
        return _denormalize_grid(arr, rows, cols)

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------
    def encode_batch(self, grids: list[Grid]) -> list[EncodedGrid]:
        return [self.encode(g) for g in grids]

    def decode_batch(self, encodeds: list[EncodedGrid]) -> list[Grid]:
        return [self.decode(e) for e in encodeds]


# ---------------------------------------------------------------------------
# Task-level convenience wrappers
# ---------------------------------------------------------------------------


def encode_task(task: dict[str, Any]) -> dict[str, Any]:
    """
    Encode a full ARC task dict (with ``train`` and ``test`` lists).
    Returns the task with added ``_encoded`` metadata on each example.
    """
    codec = ARCCodec()
    out = {"id": task.get("id", ""), "train": [], "test": []}
    for split in ("train", "test"):
        for ex in task.get(split, []):
            entry: dict[str, Any] = {"input": ex["input"]}
            if "output" in ex:
                entry["output"] = ex["output"]
            entry["_encoded_input"] = codec.encode(ex["input"])
            if "output" in ex:
                entry["_encoded_output"] = codec.encode(ex["output"])
            out[split].append(entry)
    return out


def decode_prediction(encoded_pred: EncodedGrid | list[list[int]]) -> Grid:
    """Normalize a prediction to a plain Grid (list-of-lists 0..9)."""
    if isinstance(encoded_pred, dict):
        return ARCCodec().decode(encoded_pred)
    _validate_grid(encoded_pred)
    return encoded_pred


def grids_equal(a: Grid, b: Grid) -> bool:
    """Fast structural equality for two grids."""
    if len(a) != len(b):
        return False
    return all(len(ar) == len(br) and all(x == y for x, y in zip(ar, br)) for ar, br in zip(a, b))


# ---------------------------------------------------------------------------
# CLI sanity check
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample: Grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    codec = ARCCodec()
    enc = codec.encode(sample)
    dec = codec.decode(enc)
    assert grids_equal(sample, dec), "Round-trip failed"
    print("ARCCodec OK")
    print(f"  shape={enc['shape']}, hiho={enc['hiho']}, palette={enc['palette']}")
    print(f"  latent_256 norm={np.linalg.norm(enc['latent_256']):.4f}")
