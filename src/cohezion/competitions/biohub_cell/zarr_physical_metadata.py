"""Biohub 3D OME-Zarr Physical Spatiotemporal Metadata Engine.

Parses dx, dy, dz voxel physical dimensions and temporal intervals to calculate
true Euclidean spatial distances in micrometers, eliminating anisotropic distortion.
"""

from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np

class ZarrPhysicalMetadataEngine:
    """Normalizes coordinate systems using true physical voxel resolution."""

    def __init__(self, dx_um: float = 0.2, dy_um: float = 0.2, dz_um: float = 1.0, dt_min: float = 5.0):
        self.voxel_scale = np.array([dx_um, dy_um, dz_um], dtype=np.float32)
        self.dt_min = dt_min

    def compute_physical_distance(self, c0_voxel: Tuple[float, float, float], c1_voxel: Tuple[float, float, float]) -> float:
        """Calculates true physical Euclidean distance in micrometers (µm)."""
        p0 = np.array(c0_voxel, dtype=np.float32) * self.voxel_scale
        p1 = np.array(c1_voxel, dtype=np.float32) * self.voxel_scale
        return float(np.linalg.norm(p1 - p0))

    def compute_motion_velocity_um_per_min(self, c0_voxel: Tuple[float, float, float], c1_voxel: Tuple[float, float, float]) -> float:
        """Calculates physical displacement speed (µm / min)."""
        dist_um = self.compute_physical_distance(c0_voxel, c1_voxel)
        return dist_um / max(1e-3, self.dt_min)
