from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple

class ARCGameEncoder(nn.Module):
    """
    Triune Encoder for ARC grids. 
    Projects latents into the Doer, Thinker, and Knower manifolds.
    """
    def __init__(self, latent_dim: int = 256):
        """
        Initializes the encoder with a shared backbone and manifold-specific heads.
        
        Args:
            latent_dim: Total dimension of the combined latent vector.
        """
        super().__init__()
        # Shared feature extractor
        self.backbone = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten()
        )
        
        # Manifold-specific heads
        self.doer_head = nn.Linear(64 * 16 * 16, latent_dim // 4)
        self.thinker_head = nn.Linear(64 * 16 * 16, latent_dim // 2)
        self.knower_head = nn.Linear(64 * 16 * 16, latent_dim // 4)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Returns a concatenated Triune latent vector.
        
        Args:
            x: Input grid tensor of shape (batch, 1, 64, 64)
            
        Returns:
            Latent vector where:
            [0:64]   - Doer (Action-aligned features)
            [64:192] - Thinker (Rule-aligned features)
            [192:256]- Knower (State-aligned features)
        """
        x = x.float() / 15.0
        feat = self.backbone(x)
        
        doer = self.doer_head(feat)
        thinker = self.thinker_head(feat)
        knower = self.knower_head(feat)
        
        return torch.cat([doer, thinker, knower], dim=-1)

class ARCPredictor(nn.Module):
    """JEPA-style predictor for ARC-AGI-3."""
    def __init__(self, latent_dim: int = 256):
        """
        Initializes the predictor with embeddings for actions and coordinates.
        
        Args:
            latent_dim: Dimension of the state latent space.
        """
        super().__init__()
        self.action_emb = nn.Embedding(7, 32)
        self.x_emb = nn.Embedding(64, 32)
        self.y_emb = nn.Embedding(64, 32)
        
        self.net = nn.Sequential(
            nn.Linear(latent_dim + 32 + 32 + 32, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, latent_dim)
        )

    def forward(self, z: torch.Tensor, action: torch.Tensor, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """
        Predicts the next latent state given the current state and action.
        
        Args:
            z: Latent vector (batch, latent_dim)
            action: Action index (batch,)
            x: X coordinate (batch,)
            y: Y coordinate (batch,)
            
        Returns:
            Predicted latent vector for the next state.
        """
        a_e = self.action_emb(action)
        x_e = self.x_emb(x)
        y_e = self.y_emb(y)
        feat = torch.cat([z, a_e, x_e, y_e], dim=-1)
        return self.net(feat)

class ARCWorldModel(nn.Module):
    """JEPA World Model for ARC Prize 2026."""
    def __init__(self, latent_dim: int = 256):
        """
        Initializes the world model with encoder, predictor, and EMA target encoder.
        
        Args:
            latent_dim: Latent space dimension.
        """
        super().__init__()
        self.encoder = ARCGameEncoder(latent_dim)
        self.predictor = ARCPredictor(latent_dim)
        # Target encoder (EMA of encoder or separate for JEPA)
        self.target_encoder = ARCGameEncoder(latent_dim)
        self._update_target_encoder(tau=1.0) # Init with same weights

    def _update_target_encoder(self, tau: float = 0.01):
        """
        Performs Exponential Moving Average update of the target encoder.
        
        Args:
            tau: Momentum factor for the update.
        """
        for param, target_param in zip(self.encoder.parameters(), self.target_encoder.parameters()):
            target_param.data.copy_(tau * param.data + (1.0 - tau) * target_param.data)

    def forward(
        self, 
        grid_curr: torch.Tensor, 
        action: torch.Tensor, 
        x: torch.Tensor, 
        y: torch.Tensor, 
        grid_next: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass for prediction and optional loss calculation.
        
        Args:
            grid_curr: Current grid tensor.
            action: Action index tensor.
            x: X coordinate tensor.
            y: Y coordinate tensor.
            grid_next: Optional ground truth next grid for loss calculation.
            
        Returns:
            Tuple of (predicted latent, loss tensor or None).
        """
        z_curr = self.encoder(grid_curr)
        z_pred = self.predictor(z_curr, action, x, y)
        
        if grid_next is not None:
            with torch.no_grad():
                z_target = self.target_encoder(grid_next)
            loss = F.mse_loss(z_pred, z_target)
            return z_pred, loss
        
        return z_pred, None

    def compute_surprise(self, z_pred: torch.Tensor, grid_actual: torch.Tensor) -> float:
        """
        Calculate actual surprise (prediction error) after taking an action.
        
        Args:
            z_pred: Predicted latent vector.
            grid_actual: Actual observed grid.
            
        Returns:
            MSE loss between prediction and actual target latent.
        """
        with torch.no_grad():
            z_actual = self.target_encoder(grid_actual)
            return F.mse_loss(z_pred, z_actual).item()

    @torch.no_grad()
    def evaluate_actions(self, grid_curr: torch.Tensor, x_coord: int, y_coord: int) -> torch.Tensor:
        """
        Evaluate all 7 actions and return predicted latents for counterfactual reasoning.
        
        Args:
            grid_curr: Current grid tensor.
            x_coord: Target X coordinate.
            y_coord: Target Y coordinate.
            
        Returns:
            Tensor of shape (7, latent_dim) containing predictions for each action.
        """
        z_curr = self.encoder(grid_curr)
        results = []
        for a in range(7):
            action = torch.tensor([a]).to(grid_curr.device)
            x = torch.tensor([x_coord]).to(grid_curr.device)
            y = torch.tensor([y_coord]).to(grid_curr.device)
            z_pred = self.predictor(z_curr, action, x, y)
            results.append(z_pred)
        return torch.cat(results, dim=0) # (7, latent_dim)
