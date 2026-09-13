"""Vector 3: Metamorphic Testing.
=================================
Solves the 'test oracle problem' by asserting mathematical relationships
between transformed inputs and outputs rather than hardcoded expected values.
"""

import math
import numpy as np
import pytest

from cohezion.physics.my_big_toe_entropy_engine import MyBigTOEEntropyEngine
from cohezion.flume.twistor_bundle_bridge import PoincareManifoldND


@pytest.mark.metamorphic
class TestMetamorphicRelations:
    def test_mr1_arc_grid_rotation_equivariance(self):
        """MR1: Rotational Equivariance.

        For a grid-level transformation operator F and 90-degree rotation R:
        F(R(grid)) == R(F(grid))
        """
        grid = np.array(
            [
                [1, 2, 0, 0],
                [0, 1, 3, 0],
                [4, 0, 1, 0],
                [0, 0, 0, 2],
            ],
            dtype=int,
        )

        # Morphological fill/boundary operator
        def morphology_operator(g: np.ndarray) -> np.ndarray:
            # Replaces zeros adjacent to non-zeros with max neighbor value
            out = g.copy()
            for r in range(g.shape[0]):
                for c in range(g.shape[1]):
                    if g[r, c] == 0:
                        neighbors = []
                        if r > 0 and g[r - 1, c] > 0:
                            neighbors.append(g[r - 1, c])
                        if r < g.shape[0] - 1 and g[r + 1, c] > 0:
                            neighbors.append(g[r + 1, c])
                        if c > 0 and g[r, c - 1] > 0:
                            neighbors.append(g[r, c - 1])
                        if c < g.shape[1] - 1 and g[r, c + 1] > 0:
                            neighbors.append(g[r, c + 1])
                        if neighbors:
                            out[r, c] = max(neighbors)
            return out

        # Path A: Rotate first, then apply operator
        grid_rot90 = np.rot90(grid)
        res_a = morphology_operator(grid_rot90)

        # Path B: Apply operator first, then rotate
        res_b_pre = morphology_operator(grid)
        res_b = np.rot90(res_b_pre)

        # Metamorphic Relation holds: both paths produce identical grids without hardcoded oracle
        np.testing.assert_array_equal(res_a, res_b)

    def test_mr2_poincare_hyperbolic_isometry_preservation(self):
        """MR2: Poincaré Hyperbolic Distance Isometry.

        Applying a coordinate inversion / isometric reflection R must preserve
        the exact geodesic distance between any pair of points:
        d_H(R(u), R(v)) == d_H(u, v)
        """
        dim = 16
        rng = np.random.default_rng(42)

        # Two points strictly within unit ball
        u = rng.uniform(-0.4, 0.4, size=dim)
        v = rng.uniform(-0.4, 0.4, size=dim)

        p_u = PoincareManifoldND.project(list(u), target_dim=dim)
        p_v = PoincareManifoldND.project(list(v), target_dim=dim)

        original_dist = PoincareManifoldND.distance(p_u, p_v)

        # Isometry: Parity reflection along odd axes: R(x)_i = -x_i for odd i
        u_reflected = [val if i % 2 == 0 else -val for i, val in enumerate(u)]
        v_reflected = [val if i % 2 == 0 else -val for i, val in enumerate(v)]

        p_u_ref = PoincareManifoldND.project(u_reflected, target_dim=dim)
        p_v_ref = PoincareManifoldND.project(v_reflected, target_dim=dim)

        transformed_dist = PoincareManifoldND.distance(p_u_ref, p_v_ref)

        # Metamorphic Relation: Hyperbolic distance must be invariant under isometry
        assert math.isclose(original_dist, transformed_dist, rel_tol=1e-7, abs_tol=1e-7)

    def test_mr3_entropy_replication_scaling_invariance(self):
        """MR3: Multi-Scale Replication Invariance in My Big TOE Entropy.

        Replicating a point cloud homogeneously (duplicating each point in place)
        preserves the centroid and HIHO dispersion distribution.
        """
        engine = MyBigTOEEntropyEngine()
        points = [
            (0.1, 0.2),
            (0.2, 0.1),
            (-0.1, -0.2),
            (-0.2, 0.1),
        ]
        coherences = [0.5] * len(points)

        state_orig = engine.calculate_state_entropy(points, coherences=coherences)

        # Replicate points 3 times
        replicated_points = points * 3
        replicated_coherences = coherences * 3

        state_rep = engine.calculate_state_entropy(
            replicated_points, coherences=replicated_coherences
        )

        # Metamorphic Relation: Centroid distance dispersion remains invariant
        assert math.isclose(
            state_orig.hiho_dispersion_entropy,
            state_rep.hiho_dispersion_entropy,
            rel_tol=1e-4,
            abs_tol=1e-4,
        )
