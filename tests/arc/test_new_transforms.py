"""Tests for Tier 8 high-impact transforms: symmetry, center_of_mass."""

from __future__ import annotations

import numpy as np

from cohezion.arc.transforms import (
    ALL_TRANSFORMS,
    grid_symmetry_reflect,
    object_center_of_mass,
)


class TestGridSymmetryReflect:
    """grid_symmetry_reflect mirrors missing halves of asymmetric grids."""

    def test_vertical_asymmetric(self):
        # Top row partially filled, bottom row all-zero → mirror top→bottom
        g = np.array(
            [
                [1, 0, 7],
                [3, 4, 5],
                [0, 0, 0],
            ],
            dtype=int,
        )
        result = grid_symmetry_reflect(g, axis="vertical")
        assert result is not None
        # Row 0=[1,0,7] mirrors to Row 2: col 0→fill(2,0)=1, col 2→fill(2,2)=7
        assert result[2, 0] == 1 and result[2, 2] == 7

    def test_horizontal_asymmetric(self):
        g = np.array(
            [
                [1, 0, 0],
                [3, 0, 0],
                [5, 0, 0],
            ],
            dtype=int,
        )
        result = grid_symmetry_reflect(g, axis="horizontal")
        assert result is not None
        # Left column mirrored to right: (0,0)=1→(0,2), etc.
        assert result[0, 2] == 1 and result[1, 2] == 3

    def test_already_symmetric(self):
        g = np.array(
            [
                [0, 1, 0],
                [1, 2, 1],
                [0, 1, 0],
            ],
            dtype=int,
        )
        result = grid_symmetry_reflect(g, axis="vertical")
        assert result is None

    def test_even_width_no_crash(self):
        # Even-width: outer columns already filled (no mirror zeros to fill).
        # Verify the function handles even-width without raising.
        g = np.array(
            [
                [1, 0, 0, 2],
                [3, 0, 0, 4],
            ],
            dtype=int,
        )
        result = grid_symmetry_reflect(g, axis="horizontal")
        # Mirror of col-1 is col-2 — both zero, nothing to fill → None
        assert result is None


class TestObjectCenterOfMass:
    """object_center_of_mass places markers at component centroids."""

    def test_single_object_centroid(self):
        g = np.array(
            [
                [0, 0, 0],
                [0, 1, 0],
                [0, 1, 0],
                [0, 0, 0],
            ],
            dtype=int,
        )
        result = object_center_of_mass(g)
        assert result is not None
        # Centroid of pixels at (1,1)+(2,1): mean row=1.5→round=2, col=1
        assert result[2, 1] != 0

    def test_multiple_objects(self):
        g = np.array(
            [
                [1, 0, 0],
                [1, 0, 2],
                [0, 0, 2],
            ],
            dtype=int,
        )
        result = object_center_of_mass(g)
        assert result is not None

    def test_all_background(self):
        g = np.zeros((5, 5), dtype=int)
        result = object_center_of_mass(g)
        assert result is None

    def test_single_pixel_object(self):
        g = np.zeros((5, 5), dtype=int)
        g[2, 2] = 3
        result = object_center_of_mass(g)
        assert result is not None and result[2, 2] == 3


class TestAllTransformsRegistry:
    """Verify new transforms are in ALL_TRANSFORMS dict."""

    def test_symmetry_horizontal_registered(self):
        assert "grid_symmetry_reflect_h" in ALL_TRANSFORMS

    def test_symmetry_vertical_registered(self):
        assert "grid_symmetry_reflect_v" in ALL_TRANSFORMS

    def test_center_of_mass_registered(self):
        assert "object_center_of_mass" in ALL_TRANSFORMS

    def test_transform_callable(self):
        fn = ALL_TRANSFORMS["grid_symmetry_reflect_h"]
        g = np.array([[1, 0, 0], [3, 0, 0]], dtype=int)
        result = fn(g)
        assert result is not None and np.array_equal(result.shape, g.shape)

    def test_count(self):
        """Verify we have at least 49 transforms (was 46, added 3)."""
        assert len(ALL_TRANSFORMS) >= 49


class TestChainIntegration:
    """Test new transforms compose correctly with apply_chain."""

    def test_chain_with_symmetry_reflect(self):
        from cohezion.arc.transforms import apply_chain

        g = np.array(
            [
                [0, 1, 0],
                [0, 2, 3],
                [0, 4, 0],
            ],
            dtype=int,
        )
        result = apply_chain(g, ["grid_symmetry_reflect_h"])
        assert result is not None and np.array_equal(result.shape, g.shape)

    def test_chain_three_transforms(self):
        from cohezion.arc.transforms import apply_chain

        g = np.array(
            [
                [1, 0, 0],
                [1, 2, 0],
            ],
            dtype=int,
        )
        result = apply_chain(g, ["rotate_90", "grid_symmetry_reflect_v"])
        assert result is not None


class TestDirectionalGravityAndInversion:
    """Test gravity_up, gravity_left, gravity_right, and color_invert_binary."""

    def test_gravity_up(self):
        from cohezion.arc.transforms import gravity_up

        g = np.array(
            [
                [0, 0, 0],
                [1, 0, 2],
                [3, 4, 0],
            ],
            dtype=int,
        )
        res = gravity_up(g)
        assert res is not None
        # Col 0: [1, 3] rise to top -> [1, 3, 0]
        # Col 1: [4] rises to top -> [4, 0, 0]
        # Col 2: [2] rises to top -> [2, 0, 0]
        assert np.array_equal(res[:, 0], [1, 3, 0])
        assert np.array_equal(res[:, 1], [4, 0, 0])
        assert np.array_equal(res[:, 2], [2, 0, 0])

    def test_gravity_left(self):
        from cohezion.arc.transforms import gravity_left

        g = np.array(
            [
                [0, 1, 2],
                [0, 0, 3],
                [4, 0, 5],
            ],
            dtype=int,
        )
        res = gravity_left(g)
        assert res is not None
        # Row 0: [1, 2] shift left -> [1, 2, 0]
        # Row 1: [3] shifts left -> [3, 0, 0]
        # Row 2: [4, 5] shifts left -> [4, 5, 0]
        assert np.array_equal(res[0, :], [1, 2, 0])
        assert np.array_equal(res[1, :], [3, 0, 0])
        assert np.array_equal(res[2, :], [4, 5, 0])

    def test_gravity_right(self):
        from cohezion.arc.transforms import gravity_right

        g = np.array(
            [
                [1, 2, 0],
                [3, 0, 0],
                [4, 0, 5],
            ],
            dtype=int,
        )
        res = gravity_right(g)
        assert res is not None
        # Row 0: [1, 2] shift right -> [0, 1, 2]
        # Row 1: [3] shifts right -> [0, 0, 3]
        # Row 2: [4, 5] shifts right -> [0, 4, 5]
        assert np.array_equal(res[0, :], [0, 1, 2])
        assert np.array_equal(res[1, :], [0, 0, 3])
        assert np.array_equal(res[2, :], [0, 4, 5])

    def test_color_invert_binary(self):
        from cohezion.arc.transforms import color_invert_binary

        g = np.array(
            [
                [0, 2, 0],
                [2, 2, 0],
                [0, 0, 0],
            ],
            dtype=int,
        )
        res = color_invert_binary(g)
        assert res is not None
        assert np.array_equal(
            res,
            [
                [2, 0, 2],
                [0, 0, 2],
                [2, 2, 2],
            ],
        )

    def test_color_invert_binary_multi_color_returns_none(self):
        from cohezion.arc.transforms import color_invert_binary

        g = np.array(
            [
                [1, 2, 0],
                [0, 0, 0],
            ],
            dtype=int,
        )
        assert color_invert_binary(g) is None
