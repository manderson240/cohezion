import numpy as np
import torch
import torch.nn as nn

class BioelectricCoupler:
    """
    Bioelectric Coupler for grid-cell pattern discovery.
    Uses similarity-based coupling to find 'organs' (connected components/objects).
    """
    def __init__(self, threshold=0.8):
        self.threshold = threshold

    def find_organs(self, grid):
        """
        Identify connected objects in the grid using coupling.
        Args:
            grid: np.array of shape (H, W)
        Returns:
            mask: np.array where each object has a unique integer ID.
        """
        h, w = grid.shape
        mask = np.zeros_like(grid, dtype=int)
        object_id = 1
        
        visited = np.zeros_like(grid, dtype=bool)
        
        for r in range(h):
            for c in range(w):
                if not visited[r, c] and grid[r, c] != 0: # 0 is background
                    self._flood_fill(grid, visited, mask, r, c, object_id)
                    object_id += 1
        return mask, object_id - 1

    def _flood_fill(self, grid, visited, mask, r, c, obj_id):
        h, w = grid.shape
        stack = [(r, c)]
        color = grid[r, c]
        
        while stack:
            curr_r, curr_c = stack.pop()
            if (0 <= curr_r < h and 0 <= curr_c < w and 
                not visited[curr_r, curr_c] and grid[curr_r, curr_c] == color):
                
                visited[curr_r, curr_c] = True
                mask[curr_r, curr_c] = obj_id
                
                # Check neighbors
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    stack.append((curr_r + dr, curr_c + dc))

class BioelectricNetwork(nn.Module):
    """
    Neural component that learns to predict coupling strengths.
    Inspired by 'bioelectric pattern coupling' from Phase 4 plan.
    """
    def __init__(self, latent_dim=256):
        super().__init__()
        # Simple coupling strength predictor
        self.coupler_net = nn.Sequential(
            nn.Linear(latent_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, z1, z2):
        """Predict coupling strength between two latent regions."""
        feat = torch.cat([z1, z2], dim=-1)
        return self.coupler_net(feat)

if __name__ == "__main__":
    # Test BioelectricCoupler
    coupler = BioelectricCoupler()
    test_grid = np.array([
        [0, 5, 5, 0],
        [0, 5, 5, 0],
        [0, 0, 0, 0],
        [2, 2, 0, 0]
    ])
    mask, count = coupler.find_organs(test_grid)
    print(f"Found {count} organs in test grid.")
    print("Organ Mask:")
    print(mask)
