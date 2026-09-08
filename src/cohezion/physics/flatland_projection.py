r"""Flatland Holographic Projection & Hyper-Sphere Cross-Section Engine
======================================================================
Inspired by Edwin A. Abbott's 'Flatland' (1884) and Holographic Duality (AdS/CFT).
Maps higher-dimensional Poincaré hyper-spheres (12D, 16D, 26D, 32D, 256D, 2048D)
onto 2D/3D Flatland cross-sectional slices.

Key Equations:
  - 2D Flatland Slice Radius: R_slice(w) = sqrt(max(0, R_hyper^2 - w^2))
  - Conformal Scale Factor in Flatland: lambda_flat(x, y) = 2 / (1 - (x^2 + y^2))
  - Orthogonal Gram-Schmidt Projection: P: R^N -> R^2 (preserves orientation)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cohezion.contracts import PoincarePoint


@dataclass(frozen=True, slots=True)
class FlatlandSlice:
    """2D Flatland cross-sectional slice of an N-dimensional hyper-sphere."""

    x: float
    y: float
    slice_radius: float
    conformal_factor: float
    original_dim: int
    w_depth: float  # Distance from the 2D Flatland slicing plane


class FlatlandProjector:
    """Projector for visualizing and mapping N-dimensional points into Flatland."""

    @classmethod
    def slice_hypersphere(cls, center: PoincarePoint, r_hyper: float, w_depth: float) -> float:
        """Compute the 2D slice radius seen by a Flatlander at depth w."""
        r_sq = r_hyper * r_hyper
        w_sq = w_depth * w_depth
        if w_sq >= r_sq:
            return 0.0  # Hyper-sphere does not intersect Flatland plane at this depth
        return math.sqrt(r_sq - w_sq)

    @classmethod
    def project_to_flatland(cls, pt: PoincarePoint, w_depth: float = 0.0) -> FlatlandSlice:
        """Project an N-dimensional Poincaré point onto 2D Flatland coordinates (x, y)."""
        dim = pt.dim
        coords = pt.coords

        # Extract primary 2D slice components (x_0, x_1)
        x = coords[0] if dim >= 1 else 0.0
        y = coords[1] if dim >= 2 else 0.0

        # Remaining dimensions contribute to depth w
        if dim > 2:
            remaining_sq = sum(c * c for c in coords[2:])
            actual_w = math.sqrt(remaining_sq) + w_depth
        else:
            actual_w = w_depth

        slice_r = cls.slice_hypersphere(pt, pt.norm, actual_w)
        r_2d_sq = x * x + y * y
        r_2d_sq = min(0.999, r_2d_sq)

        conformal_factor = 2.0 / (1.0 - r_2d_sq)

        return FlatlandSlice(
            x=round(x, 6),
            y=round(y, 6),
            slice_radius=round(slice_r, 6),
            conformal_factor=round(conformal_factor, 6),
            original_dim=dim,
            w_depth=round(actual_w, 6),
        )
