"""TDD tests for 8 color-aware ARC grid transform ops.

Tests written before implementation, per TDD methodology.
All ops operate on uint8 numpy arrays, values 0..9, 1x1..30x30.
"""

from __future__ import annotations

import numpy as np

# We import from transforms after registration; for TDD we test the functions directly
from cohezion.arc.transforms import (
    color_background,
    color_filter_keep,
    color_majority,
    color_map_learned,
    color_replace,
    color_swap,
    recolor_enclosed,
    recolor_interior,
)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def arr(*rows: tuple[int, ...]) -> np.ndarray:
    """Quick 2D uint8 grid from rows."""
    return np.array(rows, dtype=np.uint8)


# ═══════════════════════════════════════════════════════════════════
# 1. color_replace(grid, old, new)
# ═══════════════════════════════════════════════════════════════════


class TestColorReplace:
    def test_basic_replace(self):
        grid = arr((1, 2, 1), (2, 1, 2))
        result = color_replace(grid, old=1, new=9)
        expected = arr((9, 2, 9), (2, 9, 2))
        assert np.array_equal(result, expected)

    def test_no_match_returns_none(self):
        grid = arr((1, 2), (3, 4))
        result = color_replace(grid, old=5, new=9)
        assert result is None

    def test_all_same_old(self):
        grid = arr((1, 1), (1, 1))
        result = color_replace(grid, old=1, new=0)
        expected = arr((0, 0), (0, 0))
        assert np.array_equal(result, expected)

    def test_empty_grid_1x1(self):
        grid = arr((5,))
        result = color_replace(grid, old=5, new=9)
        expected = arr((9,))
        assert np.array_equal(result, expected)

    def test_zero_grid_replace_zero(self):
        """Replace 0 with something — should return new grid."""
        grid = np.zeros((3, 3), dtype=np.uint8)
        result = color_replace(grid, old=0, new=3)
        expected = np.full((3, 3), 3, dtype=np.uint8)
        assert np.array_equal(result, expected)

    def test_same_old_new_returns_none(self):
        grid = arr((1, 2), (3, 4))
        result = color_replace(grid, old=1, new=1)
        assert result is None

    def test_no_change_if_old_not_present(self):
        grid = arr((1, 2), (3, 4))
        result = color_replace(grid, old=7, new=8)
        assert result is None

    def test_old_is_new_but_grid_has_both(self):
        """old==new but grid only has other colors: no change."""
        grid = arr((1, 2), (3, 4))
        result = color_replace(grid, old=5, new=5)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 2. color_swap(grid, a, b)
# ═══════════════════════════════════════════════════════════════════


class TestColorSwap:
    def test_basic_swap(self):
        grid = arr((1, 2), (2, 1))
        result = color_swap(grid, a=1, b=2)
        expected = arr((2, 1), (1, 2))
        assert np.array_equal(result, expected)

    def test_only_one_color_present(self):
        grid = arr((1, 1), (1, 1))
        result = color_swap(grid, a=1, b=2)
        expected = arr((2, 2), (2, 2))
        assert np.array_equal(result, expected)

    def test_neither_color_present(self):
        grid = arr((3, 3), (3, 3))
        result = color_swap(grid, a=1, b=2)
        assert result is None

    def test_a_equals_b_returns_none(self):
        grid = arr((1, 2), (3, 4))
        result = color_swap(grid, a=1, b=1)
        assert result is None

    def test_swap_with_zero(self):
        grid = arr((0, 1), (2, 0))
        result = color_swap(grid, a=0, b=1)
        expected = arr((1, 0), (2, 1))
        assert np.array_equal(result, expected)

    def test_swap_large_grid(self):
        grid = np.random.randint(0, 10, (30, 30)).astype(np.uint8)
        grid[5, 5] = 1
        grid[5, 6] = 2
        result = color_swap(grid, a=1, b=2)
        assert result is not None
        # Original 1s became 2s, 2s became 1s
        assert result[5, 5] == 2
        assert result[5, 6] == 1


# ═══════════════════════════════════════════════════════════════════
# 3. color_filter_keep(grid, color)
# ═══════════════════════════════════════════════════════════════════


class TestColorFilterKeep:
    def test_basic_filter(self):
        grid = arr((1, 2, 3), (4, 5, 6))
        result = color_filter_keep(grid, color=3)
        expected = arr((0, 0, 3), (0, 0, 0))
        assert np.array_equal(result, expected)

    def test_color_not_present_returns_none(self):
        grid = arr((1, 2), (3, 4))
        result = color_filter_keep(grid, color=9)
        assert result is None

    def test_all_same_as_keep(self):
        grid = arr((5, 5), (5, 5))
        result = color_filter_keep(grid, color=5)
        # Identical — no change since all pixels already kept
        assert result is None

    def test_keep_zero(self):
        grid = arr((0, 1), (2, 0))
        result = color_filter_keep(grid, color=0)
        expected = arr((0, 0), (0, 0))
        assert np.array_equal(result, expected)

    def test_single_pixel_grid(self):
        grid = arr((7,))
        result = color_filter_keep(grid, color=7)
        assert result is None  # nothing to zero out

    def test_no_change_when_only_color(self):
        grid = arr((4, 4), (4, 4))
        result = color_filter_keep(grid, color=4)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 4. color_map_learned(grid, mapping)
# ═══════════════════════════════════════════════════════════════════


class TestColorMapLearned:
    def test_basic_mapping(self):
        grid = arr((1, 2), (3, 1))
        result = color_map_learned(grid, mapping={1: 9, 2: 8})
        expected = arr((9, 8), (3, 9))
        assert np.array_equal(result, expected)

    def test_empty_mapping_returns_none(self):
        grid = arr((1, 2), (3, 4))
        result = color_map_learned(grid, mapping={})
        assert result is None

    def test_mapping_no_keys_present(self):
        grid = arr((5, 6), (7, 8))
        result = color_map_learned(grid, mapping={1: 9, 2: 8})
        assert result is None

    def test_identity_mapping(self):
        grid = arr((1, 2), (3, 4))
        result = color_map_learned(grid, mapping={1: 1, 2: 2, 3: 3, 4: 4})
        assert result is None

    def test_mapping_includes_zero_to_color(self):
        grid = arr((0, 1), (2, 0))
        result = color_map_learned(grid, mapping={0: 3, 1: 9})
        expected = arr((3, 9), (2, 3))
        assert np.array_equal(result, expected)

    def test_chained_replacement(self):
        """Mapping {1:2, 2:3} — only one pass, so 1→2, 2→3 (no cascade)."""
        grid = arr((1, 2), (3, 1))
        result = color_map_learned(grid, mapping={1: 2, 2: 3, 3: 1})
        expected = arr((2, 3), (1, 2))
        assert np.array_equal(result, expected)

    def test_no_change_when_no_keys_match(self):
        grid = arr((5, 5), (5, 5))
        result = color_map_learned(grid, mapping={1: 9})
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 5. recolor_interior(grid)
# ═══════════════════════════════════════════════════════════════════


class TestRecolorInterior:
    def test_basic_square_frame(self):
        """A square frame of 1s with 0 inside -> interior becomes 1."""
        grid = arr(
            (1, 1, 1, 1),
            (1, 0, 0, 1),
            (1, 0, 0, 1),
            (1, 1, 1, 1),
        )
        result = recolor_interior(grid)
        expected = np.full((4, 4), 1, dtype=np.uint8)
        assert np.array_equal(result, expected)

    def test_multiple_frames(self):
        """Two separate frames of different colors."""
        grid = arr(
            (1, 1, 1, 0, 2, 2, 2),
            (1, 0, 1, 0, 2, 0, 2),
            (1, 1, 1, 0, 2, 2, 2),
        )
        result = recolor_interior(grid)
        expected = arr(
            (1, 1, 1, 0, 2, 2, 2),
            (1, 1, 1, 0, 2, 2, 2),
            (1, 1, 1, 0, 2, 2, 2),
        )
        assert np.array_equal(result, expected)

    def test_no_interior(self):
        """Solid block — no interior to recolor."""
        grid = arr((1, 1), (1, 1))
        result = recolor_interior(grid)
        assert result is None

    def test_single_pixel(self):
        grid = arr((5,))
        result = recolor_interior(grid)
        assert result is None

    def test_empty_grid_all_zeros(self):
        grid = np.zeros((5, 5), dtype=np.uint8)
        result = recolor_interior(grid)
        assert result is None

    def test_color_in_frame_interior(self):
        """Frame enclosing a different color — should recolor to frame color."""
        grid = arr(
            (1, 1, 1),
            (1, 3, 1),
            (1, 1, 1),
        )
        result = recolor_interior(grid)
        expected = arr(
            (1, 1, 1),
            (1, 1, 1),
            (1, 1, 1),
        )
        assert np.array_equal(result, expected)


# ═══════════════════════════════════════════════════════════════════
# 6. color_majority(grid)
# ═══════════════════════════════════════════════════════════════════


class TestColorMajority:
    def test_basic_majority_recolor(self):
        """Connected component with mixed colors -> most common color."""
        grid = arr(
            (1, 1, 2),
            (1, 2, 2),
            (2, 2, 2),
        )
        result = color_majority(grid)
        # Most common is 2 (5 pixels). All non-zero become 2.
        expected = np.full((3, 3), 2, dtype=np.uint8)
        assert np.array_equal(result, expected)

    def test_already_uniform(self):
        grid = arr((3, 3), (3, 3))
        result = color_majority(grid)
        assert result is None

    def test_two_separate_components(self):
        """Two separate blobs, each gets its own majority color."""
        grid = arr(
            (1, 1, 0, 9, 9),
            (1, 2, 0, 9, 8),
            (0, 0, 0, 0, 9),
        )
        result = color_majority(grid)
        # Left blob: 1,1,1,2 -> majority is 1
        # Right blob: 9,9,9,8,9 -> majority is 9
        expected = arr(
            (1, 1, 0, 9, 9),
            (1, 1, 0, 9, 9),
            (0, 0, 0, 0, 9),
        )
        assert np.array_equal(result, expected)

    def test_empty_grid(self):
        grid = np.zeros((4, 4), dtype=np.uint8)
        result = color_majority(grid)
        assert result is None

    def test_single_component_tie(self):
        """Tie in vote counts: pick the first-occurring color."""
        grid = arr((1, 2), (2, 1))
        result = color_majority(grid)
        # Tie: 1 appears 2x, 2 appears 2x
        # Implementation picks lowest label value (1)
        assert result is not None
        assert np.all(result[result != 0] == result[result != 0][0])


# ═══════════════════════════════════════════════════════════════════
# 7. color_background(grid, bg_color=None)
# ═══════════════════════════════════════════════════════════════════


class TestColorBackground:
    def test_fill_background_explicit_color(self):
        grid = arr(
            (0, 0, 0),
            (0, 1, 0),
            (0, 0, 0),
        )
        result = color_background(grid, bg_color=5)
        expected = arr(
            (5, 5, 5),
            (5, 1, 5),
            (5, 5, 5),
        )
        assert np.array_equal(result, expected)

    def test_auto_detect_background(self):
        """Most common edge color becomes bg."""
        grid = arr(
            (3, 3, 3),
            (3, 1, 3),
            (3, 3, 3),
        )
        result = color_background(grid, bg_color=None)
        # Edge: all 3s. Interior 1 should become 3.
        expected = np.full((3, 3), 3, dtype=np.uint8)
        assert np.array_equal(result, expected)

    def test_no_change_when_already_filled(self):
        grid = arr(
            (5, 5, 5),
            (5, 1, 5),
            (5, 5, 5),
        )
        result = color_background(grid, bg_color=5)
        assert result is None

    def test_bg_reaches_interior(self):
        """Background floods inward through gaps."""
        grid = arr(
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (0, 1, 0, 0),
            (0, 0, 0, 0),
        )
        result = color_background(grid, bg_color=2)
        expected = arr(
            (2, 2, 2, 2),
            (2, 1, 1, 2),
            (2, 1, 2, 2),
            (2, 2, 2, 2),
        )
        assert np.array_equal(result, expected)

    def test_all_same_color(self):
        grid = np.full((3, 3), 7, dtype=np.uint8)
        result = color_background(grid, bg_color=7)
        assert result is None

    def test_1x1_grid(self):
        grid = arr((0,))
        result = color_background(grid, bg_color=3)
        expected = arr((3,))
        assert np.array_equal(result, expected)


# ═══════════════════════════════════════════════════════════════════
# 8. recolor_enclosed(grid)
# ═══════════════════════════════════════════════════════════════════


class TestRecolorEnclosed:
    def test_single_enclosed_region(self):
        """A frame of 1s encloses a region of 0s -> 0 becomes 1."""
        grid = arr(
            (1, 1, 1, 1),
            (1, 0, 0, 1),
            (1, 0, 0, 1),
            (1, 1, 1, 1),
        )
        result = recolor_enclosed(grid)
        expected = np.full((4, 4), 1, dtype=np.uint8)
        assert np.array_equal(result, expected)

    def test_multiple_enclosed(self):
        """Two separate frames each enclose different interiors."""
        grid = arr(
            (1, 1, 1, 0, 2, 2, 2),
            (1, 0, 1, 0, 2, 0, 2),
            (1, 1, 1, 0, 2, 2, 2),
        )
        result = recolor_enclosed(grid)
        expected = np.full((3, 7), 0, dtype=np.uint8)  # not quite
        # Actually: enclosed interiors become boundary color
        expected = arr(
            (1, 1, 1, 0, 2, 2, 2),
            (1, 1, 1, 0, 2, 2, 2),
            (1, 1, 1, 0, 2, 2, 2),
        )
        assert np.array_equal(result, expected)

    def test_no_enclosed(self):
        """Solid block — no enclosed interior."""
        grid = np.full((3, 3), 4, dtype=np.uint8)
        result = recolor_enclosed(grid)
        assert result is None

    def test_enclosed_by_zero(self):
        """Region enclosed by 0 is not considered (0 is typically bg)."""
        grid = arr(
            (0, 0, 0),
            (0, 1, 0),
            (0, 0, 0),
        )
        result = recolor_enclosed(grid)
        # Zero boundaries don't count; 1 is not enclosed by a non-zero color
        assert result is None

    def test_nested_frames(self):
        """Frame 2 inside frame 1."""
        grid = arr(
            (1, 1, 1, 1, 1),
            (1, 2, 2, 2, 1),
            (1, 2, 0, 2, 1),
            (1, 2, 2, 2, 1),
            (1, 1, 1, 1, 1),
        )
        result = recolor_enclosed(grid)
        # Inner region enclosed by 2 becomes 2
        # Region between 1 and 2 (the 2s) are enclosed by 1? No — 2 touches nothing outside.
        # Actually: 2s are themselves enclosed by 1s, so 2s → 1
        # And the 0 enclosed by 2s → 2
        expected = arr(
            (1, 1, 1, 1, 1),
            (1, 1, 1, 1, 1),
            (1, 1, 2, 1, 1),
            (1, 1, 1, 1, 1),
            (1, 1, 1, 1, 1),
        )
        assert np.array_equal(result, expected)

    def test_non_enclosing_shape(self):
        """U-shape doesn't fully enclose."""
        grid = arr(
            (1, 1, 1),
            (1, 0, 1),
            (1, 0, 0),
        )
        result = recolor_enclosed(grid)
        assert result is None  # U is open, interior reaches edge


# ═══════════════════════════════════════════════════════════════════
# Integration / smoke tests
# ═══════════════════════════════════════════════════════════════════


class TestAllTransformsRegistration:
    """Verify all 8 new ops are in ALL_TRANSFORMS."""

    def test_all_color_ops_registered(self):
        from cohezion.arc.transforms import ALL_TRANSFORMS

        expected_names = {
            "color_replace",
            "color_swap",
            "color_filter_keep",
            "color_map_learned",
            "recolor_interior",
            "color_majority",
            "color_background",
            "recolor_enclosed",
        }
        registered = set(ALL_TRANSFORMS.keys())
        missing = expected_names - registered
        assert not missing, f"Missing from ALL_TRANSFORMS: {missing}"

    def test_apply_chain_with_color_ops(self):
        from cohezion.arc.transforms import apply_chain

        grid = arr((1, 2, 3), (4, 5, 6))
        apply_chain(grid, ["color_filter_keep", "color_background"])
        # Filter keep with default param (color=1) won't work — but this test
        # just checks they are callable via apply_chain at all
        # With no params they may return None, which is fine
        pass  # existence check only


class TestReturnNoneWhenNoChange:
    """Every color op MUST return None when the grid is unchanged."""

    def test_color_replace_nochange(self):
        assert color_replace(np.ones((3, 3), dtype=np.uint8), old=2, new=3) is None
        assert color_replace(np.ones((3, 3), dtype=np.uint8), old=1, new=1) is None

    def test_color_swap_nochange(self):
        assert color_swap(np.ones((3, 3), dtype=np.uint8), a=1, b=1) is None
        assert color_swap(np.ones((3, 3), dtype=np.uint8), a=2, b=3) is None

    def test_color_filter_keep_nochange(self):
        assert color_filter_keep(np.ones((3, 3), dtype=np.uint8), color=1) is None

    def test_color_map_learned_nochange(self):
        assert color_map_learned(np.ones((3, 3), dtype=np.uint8), mapping={}) is None
        assert color_map_learned(np.ones((3, 3), dtype=np.uint8), mapping={1: 1}) is None

    def test_recolor_interior_nochange(self):
        assert recolor_interior(np.zeros((3, 3), dtype=np.uint8)) is None
        assert recolor_interior(np.ones((3, 3), dtype=np.uint8)) is None

    def test_color_majority_nochange(self):
        assert color_majority(np.zeros((3, 3), dtype=np.uint8)) is None
        assert color_majority(np.full((3, 3), 5, dtype=np.uint8)) is None

    def test_color_background_nochange(self):
        assert color_background(np.ones((3, 3), dtype=np.uint8), bg_color=1) is None

    def test_recolor_enclosed_nochange(self):
        assert recolor_enclosed(np.zeros((3, 3), dtype=np.uint8)) is None
        assert recolor_enclosed(np.ones((3, 3), dtype=np.uint8)) is None


class TestEdgeCases:
    """Handle edge cases: 1x1, all-zero, single-color."""

    def test_1x1_grids(self):
        g = arr((5,))
        assert color_replace(g, old=5, new=9)[0, 0] == 9
        assert color_replace(g, old=9, new=0) is None
        assert color_swap(g, a=5, b=2)[0, 0] == 2
        assert color_filter_keep(g, color=5) is None
        assert color_map_learned(g, mapping={5: 3})[0, 0] == 3
        assert recolor_interior(g) is None
        assert color_majority(g) is None
        assert recolor_enclosed(g) is None

    def test_all_zero_grid(self):
        g = np.zeros((5, 5), dtype=np.uint8)
        assert color_replace(g, old=0, new=1) is not None
        assert color_swap(g, a=1, b=2) is None
        assert color_filter_keep(g, color=0) is not None
        assert color_map_learned(g, mapping={0: 1}) is not None
        assert recolor_interior(g) is None
        assert color_majority(g) is None
        assert recolor_enclosed(g) is None

    def test_all_single_color(self):
        g = np.full((4, 4), 7, dtype=np.uint8)
        assert color_filter_keep(g, color=7) is None
        assert color_majority(g) is None
        assert recolor_interior(g) is None
        assert recolor_enclosed(g) is None
