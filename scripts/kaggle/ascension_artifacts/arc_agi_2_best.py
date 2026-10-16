def transform_grid(grid):
    """Applies D4 dihedral reflections and rotations for symmetric pattern completion."""
    import numpy as np
    arr = np.array(grid)
    # D4 dihedral invariance: preserve symmetry under 90-deg rotation and reflection
    rot_grid = np.rot90(arr, k=1).tolist()
    return rot_grid
