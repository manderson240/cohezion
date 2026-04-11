import numpy as np


class ARCDSL:
    """Domain Specific Language primitives for ARC-AGI grid transformations."""

    @staticmethod
    def rotate90(grid):
        """Rotate grid 90 degrees clockwise."""
        return np.rot90(grid, k=-1)

    @staticmethod
    def rotate180(grid):
        """Rotate grid 180 degrees."""
        return np.rot90(grid, k=2)

    @staticmethod
    def rotate270(grid):
        """Rotate grid 270 degrees clockwise."""
        return np.rot90(grid, k=1)

    @staticmethod
    def flip_h(grid):
        """Flip grid horizontally."""
        return np.fliplr(grid)

    @staticmethod
    def flip_v(grid):
        """Flip grid vertically."""
        return np.flipud(grid)

    @staticmethod
    def recolor(grid, from_color, to_color):
        """Replace all instances of from_color with to_color."""
        new_grid = grid.copy()
        new_grid[grid == from_color] = to_color
        return new_grid

    @staticmethod
    def extract_object(grid, mask, obj_id):
        """Extract a single object from the grid based on its mask ID."""
        obj_grid = np.zeros_like(grid)
        obj_grid[mask == obj_id] = grid[mask == obj_id]
        return obj_grid

    @staticmethod
    def move_object(grid, mask, obj_id, dx, dy):
        """Move an object by (dx, dy) within the grid bounds."""
        new_grid = grid.copy()
        h, w = grid.shape

        # Clear original object
        new_grid[mask == obj_id] = 0

        # Draw at new position
        for r in range(h):
            for c in range(w):
                if mask[r, c] == obj_id:
                    new_r, new_c = r + dy, c + dx
                    if 0 <= new_r < h and 0 <= new_c < w:
                        new_grid[new_r, new_c] = grid[r, c]
        return new_grid

    @staticmethod
    def crop_to_content(grid):
        """Crops the grid to the smallest bounding box containing non-zero pixels."""
        coords = np.argwhere(grid != 0)
        if coords.size == 0:
            return grid
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0) + 1
        return grid[y_min:y_max, x_min:x_max]

    @staticmethod
    def symmetry_fill(grid, axis="h"):
        """Fills the grid by mirroring existing content across an axis."""
        new_grid = grid.copy()
        h, w = grid.shape
        if axis == "h":
            half_w = w // 2
            new_grid[:, half_w:] = (
                np.fliplr(new_grid[:, :half_w])
                if w % 2 == 0
                else np.fliplr(new_grid[:, : half_w + 1])[:, 1:]
            )
        else:
            half_h = h // 2
            new_grid[half_h:, :] = (
                np.flipud(new_grid[:half_h, :])
                if h % 2 == 0
                else np.flipud(new_grid[: half_h + 1, :])[1:, :]
            )
        return new_grid

    @staticmethod
    def scale_grid(grid, factor=2):
        """Scales the grid by a given integer factor (nearest neighbor)."""
        return np.repeat(np.repeat(grid, factor, axis=0), factor, axis=1)

    @staticmethod
    def get_all_ops():
        """Returns a list of all available DSL operations for the genetic algorithm."""
        return [
            ("rotate90", 0),
            ("rotate180", 0),
            ("rotate270", 0),
            ("flip_h", 0),
            ("flip_v", 0),
            ("recolor", 2),
            ("move_object", 3),
            ("crop_to_content", 0),
            ("symmetry_fill", 1),  # axis: 'h' or 'v'
            ("scale_grid", 1),  # factor
        ]
