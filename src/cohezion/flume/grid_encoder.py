"""FLUME Grid Encoder for ARC-AGI style grid patterns.

Specialized encoder/decoder for 2D matrices (0-9) representing color grids.
Maps grids to 256D FLUME latent space for semantic reasoning and trajectory tracking.
"""

import numpy as np
import torch
import torch.nn as nn


class ARCGridEncoder(nn.Module):
    """
    Encoder for ARC-AGI grids.
    Uses a simple CNN or MLP to project 2D grids into 256D.
    """

    def __init__(self, latent_dim: int = 256, max_grid_size: int = 30):
        super().__init__()
        self.latent_dim = latent_dim
        self.max_grid_size = max_grid_size

        # Flattened input size (max_grid_size * max_grid_size)
        self.input_dim = max_grid_size * max_grid_size

        self.encoder = nn.Sequential(
            nn.Linear(self.input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, latent_dim),
        )

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, self.input_dim),
            nn.Sigmoid(),
        )

        # Static 12D projection matrix (256D -> 12D)
        # Using a deterministic seed for cross-session consistency
        rng = np.random.default_rng(seed=42)
        self.proj_12d = torch.from_numpy(
            rng.standard_normal((12, latent_dim)).astype(np.float32)
        )

    def project_to_12d(self, z: torch.Tensor) -> torch.Tensor:
        """Down-project 256D latent to 12D axiomatic state."""
        # Ensure z is [batch, latent_dim]
        if z.dim() == 1:
            z = z.unsqueeze(0)
        
        # Linear projection + tanh normalization to [-1, 1] range
        state_12d = torch.matmul(z, self.proj_12d.t().to(z.device))
        return torch.tanh(state_12d)

    def preprocess_grid(self, grid: list[list[int]]) -> torch.Tensor:
        """Pad and flatten grid for encoding."""
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0

        flat_grid = np.zeros((self.max_grid_size, self.max_grid_size), dtype=np.float32)

        # Fill existing grid into top-left
        for r in range(min(rows, self.max_grid_size)):
            for c in range(min(cols, self.max_grid_size)):
                flat_grid[r, c] = grid[r][c] / 10.0

        return torch.from_numpy(flat_grid.flatten()).unsqueeze(0)

    def encode(self, grid: list[list[int]]) -> torch.Tensor:
        """Encode 2D grid to latent vector and emit telemetry."""
        x = self.preprocess_grid(grid)
        z = self.encoder(x)

        # --- JOURNEY TELEMETRY INSTRUMENTATION ---
        try:
            state_12d = self.project_to_12d(z)
            
            from cohezion.core.telemetry_bus import get_telemetry_bus
            from cohezion.data_mesh.journey_telemetry import (
                FlumeJourneyEvent, 
                QuadratureFabrics, 
                RZeroMetrics, 
                SwarmExpert, 
                HardwareTier
            )
            from datetime import datetime
            
            # Compute coherence as distance from HIHO (0.5)
            # In [-1, 1] tanh space, 0.5 is represented as 0.0 for this simple mock
            coherence = float(1.0 - torch.mean(torch.abs(state_12d)).item())
            
            bus = get_telemetry_bus()
            event = FlumeJourneyEvent(
                event_id=f"grid_{int(datetime.now().timestamp())}",
                journey_id="arc_perceive",
                z_vector=z[0].tolist(),
                state_12d=state_12d[0].tolist(),
                coherence=coherence,
                fabrics=QuadratureFabrics(space=0.9, field=0.5, control=0.2, precipitation=0.1),
                awareness_parameter=0.9,
                expert_stream=SwarmExpert.BIOLOGIST,
                hardware_tier=HardwareTier.NPU,
                latency_ms=0.0,
                r_zero=RZeroMetrics(success_rate=1.0, iteration_count=1, difficulty_adjustment=1.0)
            )
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(bus.emit(event))
            except RuntimeError:
                pass
        except Exception as te:
            # We use logger from the module level if available, but ARCGridEncoder 
            # module didn't define it. We'll use a local fallback if needed.
            pass

        return z

    def decode(self, z: torch.Tensor, original_shape: tuple[int, int]) -> list[list[int]]:
        """Decode latent vector back to 2D grid of specific shape."""
        x_hat = self.decoder(z)
        x_hat = x_hat.view(self.max_grid_size, self.max_grid_size).detach().cpu().numpy()

        rows, cols = original_shape
        grid = []
        for r in range(rows):
            row = []
            for c in range(cols):
                # Denormalize and round to nearest integer 0-9
                val = int(round(x_hat[r, c] * 10.0))
                row.append(max(0, min(9, val)))
            grid.append(row)
        return grid


class FlumeGridHarness:
    """
    Harness for integrating Grid Encoding into the FLUME evaluation loop.
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = ARCGridEncoder().to(device)
        self.model.eval()

    def get_grid_embedding(self, grid_str: str) -> np.ndarray:
        """
        Parses a grid string (e.g. "[[1,2],[3,4]]") and returns its 256D embedding.
        """
        try:
            grid = json.loads(grid_str)
            with torch.no_grad():
                z = self.model.encode(grid)
                return z.squeeze(0).cpu().numpy()
        except Exception:
            # Fallback to zero vector or hash if parsing fails
            return np.zeros(256, dtype=np.float32)


import json
