"""Mereon Projector - Implementation of the 600-Cell to M120p projection.

This module implements the geometric correspondence between the 4D 600-cell
(vertices of the binary icosahedral group 2I) and the 3D Mereon 120-polyhedron (M120p).

Key Features:
  - Stereographic projection from S3 to R3.
  - 'Lifting' from R3 to S3 using the 2phi^2 scaling factor.
  - Identification of the 8-shell structure.
  - Classification of vertex types (A, B, C) based on S3 latitude (w).

References:
  - 'The Mereon System, the 600-Cell, and the Exceptional Algebras E6, E7, E8' (arXiv:2604.00255v1)
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np


# Golden ratio constants
PHI = (1.0 + 5.0**0.5) / 2.0
PHI_SQ = PHI**2
TWO_PHI_SQ = 2.0 * PHI_SQ

# Latitude markers for the binary icosahedral group 2I
# w = cos(theta/2)
S3_LATITUDES = {
    "A": 0.5,  # 60 degrees lat, 120 deg rotation
    "B": 0.0,  # Equator, 180 deg rotation
    "C": 1.0 / (2.0 * PHI),  # 72 degrees lat, 144 deg rotation
    "Inner": PHI / 2.0,  # 36 degrees lat, 72 deg rotation (Focusing Sphere)
}


class ProjectionResult(NamedTuple):
    """Result of a Mereon projection/lift operation."""

    vector: np.ndarray
    w: float
    shell: int
    vertex_type: str
    coherence: float


class MereonProjector:
    """Handles the projection between the 600-cell in R4 and the M120p in R3."""

    def __init__(self, scale: float = TWO_PHI_SQ):
        self.scale = scale

    def lift(self, vertex: np.ndarray) -> ProjectionResult:
        """
        Lifts a 3D vertex from the M120p to a unit quaternion on S3.

        The process:
        1. Scale vertex by 1 / (2phi^2) to map to unit-ish radius.
        2. Recover the fourth dimension w = sqrt(1 - r'^2).
        3. Return the 4D unit vector (w, x', y', z').

        Parameters
        ----------
        vertex : np.ndarray
            3D coordinate (x, y, z) in the M120p coordinate system.
        """
        v = np.asarray(vertex, dtype=float)
        v_prime = v / self.scale
        r_sq = np.sum(v_prime**2)

        # Avoid precision issues with sqrt(0) or slightly > 1
        w = np.sqrt(max(0.0, 1.0 - r_sq))

        q = np.array([w, v_prime[0], v_prime[1], v_prime[2]])

        # Note: If q is not exactly unit due to precision, normalize it
        q = q / np.linalg.norm(q)

        return ProjectionResult(
            vector=q,
            w=q[0],
            shell=self.get_shell(q),
            vertex_type=self.get_vertex_type(q),
            coherence=1.0,  # Pure states on S3 always have coherence 1
        )

    def project(self, q: np.ndarray) -> np.ndarray:
        """
        Projects a 4D unit quaternion q from S3 to R3 using stereographic projection.

        pi(q) = (x, y, z) / (1 + w)

        Parameters
        ----------
        q : np.ndarray
            Unit quaternion (w, x, y, z).
        """
        q = np.asarray(q, dtype=float)
        w, x, y, z = q

        # Projection from (-1, 0, 0, 0) as per paper eq(1)
        # However, standard stereographic is usually from north pole.
        # The paper specifies pi(q) = (x,y,z)/(1+w)
        denom = 1.0 + w
        if abs(denom) < 1e-10:
            return np.array([float("inf"), float("inf"), float("inf")])

        v_prime = np.array([x, y, z]) / denom

        # Map back to M120p coordinates by applying the scale
        return v_prime * self.scale

    def get_vertex_type(self, q: np.ndarray) -> str:
        """Identifies the vertex type (A, B, C, Inner) based on the w-coordinate."""
        w = abs(q[0])
        for v_type, val in S3_LATITUDES.items():
            if np.isclose(w, val, atol=1e-4):
                return v_type
        return "Unknown"

    def get_shell(self, q: np.ndarray) -> int:
        """
        Identifies the shell index (0-7) based on the scalar part w.

        Shells are determined by |w| values:
        0: w=+1
        1: w=phi/2 (Inner)
        2: w=1/2 (A)
        3: w=1/(2phi) (C)
        4: w=0 (B)
        5: w=-1/(2phi) (C recipient)
        6: w=-1/2 (A recipient)
        7: w=-phi/2 (Inner recipient)
        inf: w=-1
        """
        w = q[0]

        if np.isclose(w, 1.0, atol=1e-4):
            return 0
        if np.isclose(w, PHI / 2.0, atol=1e-4):
            return 1
        if np.isclose(w, 0.5, atol=1e-4):
            return 2
        if np.isclose(w, 1.0 / (2.0 * PHI), atol=1e-4):
            return 3
        if np.isclose(w, 0.0, atol=1e-4):
            return 4
        if np.isclose(w, -1.0 / (2.0 * PHI), atol=1e-4):
            return 5
        if np.isclose(w, -0.5, atol=1e-4):
            return 6
        if np.isclose(w, -PHI / 2.0, atol=1e-4):
            return 7
        if np.isclose(w, -1.0, atol=1e-4):
            return 8  # Point at infinity

        return -1
