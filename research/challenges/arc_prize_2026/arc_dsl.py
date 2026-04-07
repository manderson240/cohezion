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
    def get_all_ops():
        """Returns a list of all available DSL operations for the genetic algorithm."""
        return [
            ("rotate90", 0), ("rotate180", 0), ("rotate270", 0),
            ("flip_h", 0), ("flip_v", 0),
            ("recolor", 2), # Requires 2 params: from_color, to_color
            ("move_object", 3) # Requires 3 params: obj_id, dx, dy
        ]
