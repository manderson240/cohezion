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
