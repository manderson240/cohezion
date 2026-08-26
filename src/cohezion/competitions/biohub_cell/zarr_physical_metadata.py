"""Biohub 3D OME-Zarr Physical Spatiotemporal Metadata Engine.

Parses dx, dy, dz voxel physical dimensions and temporal intervals to calculate
true Euclidean spatial distances in micrometers, eliminating anisotropic distortion.
"""

from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np

class ZarrPhysicalMetadataEngine:
    """Normalizes coordinate systems using true physical voxel resolution and Riemannian distance metric."""

    def __init__(self, dx_um: float = 0.2, dy_um: float = 0.2, dz_um: float = 1.0, dt_min: float = 5.0):
        # Enforce positive non-zero physical scaling
        self.dx = max(1e-4, float(dx_um))
        self.dy = max(1e-4, float(dy_um))
        self.dz = max(1e-4, float(dz_um))
        self.voxel_scale = np.array([self.dx, self.dy, self.dz], dtype=np.float32)
        self.dt_min = max(1e-3, float(dt_min))

    def compute_physical_distance(self, c0_voxel: Tuple[float, float, float], c1_voxel: Tuple[float, float, float]) -> float:
        """Calculates Riemannian physical distance in micrometers (µm): d_G(p0, p1) = sqrt((p1 - p0)^T G (p1 - p0))."""
        if not c0_voxel or not c1_voxel or len(c0_voxel) < 3 or len(c1_voxel) < 3:
            return 0.0

        p0 = np.array(c0_voxel[:3], dtype=np.float32) * self.voxel_scale
        p1 = np.array(c1_voxel[:3], dtype=np.float32) * self.voxel_scale
        return float(np.linalg.norm(p1 - p0))

    def compute_motion_velocity_um_per_min(self, c0_voxel: Tuple[float, float, float], c1_voxel: Tuple[float, float, float]) -> float:
        """Calculates physical displacement speed in micrometers per minute (µm/min)."""
        dist_um = self.compute_physical_distance(c0_voxel, c1_voxel)
        return dist_um / self.dt_min
