"""
Trajectory Predictor - Predict the evolution of thought vectors over time.

Instead of predicting the next discrete token, we predict the next
continuous vector position in thought-space. This allows for:

1. Anticipating conceptual evolution
2. Smooth interpolation between ideas
3. Multi-step future prediction
4. Semantic momentum and inertia
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class VectorLSTM(nn.Module):
    """
    LSTM for sequence prediction in continuous vector space.
    
    Takes a sequence of thought vectors and predicts the next.
    """
    
    def __init__(
        self,
        z_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        
        self.z_dim = z_dim
        self.hidden_dim = hidden_dim
        
        self.lstm = nn.LSTM(
            input_size=z_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        
        self.output_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, z_dim),
        )
    
    def forward(
        self,
        z_sequence: torch.Tensor,
        hidden: tuple[torch.Tensor, torch.Tensor] | None = None,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        """
        Predict next vectors from sequence.
        
        Args:
            z_sequence: (batch, seq_len, z_dim) input sequence
            hidden: Optional initial hidden state
            
        Returns:
            predictions: (batch, seq_len, z_dim) predicted next vectors
            hidden: Updated hidden state
        """
        output, hidden = self.lstm(z_sequence, hidden)
        predictions = self.output_proj(output)
        return predictions, hidden


class FlowPredictor(nn.Module):
    """
    Velocity field predictor for continuous flow in thought-space.
    
    Models thought evolution as a continuous flow, where we predict
    the velocity (derivative) at each point, then integrate.
    """
    
    def __init__(
        self,
        z_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 3,
    ):
        super().__init__()
        
        layers = []
        in_dim = z_dim + 1  # Include time dimension
        
        for i in range(num_layers):
            out_dim = hidden_dim if i < num_layers - 1 else z_dim
            layers.extend([
                nn.Linear(in_dim, out_dim),
                nn.GELU() if i < num_layers - 1 else nn.Identity(),
            ])
            in_dim = out_dim
        
        self.network = nn.Sequential(*layers)
    
    def forward(
        self,
        z: torch.Tensor,
        t: torch.Tensor,
    ) -> torch.Tensor:
        """
        Predict velocity at position z and time t.
        
        Args:
            z: (batch, z_dim) current position
            t: (batch, 1) time
            
        Returns:
            velocity: (batch, z_dim) predicted velocity
        """
        x = torch.cat([z, t], dim=-1)
        return self.network(x)


class TrajectoryPredictor:
    """
    High-level predictor for thought vector trajectories.
    
    Combines LSTM sequence modeling with flow-based continuous
    prediction for flexible trajectory generation.
    """
    
    def __init__(
        self,
        z_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 2,
        use_flow: bool = True,
        device: str | torch.device | None = None,
    ):
        self.z_dim = z_dim
        self.use_flow = use_flow
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        
        self.lstm = VectorLSTM(z_dim, hidden_dim, num_layers).to(self.device)
        
        if use_flow:
            self.flow = FlowPredictor(z_dim, hidden_dim).to(self.device)
        else:
            self.flow = None
        
        self._hidden: tuple[torch.Tensor, torch.Tensor] | None = None
    
    def reset(self) -> None:
        """Reset hidden state for new sequence."""
        self._hidden = None
    
    def predict_next(
        self,
        z: torch.Tensor | np.ndarray,
    ) -> torch.Tensor:
        """
        Predict the next thought vector from current.
        
        Args:
            z: (z_dim,) or (batch, z_dim) current vector(s)
            
        Returns:
            z_next: Predicted next vector(s)
        """
        if isinstance(z, np.ndarray):
            z = torch.from_numpy(z).float()
        
        z = z.to(self.device)
        
        if z.dim() == 1:
            z = z.unsqueeze(0).unsqueeze(0)  # (1, 1, z_dim)
        elif z.dim() == 2:
            z = z.unsqueeze(1)  # (batch, 1, z_dim)
        
        with torch.no_grad():
            predictions, self._hidden = self.lstm(z, self._hidden)
        
        return predictions.squeeze(1)  # (batch, z_dim)
    
    def predict_sequence(
        self,
        z_start: torch.Tensor | np.ndarray,
        steps: int = 5,
        momentum: float = 0.0,
    ) -> list[torch.Tensor]:
        """
        Predict a sequence of future thought vectors.
        
        Args:
            z_start: Starting thought vector
            steps: Number of steps to predict
            momentum: How much to carry forward previous velocity (0-1)
            
        Returns:
            List of predicted thought vectors
        """
        if isinstance(z_start, np.ndarray):
            z_start = torch.from_numpy(z_start).float()
        
        z_start = z_start.to(self.device)
        if z_start.dim() == 1:
            z_start = z_start.unsqueeze(0)
        
        self.reset()
        trajectory = [z_start]
        z_current = z_start
        velocity = torch.zeros_like(z_current)
        
        for _ in range(steps):
            # Get LSTM prediction
            z_next = self.predict_next(z_current)
            
            # Compute new velocity
            new_velocity = z_next - z_current
            
            # Apply momentum
            velocity = momentum * velocity + (1 - momentum) * new_velocity
            z_next = z_current + velocity
            
            trajectory.append(z_next)
            z_current = z_next
        
        return trajectory
    
    def predict_flow(
        self,
        z_start: torch.Tensor | np.ndarray,
        t_end: float = 1.0,
        steps: int = 10,
    ) -> list[torch.Tensor]:
        """
        Predict trajectory using continuous flow.
        
        Uses Euler integration of the velocity field.
        
        Args:
            z_start: Starting thought vector
            t_end: End time for integration
            steps: Number of integration steps
            
        Returns:
            List of thought vectors along trajectory
        """
        if self.flow is None:
            raise ValueError("Flow predictor not initialized. Set use_flow=True.")
        
        if isinstance(z_start, np.ndarray):
            z_start = torch.from_numpy(z_start).float()
        
        z_start = z_start.to(self.device)
        if z_start.dim() == 1:
            z_start = z_start.unsqueeze(0)
        
        trajectory = [z_start]
        z_current = z_start
        dt = t_end / steps
        
        for i in range(steps):
            t = torch.full((z_current.shape[0], 1), i * dt, device=self.device)
            
            with torch.no_grad():
                velocity = self.flow(z_current, t)
            
            z_current = z_current + velocity * dt
            trajectory.append(z_current)
        
        return trajectory
    
    def smooth_trajectory(
        self,
        trajectory: list[torch.Tensor],
        smoothing: float = 0.5,
    ) -> list[torch.Tensor]:
        """
        Apply smoothing to a trajectory.
        
        Uses exponential moving average for fluid motion.
        """
        if len(trajectory) < 2:
            return trajectory
        
        smoothed = [trajectory[0]]
        
        for z in trajectory[1:]:
            z_smooth = smoothing * smoothed[-1] + (1 - smoothing) * z
            smoothed.append(z_smooth)
        
        return smoothed
    
    def trajectory_to_numpy(
        self,
        trajectory: list[torch.Tensor],
    ) -> np.ndarray:
        """Convert trajectory to numpy array for visualization."""
        return np.stack([z.cpu().numpy().squeeze() for z in trajectory])
    
    def save(self, path: Path | str) -> None:
        """Save model weights."""
        state = {
            "lstm": self.lstm.state_dict(),
            "flow": self.flow.state_dict() if self.flow else None,
            "config": {
                "z_dim": self.z_dim,
                "use_flow": self.use_flow,
            },
        }
        torch.save(state, path)
        logger.info(f"Saved predictor to {path}")
    
    def load(self, path: Path | str) -> None:
        """Load model weights."""
        state = torch.load(path, weights_only=True)
        self.lstm.load_state_dict(state["lstm"])
        if self.flow and state.get("flow"):
            self.flow.load_state_dict(state["flow"])
        logger.info(f"Loaded predictor from {path}")
