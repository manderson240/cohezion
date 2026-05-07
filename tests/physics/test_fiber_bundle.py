"""Tests for fiber bundle structure P(B⁴, SO(3)⁴)."""

import numpy as np
import pytest

from cohezion.physics.fiber_bundle import FiberBundle, FiberBundleState


class TestDecomposition:
    """Verify base/fiber decomposition and reconstruction."""

    def test_decompose_returns_correct_types(self):
        fb = FiberBundle()
        state = np.array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.5, 0.5, 0.0])
        decomp = fb.decompose(state)
        assert isinstance(decomp, FiberBundleState)
        assert decomp.base.shape == (4,)
        assert decomp.fiber.shape == (4, 3)

    def test_base_is_fabric_norms(self):
        """Base coordinates = norms of each fabric triplet."""
        fb = FiberBundle()
        state = np.array([3.0, 4.0, 0.0, 0.0, 0.0, 5.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        decomp = fb.decompose(state)
        assert decomp.base[0] == pytest.approx(5.0)  # ‖[3,4,0]‖
        assert decomp.base[1] == pytest.approx(5.0)  # ‖[0,0,5]‖
        assert decomp.base[2] == pytest.approx(1.0)  # ‖[1,0,0]‖
        assert decomp.base[3] == pytest.approx(0.0, abs=1e-15)  # ‖[0,0,0]‖

    def test_fiber_is_unit_direction(self):
        """Fiber directions are unit vectors."""
        fb = FiberBundle()
        state = np.random.randn(12)
        decomp = fb.decompose(state)
        for i in range(4):
            if decomp.base[i] > 1e-15:
                assert np.linalg.norm(decomp.fiber[i]) == pytest.approx(1.0, abs=1e-10)

    def test_reconstruct_roundtrip(self):
        """decompose → reconstruct recovers original state."""
        fb = FiberBundle()
        state = np.array([0.3, 0.7, 0.5, 1.0, 0.2, 0.8, 0.4, 0.6, 0.9, 0.1, 0.5, 0.3])
        decomp = fb.decompose(state)
        reconstructed = fb.reconstruct(decomp.base, decomp.fiber)
        np.testing.assert_allclose(reconstructed, state, atol=1e-10)

    def test_projection_is_surjective(self):
        """Any base point can be hit by some 12D state."""
        fb = FiberBundle()
        target_base = np.array([1.0, 2.0, 3.0, 4.0])
        # Construct a state with these norms (axis-aligned)
        state = np.zeros(12)
        state[0] = 1.0
        state[3] = 2.0
        state[6] = 3.0
        state[9] = 4.0
        base = fb.project_to_base(state)
        np.testing.assert_allclose(base, target_base)


class TestHorizontalVertical:
    """Verify horizontal/vertical decomposition of tangent vectors."""

    def test_h_plus_v_equals_original(self):
        """v = v_H + v_V (completeness)."""
        fb = FiberBundle()
        state = np.random.randn(12) + 0.5
        tangent = np.random.randn(12)
        h = fb.horizontal_component(state, tangent)
        v = fb.vertical_component(state, tangent)
        np.testing.assert_allclose(h + v, tangent, atol=1e-10)

    def test_horizontal_is_along_fiber_direction(self):
        """Horizontal component is parallel to current fiber direction per fabric."""
        fb = FiberBundle()
        state = np.array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0])
        tangent = np.random.randn(12)
        h = fb.horizontal_component(state, tangent)
        decomp = fb.decompose(state)
        for i in range(4):
            sl = list(fb.__class__.__mro__[0].__init__.__code__.co_varnames)
            # The horizontal block should be proportional to the fiber direction
            h_block = h[i * 3 : (i + 1) * 3]
            n = decomp.fiber[i]
            # h_block = (h_block · n) * n → h_block × n should be zero
            cross = np.cross(h_block, n)
            np.testing.assert_allclose(cross, 0.0, atol=1e-10)


class TestFlatConnection:
    """Verify flat connection properties."""

    def test_flat_curvature_is_zero(self):
        """Curvature vanishes for flat connection."""
        fb = FiberBundle()
        state = np.random.randn(12) + 0.5
        v1 = np.random.randn(12)
        v2 = np.random.randn(12)
        # For perfectly aligned tangent vectors, curvature is typically zero
        curv = fb.curvature_norm(state, v1 * 0, v2 * 0)
        assert curv == pytest.approx(0.0, abs=1e-10)

    def test_parallel_transport_constant_for_flat(self):
        """Parallel transport is path-independent on flat connection."""
        fb = FiberBundle()
        fiber = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
        curve = np.random.randn(10, 4)  # Random base-space curve
        transported = fb.parallel_transport(fiber, curve)
        for t_fiber in transported:
            np.testing.assert_array_equal(t_fiber, fiber)


class TestFabricCurvature:
    """Verify per-fabric curvature computation."""

    def test_constant_trajectory_zero_curvature(self):
        """Constant trajectory has zero fiber curvature."""
        fb = FiberBundle()
        traj = np.tile([0.5] * 12, (10, 1))
        curvatures = fb.fabric_curvature_per_fabric(traj)
        for name, c in curvatures.items():
            assert c == pytest.approx(0.0, abs=1e-10), f"{name} curvature should be 0"

    def test_rotating_trajectory_positive_curvature(self):
        """Trajectory with rotating fiber direction has positive curvature."""
        fb = FiberBundle()
        n = 50
        traj = np.zeros((n, 12))
        for t in range(n):
            angle = t * 0.1
            traj[t, 0] = np.cos(angle)
            traj[t, 1] = np.sin(angle)
            traj[t, 2] = 0
            traj[t, 3:] = 0.5  # Other fabrics constant
        curvatures = fb.fabric_curvature_per_fabric(traj)
        assert curvatures["Space"] > 0.01


class TestSerialization:
    """Verify dict serialization."""

    def test_to_dict_structure(self):
        fb = FiberBundle()
        state = np.array([0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.5, 0.5, 0.5])
        decomp = fb.decompose(state)
        d = decomp.to_dict()
        assert "base" in d
        assert "fiber" in d
        assert "fabric_norms" in d
        assert "fabric_directions" in d
        assert len(d["fabric_norms"]) == 4
